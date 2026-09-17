"""
Tests for client.icons and client.theme (Fases 1 y 2).
"""

import os
import sys
import unittest

from PyQt6.QtWidgets import QApplication, QDialog, QPushButton, QTabWidget, QWidget
from PyQt6.QtGui import QIcon, QPixmap

from client.icons import get_icon, get_pixmap, get_themed_icon, ICONS_DIR
from client.theme import get_theme_colors, get_theme_stylesheet, apply_dialog_theme

# Ensure Qt Application exists
_app = QApplication.instance() or QApplication(sys.argv)


class TestIconsAndTheme(unittest.TestCase):
    def test_icons_directory_exists(self):
        self.assertTrue(os.path.isdir(ICONS_DIR), f"Icons directory not found at {ICONS_DIR}")

    def test_required_lucide_icons_exist(self):
        required = [
            "shield", "shield-alert", "shield-check", "sliders", "clock",
            "activity", "sun", "moon", "monitor", "settings", "coffee",
            "timer", "zap", "lock", "unlock", "plus", "minus", "trash-2",
            "check", "search", "info", "power", "copy", "globe", "undo", "x"
        ]
        for name in required:
            icon = get_icon(name, size=16)
            self.assertFalse(icon.isNull(), f"Icon '{name}' should not be null")

    def test_icon_pixmap_tinting(self):
        pix_dark = get_pixmap("shield", color="#388BFD", size=24, dpr=1.0)
        self.assertFalse(pix_dark.isNull())
        self.assertEqual(pix_dark.width(), 24)
        self.assertEqual(pix_dark.height(), 24)

    def test_themed_icons(self):
        # Dark mode
        icon_dark = get_themed_icon("sun", is_dark=True, role="accent")
        self.assertFalse(icon_dark.isNull())

        # Light mode
        icon_light = get_themed_icon("moon", is_dark=False, role="primary")
        self.assertFalse(icon_light.isNull())

    def test_theme_colors_structure(self):
        dark_colors = get_theme_colors(is_dark=True)
        light_colors = get_theme_colors(is_dark=False)

        for key in ["bg_window", "bg_card", "border_color", "accent_blue", "text_primary", "danger", "success"]:
            self.assertIn(key, dark_colors)
            self.assertIn(key, light_colors)

    def test_stylesheet_generation(self):
        this_dir = os.path.dirname(os.path.realpath(__file__))
        res_dir = os.path.abspath(os.path.join(this_dir, "../resources"))
        qss_dark = get_theme_stylesheet(is_dark=True, resource_dir=res_dir)
        qss_light = get_theme_stylesheet(is_dark=False, resource_dir=res_dir)

        self.assertIn("QDialog", qss_dark)
        self.assertIn("QTabBar::tab", qss_dark)
        self.assertIn("QPushButton#primaryBtn", qss_dark)
        self.assertIn("QMenu", qss_dark)

        self.assertIn("QDialog", qss_light)

    def test_apply_dialog_theme(self):
        dlg = QDialog()
        apply_dialog_theme(dlg, is_dark=True)
        self.assertTrue(len(dlg.styleSheet()) > 0)


if __name__ == "__main__":
    unittest.main()
