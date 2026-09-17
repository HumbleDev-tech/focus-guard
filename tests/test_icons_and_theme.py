"""
Tests for client.icons and client.theme (Fases 1 y 2).
"""

import os
import sys
import unittest

from PyQt6.QtWidgets import QApplication, QDialog, QPushButton, QTabWidget, QWidget
from PyQt6.QtGui import QIcon, QPixmap

from client.icons import get_icon, get_pixmap, get_themed_icon, get_svg_pixmap, ICONS_DIR
from client.theme import (
    get_theme_colors, get_theme_stylesheet, apply_dialog_theme,
    get_status_tokens, get_status_badge_style, STATUS_TOKENS
)

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

        for key in ["bg_window", "bg_card", "border_color", "accent_blue", "text_primary", "danger", "success", "curfew"]:
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
        result = apply_dialog_theme(dlg, is_dark=True)
        self.assertTrue(result)
        self.assertTrue(len(dlg.styleSheet()) > 0)

    def test_clear_icon_cache(self):
        from client.icons import clear_icon_cache
        icon = get_icon("shield", size=16)
        self.assertFalse(icon.isNull())
        clear_icon_cache()
        # Ensure it works after clearing cache
        icon2 = get_icon("shield", size=16)
        self.assertFalse(icon2.isNull())

    def test_themed_icon_auto_detect(self):
        # When is_dark is omitted, should resolve automatically without error
        icon_auto = get_themed_icon("check", role="white")
        self.assertFalse(icon_auto.isNull())

    def test_icon_active_hover_mode(self):
        # Verify that get_icon attaches pixmaps for Active & Selected modes
        icon = get_icon("minus", color="#8B949E", active_color="#FFFFFF", size=14)
        self.assertFalse(icon.isNull())
        act_pm = icon.pixmap(14, 14, QIcon.Mode.Active, QIcon.State.Off)
        self.assertFalse(act_pm.isNull())

    def test_tab_is_dark_mode_inside_qtabwidget(self):
        from client.tabs import DomainsTab, RulesTab, SelectiveTab, DashboardTab
        from client.settings_dialog import SettingsDialog
        from client.ipc_client import FocusIPCClient

        class DummyIPC:
            def get_status(self): return {"status": "ok", "state": "FREE_TIME"}
            def get_config(self): return {"status": "ok", "config": {}}

        dlg = QDialog()
        dlg.is_dark_mode = lambda: False
        tabs = QTabWidget(dlg)

        dom_tab = DomainsTab(DummyIPC().get_status, DummyIPC().get_config, parent=dlg)
        tabs.addTab(dom_tab, "Domains")

        rules_tab = RulesTab(parent=dlg)
        tabs.addTab(rules_tab, "Rules")

        # Even though parent is QStackedWidget, window() resolves to dlg
        self.assertFalse(dom_tab.is_dark_mode())
        self.assertFalse(rules_tab.is_dark_mode())

    def test_semantic_status_tokens(self):
        # All key statuses should return complete token dictionaries
        for status in ["UNLOCKED", "BYPASS", "CURFEW", "BOOT_COOLDOWN", "MANUAL_LOCK", "SELECTIVE_LOCK", "OFFLINE"]:
            dark_tok = get_status_tokens(status, is_dark=True)
            light_tok = get_status_tokens(status, is_dark=False)

            for tok in [dark_tok, light_tok]:
                self.assertIn("text", tok)
                self.assertIn("bg", tok)
                self.assertIn("border", tok)
                self.assertIn("progress_chunk", tok)

            # Contrast verification: Light mode text must differ from dark mode neon pastel
            self.assertNotEqual(dark_tok["text"], light_tok["text"], f"Status {status} text color must adapt for light mode")

        # Specific WCAG contrast checks
        unlocked_light = get_status_tokens("UNLOCKED", is_dark=False)
        self.assertEqual(unlocked_light["text"], "#1A7F37")

        curfew_light = get_status_tokens("CURFEW", is_dark=False)
        self.assertEqual(curfew_light["text"], "#6639BA")

        bypass_light = get_status_tokens("BYPASS", is_dark=False)
        self.assertEqual(bypass_light["text"], "#855800")

    def test_status_badge_style_generation(self):
        style_dark = get_status_badge_style("CURFEW", is_dark=True)
        style_light = get_status_badge_style("CURFEW", is_dark=False)

        self.assertIn("border-radius: 12px", style_dark)
        self.assertIn("#D2A8FF", style_dark)
        self.assertIn("#6639BA", style_light)

    def test_get_svg_pixmap_hidpi(self):
        from client.icons import get_svg_pixmap
        icon_path = os.path.join(ICONS_DIR, "shield.svg")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(os.path.dirname(__file__), "../resources/icons/shield.svg")

        # Test with dpr=2.0
        pm = get_svg_pixmap(icon_path, size=32, dpr=2.0)
        self.assertFalse(pm.isNull())
        self.assertEqual(pm.devicePixelRatio(), 2.0)
        self.assertEqual(pm.width(), 64)
        self.assertEqual(pm.height(), 64)

    def test_confirm_dialog_error_handling(self):
        from client.dialogs import ConfirmDomainRemovalDialog
        dlg = ConfirmDomainRemovalDialog(domain="facebook.com", reason_str="Curfew", phrase="unlock code")
        self.assertIsNotNone(dlg.input_field)
        self.assertFalse(dlg.input_field.property("error"))

        # Trigger confirm with wrong phrase
        dlg.input_field.setText("wrong phrase")
        dlg.on_confirm()
        self.assertTrue(dlg.input_field.property("error"))
        self.assertFalse(dlg.confirmed)

        # Typing text should clear the error state
        dlg.input_field.setText("wrong phrase 2")
        self.assertFalse(dlg.input_field.property("error"))

    def test_emergency_dialog_error_handling(self):
        from client.dialogs import EmergencyPromptDialog
        dlg = EmergencyPromptDialog(phrase="emergency pass")
        self.assertIsNotNone(dlg.input_field)
        self.assertFalse(dlg.input_field.property("error"))

        # Wrong phrase
        dlg.input_field.setText("wrong")
        dlg.on_confirm()
        self.assertTrue(dlg.input_field.property("error"))
        self.assertFalse(dlg.confirmed)

        # Type to clear
        dlg.input_field.setText("em")
        self.assertFalse(dlg.input_field.property("error"))

    def test_domains_tab_batch_add(self):
        from client.tabs import DomainsTab
        tab = DomainsTab(lambda: {}, lambda: {})
        tab.set_domains(["existing.com"])

        # Multiple domains separated by commas and spaces
        tab.domain_input.setText("apple.com, google.com; microsoft.com")
        tab.on_add_domain_clicked()

        domains = tab.get_domains()
        self.assertIn("apple.com", domains)
        self.assertIn("google.com", domains)
        self.assertIn("microsoft.com", domains)
        self.assertIn("existing.com", domains)
        self.assertEqual(len(domains), 4)

        # Batch preview label
        tab.domain_input.setText("site1.com, site2.com")
        self.assertIn("2", tab.domain_preview_lbl.text())

        # Trailing comma/space should still preview valid single domain
        tab.domain_input.setText("single.com, ")
        self.assertIn("single.com", tab.domain_preview_lbl.text())

    def test_selective_tab_batch_add(self):
        from client.tabs import SelectiveTab
        tab = SelectiveTab()
        tab.set_domains(["base.com"])

        tab.sel_add_input.setText("alpha.com, beta.com")
        tab.on_sel_add_domain_clicked()

        self.assertIn("alpha.com", tab.selected_selective_domains)
        self.assertIn("beta.com", tab.selected_selective_domains)
        self.assertIn("alpha.com", tab.blocked_domains)
        self.assertIn("beta.com", tab.blocked_domains)

    def test_rules_tab_preset_chips_highlighting(self):
        from client.tabs import RulesTab
        from PyQt6.QtCore import QTime
        tab = RulesTab()

        # Check initial boot highlight for 30m
        tab.boot_duration_spin.setValue(30)
        for pill, mins in tab.boot_preset_data:
            if mins == 30:
                self.assertEqual(pill.objectName(), "presetChipSmallSelected")
            else:
                self.assertEqual(pill.objectName(), "presetChipSmall")

        # Change to 45m
        tab.boot_duration_spin.setValue(45)
        for pill, mins in tab.boot_preset_data:
            if mins == 45:
                self.assertEqual(pill.objectName(), "presetChipSmallSelected")
            else:
                self.assertEqual(pill.objectName(), "presetChipSmall")

        # Curfew preset highlighting: match 23:00 - 07:00
        tab.curfew_start_time.setTime(QTime(23, 0))
        tab.curfew_end_time.setTime(QTime(7, 0))
        tab.update_curfew_summary()

        for pill, p_start, p_end in tab.curfew_preset_data:
            if p_start == (23, 0) and p_end == (7, 0):
                self.assertEqual(pill.objectName(), "presetChipSmallSelected")
            else:
                self.assertEqual(pill.objectName(), "presetChipSmall")

    def test_all_status_shield_svgs(self):
        res_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../resources"))
        required_shields = [
            "icon-active.svg", "icon-selective.svg", "icon-curfew.svg",
            "icon-boot.svg", "icon-bypass.svg", "icon-idle.svg",
            "icon-offline.svg", "focus-guard.svg"
        ]
        for s_name in required_shields:
            path = os.path.join(res_dir, s_name)
            self.assertTrue(os.path.isfile(path), f"Shield SVG missing: {s_name}")
            pm = get_svg_pixmap(path, size=28, dpr=1.0)
            self.assertFalse(pm.isNull(), f"Shield {s_name} failed to render")
            self.assertEqual(pm.width(), 28)

    def test_tray_status_icon_mapping(self):
        from unittest.mock import MagicMock
        from client.tray import FocusTrayApplet
        from client.ipc_client import FocusIPCClient
        mock_ipc = MagicMock(spec=FocusIPCClient)
        res_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../resources"))

        tray = FocusTrayApplet(mock_ipc, res_dir)

        # 1. UNLOCKED -> icon_idle
        mock_ipc.get_status.return_value = {"status": "ok", "state": "UNLOCKED", "reason": "FREE_TIME"}
        tray.refresh_status()
        self.assertEqual(tray.icon().cacheKey(), tray.icon_idle.cacheKey())

        # 2. SELECTIVE_LOCK -> icon_selective
        mock_ipc.get_status.return_value = {
            "status": "ok", "state": "LOCKED", "reason": "SELECTIVE_LOCK",
            "is_blocking": True, "selective_domains": ["reddit.com"]
        }
        tray.refresh_status()
        self.assertEqual(tray.icon().cacheKey(), tray.icon_selective.cacheKey())

        # 3. MANUAL_LOCK -> icon_active
        mock_ipc.get_status.return_value = {
            "status": "ok", "state": "LOCKED", "reason": "MANUAL_LOCK",
            "is_blocking": True
        }
        tray.refresh_status()
        self.assertEqual(tray.icon().cacheKey(), tray.icon_active.cacheKey())

        # 4. CURFEW -> icon_curfew
        mock_ipc.get_status.return_value = {
            "status": "ok", "state": "LOCKED", "reason": "CURFEW",
            "is_blocking": True
        }
        tray.refresh_status()
        self.assertEqual(tray.icon().cacheKey(), tray.icon_curfew.cacheKey())

        # 5. BOOT_COOLDOWN -> icon_boot
        mock_ipc.get_status.return_value = {
            "status": "ok", "state": "LOCKED", "reason": "BOOT_COOLDOWN",
            "is_blocking": True
        }
        tray.refresh_status()
        self.assertEqual(tray.icon().cacheKey(), tray.icon_boot.cacheKey())

        # 6. BYPASS -> icon_bypass
        mock_ipc.get_status.return_value = {
            "status": "ok", "state": "BYPASS", "reason": "USER_BYPASS"
        }
        tray.refresh_status()
        self.assertEqual(tray.icon().cacheKey(), tray.icon_bypass.cacheKey())

        # 7. OFFLINE -> icon_offline
        mock_ipc.get_status.return_value = {"status": "error"}
        tray.refresh_status()
        self.assertEqual(tray.icon().cacheKey(), tray.icon_offline.cacheKey())


if __name__ == "__main__":
    unittest.main()
