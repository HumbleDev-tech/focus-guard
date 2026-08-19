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

        # Apply block
        success = self.mgr.apply_block(["twitter.com", "reddit.com"])
        self.assertTrue(success)
        self.assertTrue(self.mgr.is_blocked())

        # Check content
        with open(self.tmp_hosts.name, "r") as f:
            content = f.read()

        self.assertIn("192.168.1.50 custom.local", content)
        self.assertIn(HEADER_MARKER, content)
        self.assertIn(FOOTER_MARKER, content)
        self.assertIn("127.0.0.1 twitter.com", content)
        self.assertIn("127.0.0.1 www.twitter.com", content)
        self.assertIn("127.0.0.1 reddit.com", content)

        # Remove block
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
        self.scheduler = StateScheduler(self.config)

    def test_boot_cooldown(self):
        now = self.scheduler.daemon_start_time + timedelta(minutes=5)
        in_boot, remaining = self.scheduler.is_in_boot_cooldown(now)
        self.assertTrue(in_boot)
        self.assertGreater(remaining, 1400)

        after_cooldown = self.scheduler.daemon_start_time + timedelta(minutes=35)
        in_boot2, remaining2 = self.scheduler.is_in_boot_cooldown(after_cooldown)
        self.assertFalse(in_boot2)
        self.assertEqual(remaining2, 0)

    def test_curfew_midnight_crossing(self):
        # 23:30 is in curfew
        night_time = datetime(2026, 8, 19, 23, 30, 0)
        in_curfew, rem = self.scheduler.is_in_curfew(night_time)
        self.assertTrue(in_curfew)
        self.assertEqual(rem, 7 * 3600 + 30 * 60)

        # 03:00 is in curfew
        early_time = datetime(2026, 8, 20, 3, 0, 0)
        in_curfew2, rem2 = self.scheduler.is_in_curfew(early_time)
        self.assertTrue(in_curfew2)
        self.assertEqual(rem2, 4 * 3600)

        # 14:00 is outside curfew
        day_time = datetime(2026, 8, 19, 14, 0, 0)
        in_curfew3, _ = self.scheduler.is_in_curfew(day_time)
        self.assertFalse(in_curfew3)

    def test_bypass_denied_during_curfew(self):
        # If tested during real-time curfew, normal bypass is denied
        now = datetime.now()
        in_curfew, _ = self.scheduler.is_in_curfew(now)
        if in_curfew:
            ok, msg = self.scheduler.request_bypass(15)
            self.assertFalse(ok)
            self.assertIn("Curfew", msg)

    def test_bypass_outside_curfew(self):
        # Disable curfew temporarily for bypass testing
        cfg_no_curfew = dict(self.config)
        cfg_no_curfew["curfew"] = {"enabled": False}
        sched = StateScheduler(cfg_no_curfew)

        ok, msg = sched.request_bypass(15)
        self.assertTrue(ok)
        self.assertTrue(sched.is_in_bypass()[0])

        # Cancel bypass
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
            socket_path=cls.sock_path
        )
        import threading
        cls.daemon_thread = threading.Thread(target=cls.daemon.run, daemon=True)
        cls.daemon_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.daemon.stop()
        if os.path.exists(cls.sock_path):
            os.unlink(cls.sock_path)
        if os.path.exists(cls.hosts_file):
            os.unlink(cls.hosts_file)

    def test_ipc_communication(self):
        client = FocusIPCClient(socket_path=self.sock_path)

        # 1. Get status
        status = client.get_status()
        self.assertEqual(status.get("status"), "ok")
        self.assertIn("state", status)
        self.assertIn("reason", status)

        # 2. Request Lock
        res_lock = client.lock_now()
        self.assertEqual(res_lock.get("status"), "ok")

        status2 = client.get_status()
        self.assertTrue(status2.get("is_blocking"))

        # 3. Cancel Bypass / Status check
        res_cancel = client.cancel_bypass()
        self.assertEqual(res_cancel.get("status"), "ok")


if __name__ == "__main__":
    unittest.main()
