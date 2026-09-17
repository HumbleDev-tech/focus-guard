"""
Automated unit tests for Phase 1 (AUR Packaging & Arch Standards)
and Phase 2 (Daemon Concurrency, Thread-Safety & Anti-Hang IPC).
"""
import os
import sys
import time
import json
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from daemon.focus_daemon import FocusDaemon
from daemon.hosts_manager import HostsManager, BLOCK_START_DELIMITER, BLOCK_END_DELIMITER
from client.ipc_client import FocusIPCClient


class TestAURPackagingCompliance(unittest.TestCase):
    def setUp(self):
        self.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.pkgbuild_path = os.path.join(self.repo_root, "packaging/aur/PKGBUILD")
        self.srcinfo_path = os.path.join(self.repo_root, "packaging/aur/.SRCINFO")
        self.install_path = os.path.join(self.repo_root, "packaging/aur/focus-guard.install")
        self.install_sh = os.path.join(self.repo_root, "scripts/install.sh")

    def test_pkgbuild_dependencies_include_qt6_svg(self):
        """PKGBUILD must explicitly require qt6-svg for Arch Linux."""
        with open(self.pkgbuild_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("'qt6-svg'", content, "PKGBUILD is missing qt6-svg dependency")

    def test_srcinfo_dependencies_include_qt6_svg(self):
        """.SRCINFO must declare qt6-svg dependency for AUR helpers."""
        with open(self.srcinfo_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("depends = qt6-svg", content, ".SRCINFO is missing depends = qt6-svg")

    def test_pkgbuild_config_file_exists(self):
        """PKGBUILD must reference an existing default configuration file."""
        with open(self.pkgbuild_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("config/config.default.json", content, "PKGBUILD references non-existent config.default.json")
        self.assertIn("config/default_config.json", content, "PKGBUILD must reference config/default_config.json")
        real_config = os.path.join(self.repo_root, "config/default_config.json")
        self.assertTrue(os.path.exists(real_config), f"Target default config {real_config} does not exist")

    def test_install_script_delimiters_match_hosts_manager(self):
        """focus-guard.install must use the exact delimiters produced by HostsManager."""
        with open(self.install_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Must NOT contain outdated markers
        self.assertNotIn("# FOCUS-GUARD-BEGIN", content)
        self.assertNotIn("# FOCUS-GUARD-END", content)
        # Must contain true HostsManager delimiters
        self.assertIn("FOCUS-GUARD-BLOCK-START", content)
        self.assertIn("FOCUS-GUARD-BLOCK-END", content)

    def test_install_script_no_imperative_systemctl_restarts(self):
        """focus-guard.install must not imperatively restart systemd services in post_upgrade."""
        with open(self.install_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("systemctl restart focus-guard.service", content)
        self.assertNotIn("systemctl daemon-reload", content)

    def test_install_sh_symlinks_cli(self):
        """scripts/install.sh must symlink focus-guard-cli to /usr/bin/."""
        with open(self.install_sh, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("ln -sf /opt/focus-guard/client/cli.py /usr/bin/focus-guard-cli", content)


class TestDaemonConcurrencyAndIPC(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        unique_id = int(time.time() * 1000) % 1000000
        cls.test_dir = tempfile.mkdtemp()
        cls.config_file = os.path.join(cls.test_dir, f"test_cfg_{unique_id}.json")
        cls.hosts_file = os.path.join(cls.test_dir, f"test_hosts_{unique_id}")
        cls.sock_path = os.path.join(cls.test_dir, f"test_{unique_id}.sock")
        cls.state_file = os.path.join(cls.test_dir, f"test_state_{unique_id}.json")

        initial_config = {
            "version": "1.0.0",
            "socket_path": cls.sock_path,
            "hosts_path": cls.hosts_file,
            "boot_cooldown": {"enabled": False, "duration_minutes": 30},
            "curfew": {"enabled": False, "start_time": "23:15", "end_time": "07:00"},
            "bypasses": {"enabled": True, "allow_during_curfew": False, "emergency_phrase": "emergencia"},
            "blocked_domains": ["reddit.com", "x.com", "tiktok.com"],
            "redirect_ipv4": "0.0.0.0",
            "redirect_ipv6": "::1"
        }
        with open(cls.config_file, "w", encoding="utf-8") as f:
            json.dump(initial_config, f)

        with open(cls.hosts_file, "w", encoding="utf-8") as f:
            f.write("127.0.0.1 localhost\n::1 localhost\n")

        cls.daemon = FocusDaemon(
            config_path=cls.config_file,
            hosts_path=cls.hosts_file,
            socket_path=cls.sock_path,
            state_path=cls.state_file,
            dev_mode=True
        )

        cls.server_thread = threading.Thread(target=cls.daemon.run, daemon=True)
        cls.server_thread.start()

        # Wait for socket availability
        for _ in range(30):
            if os.path.exists(cls.sock_path):
                break
            time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.daemon.stop(clean_hosts=False)
        for p in [cls.config_file, cls.hosts_file, cls.sock_path, cls.state_file]:
            if os.path.exists(p):
                try:
                    os.unlink(p)
                except Exception:
                    pass
        if os.path.exists(cls.test_dir):
            try:
                os.rmdir(cls.test_dir)
            except Exception:
                pass

    def test_concurrent_ipc_requests_no_deadlock(self):
        """Simulates rapid concurrent requests from multiple clients without deadlocks or crashes."""
        client = FocusIPCClient(socket_path=self.sock_path)
        errors = []
        iterations = 25

        def worker_lock_unlock(worker_id):
            try:
                for i in range(iterations):
                    res1 = client.lock_now(duration_minutes=20)
                    if res1.get("status") != "ok":
                        errors.append(f"Worker {worker_id} lock failed: {res1}")
                    time.sleep(0.01)
                    res2 = client.unlock_now()
                    if res2.get("status") != "ok":
                        errors.append(f"Worker {worker_id} unlock failed: {res2}")
            except Exception as e:
                errors.append(f"Worker {worker_id} exception: {e}")

        def worker_status_poller(worker_id):
            try:
                for _ in range(iterations * 2):
                    st = client.get_status()
                    if st.get("status") != "ok":
                        errors.append(f"Poller {worker_id} status failed: {st}")
                    time.sleep(0.005)
            except Exception as e:
                errors.append(f"Poller {worker_id} exception: {e}")

        threads = []
        # Launch 4 concurrent workers
        threads.append(threading.Thread(target=worker_lock_unlock, args=(1,)))
        threads.append(threading.Thread(target=worker_lock_unlock, args=(2,)))
        threads.append(threading.Thread(target=worker_status_poller, args=(3,)))
        threads.append(threading.Thread(target=worker_status_poller, args=(4,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10.0)

        for t in threads:
            self.assertFalse(t.is_alive(), "A concurrent worker thread deadlocked!")

        self.assertEqual(len(errors), 0, f"Concurrent workers encountered errors: {errors}")

        # Hosts file must still be clean and structurally valid
        with open(self.hosts_file, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("127.0.0.1 localhost", content)
        # Delimiters must not be duplicated or corrupted
        self.assertLessEqual(content.count(BLOCK_START_DELIMITER), 1)
        self.assertLessEqual(content.count(BLOCK_END_DELIMITER), 1)

    def test_large_json_payload_stream_handling(self):
        """Tests that a large JSON payload (100+ domains) is handled without JSONDecodeError."""
        client = FocusIPCClient(socket_path=self.sock_path)
        cfg_res = client.get_config()
        self.assertEqual(cfg_res.get("status"), "ok")

        large_domain_list = [f"domain-{i}.example.com" for i in range(150)]
        test_cfg = dict(cfg_res["config"])
        test_cfg["blocked_domains"] = large_domain_list

        save_res = client.save_config(test_cfg)
        self.assertEqual(save_res.get("status"), "ok", f"Saving large config failed: {save_res}")

        # Verify saved domains count
        verify_cfg = client.get_config()
        self.assertEqual(len(verify_cfg["config"]["blocked_domains"]), 150)

        # Restore normal domain list
        test_cfg["blocked_domains"] = ["reddit.com", "x.com"]
        client.save_config(test_cfg)


if __name__ == "__main__":
    unittest.main()
