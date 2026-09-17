"""
Tests for Phase 3 and Phase 4 Performance, Stability, and FHS Compliance.
Validates:
- Boot time caching in scheduler (prevents /proc/stat disk churn)
- SVG pixmap LRU caching in client/icons
- FHS /var/lib/focus-guard/state.json resolution in daemon
- Debounce timers on search inputs (DomainsTab & SelectiveTab)
- Low-latency IPC timeout defaults
"""
import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from daemon import scheduler
from client import icons
from client.ipc_client import IPCClient


class TestSchedulerBootTimeCache(unittest.TestCase):
    """Verifies that /proc/stat btime is cached in memory."""

    def setUp(self):
        # Reset cached boot epoch before test
        scheduler._CACHED_BOOT_EPOCH = None

    def tearDown(self):
        scheduler._CACHED_BOOT_EPOCH = None

    def test_boot_epoch_is_cached(self):
        fake_stat = "cpu  123 456\nbtime 1700000000\nprocesses 789\n"

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", unittest.mock.mock_open(read_data=fake_stat)) as mock_file:
                with patch("time.time", return_value=1700000100.0):
                    res1 = scheduler.get_real_seconds_since_boot()
                    self.assertEqual(res1, 100.0)
                    self.assertEqual(scheduler._CACHED_BOOT_EPOCH, 1700000000.0)

                    # Second call with time advanced
                    with patch("time.time", return_value=1700000250.0):
                        res2 = scheduler.get_real_seconds_since_boot()
                        self.assertEqual(res2, 250.0)

                # open() should have been called only ONCE because of caching
                self.assertEqual(mock_file.call_count, 1)


class TestIconCaching(unittest.TestCase):
    """Verifies SVG pixmap LRU caching behavior."""

    def test_svg_pixmap_cached(self):
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QPixmap

        app = QApplication.instance() or QApplication(["test"])

        icons.clear_icon_cache()
        cache_info_before = icons._render_svg_file_cached.cache_info()

        # Call get_svg_pixmap for a known icon path
        icon_path = icons.get_icon_path("shield") or icons.get_icon_path("lock")
        if icon_path and os.path.isfile(icon_path):
            px1 = icons.get_svg_pixmap(icon_path, size=16)
            self.assertFalse(px1.isNull())
            px2 = icons.get_svg_pixmap(icon_path, size=16)
            cache_info_after = icons._render_svg_file_cached.cache_info()
            self.assertGreater(cache_info_after.hits, cache_info_before.hits)

        icons.clear_icon_cache()
        cache_info_cleared = icons._render_svg_file_cached.cache_info()
        self.assertEqual(cache_info_cleared.currsize, 0)


class TestFHSStatePathResolution(unittest.TestCase):
    """Verifies FocusDaemon correctly resolves FHS state path."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.cfg_file = os.path.join(self.temp_dir, "config.json")
        with open(self.cfg_file, "w") as f:
            f.write('{"blocked_domains": ["badsite.com"]}')

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_explicit_state_path_respected(self):
        from daemon.focus_daemon import FocusDaemon
        explicit = os.path.join(self.temp_dir, "custom_state.json")
        d = FocusDaemon(config_path=self.cfg_file, state_path=explicit, dev_mode=True)
        self.assertEqual(d.state_path, explicit)

    def test_dev_mode_state_path(self):
        from daemon.focus_daemon import FocusDaemon
        d = FocusDaemon(config_path=self.cfg_file, dev_mode=True)
        self.assertEqual(d.state_path, "/tmp/focus_guard_dev_state.json")

    def test_fhs_var_lib_path_resolution(self):
        from daemon.focus_daemon import FocusDaemon
        with patch("os.path.exists") as mock_exists:
            # Simulate /var/lib exists, no legacy state
            def exists_side_effect(path):
                if path == self.cfg_file:
                    return True
                if path == "/var/lib":
                    return True
                return False

            mock_exists.side_effect = exists_side_effect
            d = FocusDaemon(config_path=self.cfg_file, dev_mode=False)
            self.assertEqual(d.state_path, "/var/lib/focus-guard/state.json")

    def test_legacy_etc_state_migration(self):
        from daemon.focus_daemon import FocusDaemon
        legacy_state = os.path.join(self.temp_dir, "state.json")
        with open(legacy_state, "w") as f:
            f.write('{"selective_is_indefinite": true, "selective_domains": ["youtube.com"]}')

        target_var = os.path.join(self.temp_dir, "var_lib_target", "state.json")

        with patch("os.path.exists") as mock_exists:
            with patch("shutil.copy2") as mock_copy:
                with patch("os.makedirs"):
                    def exists_side_effect(path):
                        if path in (self.cfg_file, legacy_state):
                            return True
                        if path == "/var/lib/focus-guard/state.json":
                            return False
                        return False

                    mock_exists.side_effect = exists_side_effect
                    d = FocusDaemon(config_path=self.cfg_file, dev_mode=False)
                    self.assertEqual(d.state_path, "/var/lib/focus-guard/state.json")
                    mock_copy.assert_called_once()


class TestSearchDebounceTimers(unittest.TestCase):
    """Verifies that search inputs use 150ms single-shot debounce QTimers."""

    def setUp(self):
        from PyQt6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication(["test"])

    def test_domains_tab_search_debounce(self):
        from client.tabs.domains_tab import DomainsTab
        tab = DomainsTab(lambda: {}, lambda: {})
        self.assertTrue(hasattr(tab, "_search_timer"))
        self.assertTrue(tab._search_timer.isSingleShot())
        self.assertEqual(tab._search_timer.interval(), 150)

    def test_selective_tab_search_debounce(self):
        from client.tabs.selective_tab import SelectiveTab
        tab = SelectiveTab()
        self.assertTrue(hasattr(tab, "_sel_search_timer"))
        self.assertTrue(tab._sel_search_timer.isSingleShot())
        self.assertEqual(tab._sel_search_timer.interval(), 150)


class TestIPCTimeouts(unittest.TestCase):
    """Verifies IPC client timeout settings to prevent Wayland freezes."""

    def test_default_timeout(self):
        client = IPCClient()
        self.assertEqual(client.timeout, 1.0)

    def test_get_status_uses_tight_timeout(self):
        client = IPCClient()
        with patch.object(client, "send_command") as mock_send:
            mock_send.return_value = {"status": "ok"}
            res = client.get_status()
            mock_send.assert_called_once_with({"action": "status"}, timeout=0.8)


if __name__ == "__main__":
    unittest.main()
