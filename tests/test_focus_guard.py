"""
Automated unit and integration test suite for Focus-Guard.
"""
import os
import sys
import time
import tempfile
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from daemon.hosts_manager import HostsManager, HEADER_MARKER, FOOTER_MARKER
from daemon.scheduler import StateScheduler
from daemon.focus_daemon import FocusDaemon
from client.ipc_client import FocusIPCClient


class TestHostsManager(unittest.TestCase):
    def setUp(self):
        self.tmp_hosts = tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8")
        self.tmp_hosts.write("127.0.0.1 localhost myhost\n::1 localhost\n192.168.1.50 custom.local\n")
        self.tmp_hosts.close()
        self.mgr = HostsManager(self.tmp_hosts.name)

    def tearDown(self):
        if os.path.exists(self.tmp_hosts.name):
            os.unlink(self.tmp_hosts.name)

    def test_apply_and_remove_block(self):
        self.assertFalse(self.mgr.is_blocked())

        success = self.mgr.apply_block(["twitter.com", "reddit.com"])
        self.assertTrue(success)
        self.assertTrue(self.mgr.is_blocked())

        with open(self.tmp_hosts.name, "r") as f:
            content = f.read()

        self.assertIn("192.168.1.50 custom.local", content)
        self.assertIn(HEADER_MARKER, content)
        self.assertIn(FOOTER_MARKER, content)
        self.assertIn("127.0.0.1 twitter.com", content)
        self.assertIn("127.0.0.1 www.twitter.com", content)
        self.assertIn("127.0.0.1 reddit.com", content)

        success_remove = self.mgr.remove_block()
        self.assertTrue(success_remove)
        self.assertFalse(self.mgr.is_blocked())

        with open(self.tmp_hosts.name, "r") as f:
            clean_content = f.read()

        self.assertIn("192.168.1.50 custom.local", clean_content)
        self.assertNotIn(HEADER_MARKER, clean_content)
        self.assertNotIn("twitter.com", clean_content)


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.config = {
            "version": "1.0.0",
            "boot_cooldown": {"enabled": True, "duration_minutes": 30},
            "curfew": {"enabled": True, "start_time": "23:15", "end_time": "07:00", "allow_bypass": False},
            "blocked_domains": ["twitter.com"]
        }
        # In test mode we enable dev_mode to test relative timings
        self.scheduler = StateScheduler(self.config, dev_mode=True)

    def test_boot_cooldown_dev(self):
        now = self.scheduler.daemon_start_time + timedelta(minutes=5)
        in_boot, remaining, target = self.scheduler.is_in_boot_cooldown(now)
        self.assertTrue(in_boot)
        self.assertGreater(remaining, 1400)
        self.assertIsNotNone(target)

        after_cooldown = self.scheduler.daemon_start_time + timedelta(minutes=35)
        in_boot2, remaining2, target2 = self.scheduler.is_in_boot_cooldown(after_cooldown)
        self.assertFalse(in_boot2)
        self.assertEqual(remaining2, 0)
        self.assertIsNone(target2)

    def test_curfew_midnight_crossing(self):
        night_time = datetime(2026, 8, 19, 23, 30, 0)
        in_curfew, rem, target = self.scheduler.is_in_curfew(night_time)
        self.assertTrue(in_curfew)
        self.assertEqual(rem, 7 * 3600 + 30 * 60)
        self.assertEqual(target.hour, 7)

        early_time = datetime(2026, 8, 20, 3, 0, 0)
        in_curfew2, rem2, target2 = self.scheduler.is_in_curfew(early_time)
        self.assertTrue(in_curfew2)
        self.assertEqual(rem2, 4 * 3600)
        self.assertEqual(target2.hour, 7)

        day_time = datetime(2026, 8, 19, 14, 0, 0)
        in_curfew3, _, target3 = self.scheduler.is_in_curfew(day_time)
        self.assertFalse(in_curfew3)
        self.assertIsNone(target3)

    def test_curfew_warning(self):
        # 23:10 is 5 mins before 23:15 -> warning should be True
        pre_curfew_time = datetime(2026, 8, 19, 23, 10, 0)
        warn, secs = self.scheduler.is_curfew_approaching(pre_curfew_time, warning_minutes=10)
        self.assertTrue(warn)
        self.assertEqual(secs, 300)

        # 22:00 is 1h15m before -> warning should be False
        early_time = datetime(2026, 8, 19, 22, 0, 0)
        warn2, _ = self.scheduler.is_curfew_approaching(early_time, warning_minutes=10)
        self.assertFalse(warn2)

    def test_emergency_bypass_during_curfew(self):
        # Normal bypass rejected during curfew
        now = datetime.now()
        in_curfew, _, _ = self.scheduler.is_in_curfew(now)
        if in_curfew:
            ok, msg = self.scheduler.request_bypass(15, force=False)
            self.assertFalse(ok)

            # Emergency bypass accepted with force=True
            ok_emerg, msg_emerg = self.scheduler.request_bypass(15, force=True)
            self.assertTrue(ok_emerg)
            eval_state = self.scheduler.evaluate_state()
            self.assertEqual(eval_state["state"], "BYPASS")
            self.assertEqual(eval_state["reason"], "EMERGENCY_BYPASS")
            self.assertFalse(eval_state["is_blocking"])

    def test_bypass_outside_curfew(self):
        cfg_no_curfew = dict(self.config)
        cfg_no_curfew["curfew"] = {"enabled": False}
        sched = StateScheduler(cfg_no_curfew, dev_mode=True)

        ok, msg = sched.request_bypass(15)
        self.assertTrue(ok)
        self.assertTrue(sched.is_in_bypass()[0])

        ok_c, _ = sched.cancel_bypass()
        self.assertTrue(ok_c)
        self.assertFalse(sched.is_in_bypass()[0])


class TestIPCIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sock_path = f"/tmp/focus_guard_test_{int(time.time())}.sock"
        cls.hosts_file = f"/tmp/focus_guard_test_hosts_{int(time.time())}"
        with open(cls.hosts_file, "w") as f:
            f.write("127.0.0.1 localhost\n")

        cls.daemon = FocusDaemon(
            hosts_path=cls.hosts_file,
            socket_path=cls.sock_path,
            dev_mode=True
        )
        import threading
        cls.daemon_thread = threading.Thread(target=cls.daemon.run, daemon=True)
        cls.daemon_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.daemon.stop(clean_hosts=True)
        if os.path.exists(cls.sock_path):
            os.unlink(cls.sock_path)
        if os.path.exists(cls.hosts_file):
            os.unlink(cls.hosts_file)

    def test_ipc_communication(self):
        client = FocusIPCClient(socket_path=self.sock_path)

        status = client.get_status()
        self.assertEqual(status.get("status"), "ok")
        self.assertIn("state", status)
        self.assertIn("reason", status)

        res_lock = client.lock_now()
        self.assertEqual(res_lock.get("status"), "ok")

        status2 = client.get_status()
        self.assertTrue(status2.get("is_blocking"))

        res_cancel = client.cancel_bypass()
        self.assertEqual(res_cancel.get("status"), "ok")


if __name__ == "__main__":
    unittest.main()
