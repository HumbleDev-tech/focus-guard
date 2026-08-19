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

from daemon.hosts_manager import HostsManager, is_valid_domain, HEADER_MARKER, FOOTER_MARKER
from daemon.scheduler import StateScheduler
from daemon.focus_daemon import FocusDaemon
from client.ipc_client import FocusIPCClient
from client.settings_dialog import sanitize_domain, is_autostart_enabled, set_autostart_enabled, USER_AUTOSTART_PATH, SYSTEM_AUTOSTART_PATH
from client.main import get_instance_key


class TestDomainSanitizerAndValidator(unittest.TestCase):
    def test_sanitize_domain(self):
        self.assertEqual(sanitize_domain("twitter.com"), "twitter.com")
        self.assertEqual(sanitize_domain("https://www.youtube.com/watch?v=123"), "youtube.com")
        self.assertEqual(sanitize_domain("http://reddit.com/r/all"), "reddit.com")
        self.assertEqual(sanitize_domain("  INSTAGRAM.COM  "), "instagram.com")
        self.assertEqual(sanitize_domain("sub.domain.com:8080/path"), "sub.domain.com")
        self.assertIsNone(sanitize_domain("invalid_domain_name"))
        self.assertIsNone(sanitize_domain(""))

    def test_is_valid_domain(self):
        self.assertTrue(is_valid_domain("x.com"))
        self.assertTrue(is_valid_domain("sub.domain.co.uk"))
        self.assertTrue(is_valid_domain("reddit.com"))
        self.assertTrue(is_valid_domain("use-application-dns.net"))

        # Rejections: CRLF, whitespace, tabs, comments, path characters
        self.assertFalse(is_valid_domain("evil.com\n127.0.0.1 hack.com"))
        self.assertFalse(is_valid_domain("evil.com\r\n"))
        self.assertFalse(is_valid_domain("space in domain.com"))
        self.assertFalse(is_valid_domain("evil.com#comment"))
        self.assertFalse(is_valid_domain("evil.com/path"))
        self.assertFalse(is_valid_domain("evil.com:80"))
        self.assertFalse(is_valid_domain("a" * 255 + ".com"))
        self.assertFalse(is_valid_domain(""))
        self.assertFalse(is_valid_domain(None))


class TestHostsManager(unittest.TestCase):
    def setUp(self):
        self.tmp_hosts = tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8")
        self.tmp_hosts.write("127.0.0.1 localhost myhost\n::1 localhost\n192.168.1.50 custom.local\n")
        self.tmp_hosts.close()
        self.mgr = HostsManager(self.tmp_hosts.name, redirect_ipv4="0.0.0.0", redirect_ipv6="::1")

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
        self.assertIn("0.0.0.0 twitter.com", content)
        self.assertIn("0.0.0.0 www.twitter.com", content)
        self.assertIn("0.0.0.0 reddit.com", content)

        success_remove = self.mgr.remove_block()
        self.assertTrue(success_remove)
        self.assertFalse(self.mgr.is_blocked())

        with open(self.tmp_hosts.name, "r") as f:
            clean_content = f.read()

        self.assertIn("192.168.1.50 custom.local", clean_content)
        self.assertNotIn(HEADER_MARKER, clean_content)
        self.assertNotIn("twitter.com", clean_content)

    def test_malicious_domain_injection_filtered(self):
        malicious_input = [
            "valid-site.com",
            "evil.com\n127.0.0.1 hijacked.org",
            "bad site.com",
            "test.com#comment"
        ]
        self.mgr.apply_block(malicious_input)

        with open(self.tmp_hosts.name, "r") as f:
            content = f.read()

        self.assertIn("0.0.0.0 valid-site.com", content)
        self.assertNotIn("hijacked.org", content)
        self.assertNotIn("bad site.com", content)
        self.assertNotIn("#comment", content)


