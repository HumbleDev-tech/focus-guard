"""
Tests for Focus-Guard Adaptive Scaling & Multi-Resolution Support.
Validates window geometry calculations, screen dimension clamping,
High-DPI policy, and DashboardTab scrollability.
"""

import sys
import os
import unittest
from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QApplication, QScrollArea
from PyQt6.QtCore import QRect, QSettings, Qt

from client.settings_dialog import SettingsDialog
from client.tabs.dashboard_tab import DashboardTab
from client.ipc_client import FocusIPCClient

_app = QApplication.instance() or QApplication(sys.argv)


class MockScreen:
    def __init__(self, x=0, y=0, width=1920, height=1080):
        self._rect = QRect(x, y, width, height)

    def availableGeometry(self):
        return self._rect


class TestAdaptiveScaling(unittest.TestCase):
    def setUp(self):
        self.mock_ipc = MagicMock(spec=FocusIPCClient)
        self.mock_ipc.get_status.return_value = {"status": "ok", "state": "FREE"}
        self.mock_ipc.get_config.return_value = {"status": "ok", "config": {}}
        self.resource_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../resources"))

        # Clear any stored test window geometry
        settings = QSettings("FocusGuard", "FocusGuardTray")
        settings.remove("window_geometry")

    def tearDown(self):
        settings = QSettings("FocusGuard", "FocusGuardTray")
        settings.remove("window_geometry")

    def test_compact_screen_adaptation_768p(self):
        """On 1366x768 screens, the window must fit within available bounds and not overflow."""
        # Simulated 1366x768 screen with 48px panel at bottom -> 1366x720 available
        mock_screen = MockScreen(0, 0, 1366, 720)

        with patch.object(SettingsDialog, "screen", return_value=mock_screen):
            dlg = SettingsDialog(ipc_client=self.mock_ipc, resource_dir=self.resource_dir)

            # Minimum size must allow fitting on 720p height
            self.assertLessEqual(dlg.minimumHeight(), 500)
            self.assertLessEqual(dlg.minimumWidth(), 640)

            # Initial window size must fit within available height and width
            self.assertLessEqual(dlg.width(), 1366)
            self.assertLessEqual(dlg.height(), 720)
            self.assertLessEqual(dlg.height(), 600)  # Should use compact target

            # Window position must not start off-screen
            self.assertGreaterEqual(dlg.x(), 0)
            self.assertGreaterEqual(dlg.y(), 0)

            dlg.close()

    def test_full_hd_screen_adaptation_1080p(self):
        """On 1920x1080 screens, the window adopts standard comfortable dimensions."""
        mock_screen = MockScreen(0, 0, 1920, 1032)

        with patch.object(SettingsDialog, "screen", return_value=mock_screen):
            dlg = SettingsDialog(ipc_client=self.mock_ipc, resource_dir=self.resource_dir)

            # Should size comfortably around ~800x680
            self.assertEqual(dlg.width(), 800)
            self.assertEqual(dlg.height(), 680)

            # Centered horizontally and vertically
            expected_x = (1920 - 800) // 2
            expected_y = (1032 - 680) // 2
            self.assertEqual(dlg.x(), expected_x)
            self.assertEqual(dlg.y(), expected_y)

            dlg.close()

    def test_high_resolution_adaptation_1440p(self):
        """On 2560x1440 screens, the window scales up to spacious target dimensions."""
        mock_screen = MockScreen(0, 0, 2560, 1400)

        with patch.object(SettingsDialog, "screen", return_value=mock_screen):
            dlg = SettingsDialog(ipc_client=self.mock_ipc, resource_dir=self.resource_dir)

            # Target size on 1440p / 4K should scale to 920x780
            self.assertEqual(dlg.width(), 920)
            self.assertEqual(dlg.height(), 780)

            expected_x = (2560 - 920) // 2
            expected_y = (1400 - 780) // 2
            self.assertEqual(dlg.x(), expected_x)
            self.assertEqual(dlg.y(), expected_y)

            dlg.close()

    def test_geometry_persistence_and_safe_fallback(self):
        """Window restores previous user geometry when valid, and falls back if geometry exceeds new screen."""
        mock_screen_1080 = MockScreen(0, 0, 1920, 1080)

        with patch.object(SettingsDialog, "screen", return_value=mock_screen_1080):
            dlg1 = SettingsDialog(ipc_client=self.mock_ipc, resource_dir=self.resource_dir)
            dlg1.resize(850, 710)
            dlg1.save_current_geometry()
            dlg1.close()

        # Reopening on same screen should restore 850x710
        with patch.object(SettingsDialog, "screen", return_value=mock_screen_1080):
            dlg2 = SettingsDialog(ipc_client=self.mock_ipc, resource_dir=self.resource_dir)
            self.assertEqual(dlg2.width(), 850)
            self.assertEqual(dlg2.height(), 710)
            dlg2.close()

        # Reopening on smaller 1024x600 screen should safely discard oversized saved geometry and adapt
        mock_screen_small = MockScreen(0, 0, 1024, 600)
        with patch.object(SettingsDialog, "screen", return_value=mock_screen_small):
            dlg3 = SettingsDialog(ipc_client=self.mock_ipc, resource_dir=self.resource_dir)
            # Must not be 850x710 because height 710 > available 600
            self.assertLessEqual(dlg3.height(), 600)
            self.assertLessEqual(dlg3.width(), 1024)
            dlg3.close()

    def test_dashboard_tab_has_scroll_area(self):
        """DashboardTab must contain a QScrollArea to prevent clipping on compact displays."""
        dash = DashboardTab()
        scroll_areas = dash.findChildren(QScrollArea)
        self.assertGreaterEqual(len(scroll_areas), 1)
        self.assertTrue(scroll_areas[0].widgetResizable())


if __name__ == "__main__":
    unittest.main()