class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.config = {
            "version": "1.0.0",
            "boot_cooldown": {"enabled": True, "duration_minutes": 30},
            "curfew": {"enabled": True, "start_time": "23:15", "end_time": "07:00", "allow_bypass": False},
            "blocked_domains": ["twitter.com"]
        }
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
        pre_curfew_time = datetime(2026, 8, 19, 23, 10, 0)
        warn, secs = self.scheduler.is_curfew_approaching(pre_curfew_time, warning_minutes=10)
        self.assertTrue(warn)
        self.assertEqual(secs, 300)

        early_time = datetime(2026, 8, 19, 22, 0, 0)
        warn2, _ = self.scheduler.is_curfew_approaching(early_time, warning_minutes=10)
        self.assertFalse(warn2)

    def test_emergency_bypass_during_curfew(self):
        now = datetime.now()
        in_curfew, _, _ = self.scheduler.is_in_curfew(now)
        if in_curfew:
            ok, msg = self.scheduler.request_bypass(15, force=False)
            self.assertFalse(ok)

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


class TestIPCAndSecurityValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sock_path = f"/tmp/focus_guard_test_{int(time.time())}.sock"
        cls.hosts_file = f"/tmp/focus_guard_test_hosts_{int(time.time())}"
        cls.config_file = f"/tmp/focus_guard_test_cfg_{int(time.time())}.json"
        
        with open(cls.hosts_file, "w") as f:
            f.write("127.0.0.1 localhost\n")

        with open(cls.config_file, "w") as f:
            f.write('{"version": "1.0.0", "socket_path": "/run/focus-guard.sock", "hosts_path": "/etc/hosts", "blocked_domains": ["x.com"], "curfew": {"enabled": false}, "boot_cooldown": {"enabled": false}}')

        cls.daemon = FocusDaemon(
            config_path=cls.config_file,
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
        if os.path.exists(cls.config_file):
            os.unlink(cls.config_file)

    def test_ipc_communication_and_schema_validation(self):
        client = FocusIPCClient(socket_path=self.sock_path)

        # 1. Get status
        status = client.get_status()
        self.assertEqual(status.get("status"), "ok")

        # 2. Save Valid Config
        cfg = client.get_config()
        self.assertEqual(cfg.get("status"), "ok")
        
        updated_cfg = dict(cfg["config"])
        updated_cfg["blocked_domains"] = ["tiktok.com", "instagram.com"]
        save_res = client.save_config(updated_cfg)
        self.assertEqual(save_res.get("status"), "ok")

        cfg_after = client.get_config()
        self.assertIn("tiktok.com", cfg_after["config"]["blocked_domains"])

        # 3. Security check: Protected paths cannot be hijacked via IPC save_config
        tamper_cfg = {
            "hosts_path": "/etc/shadow",
            "socket_path": "/tmp/pwned.sock",
            "blocked_domains": ["twitch.tv"]
        }
        res_tamper = client.save_config(tamper_cfg)
        self.assertEqual(res_tamper.get("status"), "ok")
        # hosts_path in daemon must NOT have been changed
        self.assertEqual(self.daemon.hosts_path, self.hosts_file)

        # 4. Validation check: Invalid curfew time rejected
        bad_curfew_cfg = {
            "curfew": {"start_time": "99:99"}
        }
        res_bad_curfew = client.save_config(bad_curfew_cfg)
        self.assertEqual(res_bad_curfew.get("status"), "error")

        # 5. Lock & Cancel Bypass
        res_lock = client.lock_now()
        self.assertEqual(res_lock.get("status"), "ok")
        res_cancel = client.cancel_bypass()
        self.assertEqual(res_cancel.get("status"), "ok")


class TestSystemIntegrationHelpers(unittest.TestCase):
    def test_instance_key_generation(self):
        key = get_instance_key(dev_mode=False)
        self.assertTrue(key.startswith("focus-guard-tray-instance_"))
        key_dev = get_instance_key(dev_mode=True)
        self.assertTrue(key_dev.endswith("_dev"))


if __name__ == "__main__":
    unittest.main()
