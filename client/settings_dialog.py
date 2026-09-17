"""
Focus-Guard Settings & Dashboard Dialog.
Unified KDE Plasma 6 / Wayland HIG Design System.
Modular Orchestrator coordinating Domains, Selective, Rules, and Dashboard tabs.
"""
import os
from typing import Dict, Any, List, Set

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QApplication, QToolTip, QComboBox
)
from PyQt6.QtGui import QIcon, QPalette, QKeySequence, QShortcut, QGuiApplication
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QEvent, QSettings, QRect

from client.ipc_client import FocusIPCClient
from client.autostart import (
    USER_AUTOSTART_PATH,
    SYSTEM_AUTOSTART_PATH,
    AUTOSTART_PATH,
    is_autostart_enabled,
    set_autostart_enabled,
)
from client.utils import sanitize_domain, format_human_time
from client.theme import get_theme_stylesheet, get_status_tokens, get_status_badge_style
from client.icons import get_themed_icon
from client.i18n import (
    t,
    get_configured_language_setting,
    set_configured_language_setting,
    resolve_active_language
)
from client.dialogs import (
    EmergencyPromptDialog,
    ConfirmDomainRemovalDialog,
    AboutDialog,
    UnsavedChangesDialog,
)
from client.tabs import (
    DomainsTab,
    SelectiveTab,
    RulesTab,
    DashboardTab,
)

__all__ = [
    "SettingsDialog",
    "UniversalToolTipFilter",
    "EmergencyPromptDialog",
    "ConfirmDomainRemovalDialog",
    "AboutDialog",
    "UnsavedChangesDialog",
    "sanitize_domain",
    "format_human_time",
    "is_autostart_enabled",
    "set_autostart_enabled",
    "USER_AUTOSTART_PATH",
    "SYSTEM_AUTOSTART_PATH",
    "AUTOSTART_PATH",
]


class UniversalToolTipFilter(QObject):
    """Enables tooltips to display across all widgets, including disabled ones."""
    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.ToolTip:
            gpos = event.globalPos()
            if isinstance(watched, QWidget):
                win = watched.window()
                if win:
                    for child in reversed(win.findChildren(QWidget)):
                        if child.isVisible() and child.rect().contains(child.mapFromGlobal(gpos)):
                            tip = child.toolTip()
                            if tip:
                                QToolTip.showText(gpos, tip, child)
                                return True
        return super().eventFilter(watched, event)


class SettingsDialog(QDialog):
    """Main Settings and Control Dashboard Dialog for Focus-Guard."""

    config_saved = pyqtSignal()
    theme_changed = pyqtSignal(str)
    language_changed = pyqtSignal(str)

    def __init__(self, ipc_client: FocusIPCClient, resource_dir: str, parent=None):
        super().__init__(parent)
        self.ipc = ipc_client
        self.resource_dir = resource_dir
        self.config_data: Dict[str, Any] = {}
        self.blocked_domains: List[str] = []

        self.setWindowTitle(t("app.window_title"))
        self.apply_theme_styles()
        self.setup_adaptive_geometry()

        # Universal tooltip filter for disabled buttons
        self.tooltip_filter = UniversalToolTipFilter(self)
        app_inst = QApplication.instance()
        if app_inst:
            app_inst.installEventFilter(self.tooltip_filter)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(14)

        # 1. Header
        self.setup_header()

        # 2. Modular Tabs
        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        
        self.domains_tab = DomainsTab(
            get_protection_status_fn=self.ipc.get_status,
            get_config_fn=self.ipc.get_config,
            parent=self
        )
        self.selective_tab = SelectiveTab(parent=self)
        self.rules_tab = RulesTab(parent=self)
        self.dashboard_tab = DashboardTab(parent=self)

        self.tabs.addTab(self.domains_tab, get_themed_icon("shield", self.is_dark_mode(), size=16), t("tab.domains"))
        self.tabs.addTab(self.selective_tab, get_themed_icon("sliders", self.is_dark_mode(), size=16), t("tab.selective"))
        self.tabs.addTab(self.rules_tab, get_themed_icon("clock", self.is_dark_mode(), size=16), t("tab.rules"))
        self.tabs.addTab(self.dashboard_tab, get_themed_icon("activity", self.is_dark_mode(), size=16), t("tab.dashboard"))

        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.main_layout.addWidget(self.tabs)

        # 3. Connect signals between tabs and controller
        self._connect_tab_signals()

        # 4. Bottom Bar
        self.setup_bottom_bar()

        # 5. Keyboard Shortcuts
        self._setup_shortcuts()

        # 6. Initial config & status load
        self.load_configuration()
        self.refresh_live_status()

        # 7. Live poll timer
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.refresh_live_status)
        self.poll_timer.start(1500)

    # -------------------------------------------------------------------------
    # Backward Compatibility Properties
    # -------------------------------------------------------------------------
    @property
    def domain_input(self):
        return self.domains_tab.domain_input

    @property
    def search_input(self):
        return self.domains_tab.search_input

    # -------------------------------------------------------------------------
    # Styling & Setup
    # -------------------------------------------------------------------------
    def get_theme_mode(self) -> str:
        settings = QSettings("FocusGuard", "FocusGuardTray")
        return settings.value("theme_mode", "auto")

    def is_dark_mode(self) -> bool:
        mode = self.get_theme_mode()
        if mode == "dark":
            return True
        elif mode == "light":
            return False
        bg = self.palette().color(QPalette.ColorRole.Window)
        return bg.lightness() < 128

    def on_theme_changed(self, index: int):
        mode = self.theme_combo.currentData()
        settings = QSettings("FocusGuard", "FocusGuardTray")
        settings.setValue("theme_mode", mode)
        self.apply_theme_styles()
        if hasattr(self, "domains_tab"):
            self.domains_tab.render_domains_list()
        if hasattr(self, "selective_tab"):
            self.selective_tab.render_selective_domains_list()
        self.refresh_live_status()
        self.theme_changed.emit(mode)

    def _update_tab_icons(self):
        is_dark = self.is_dark_mode()
        if hasattr(self, "tabs") and self.tabs.count() >= 4:
            self.tabs.setTabIcon(0, get_themed_icon("shield", is_dark, size=16))
            self.tabs.setTabIcon(1, get_themed_icon("sliders", is_dark, size=16))
            self.tabs.setTabIcon(2, get_themed_icon("clock", is_dark, size=16))
            self.tabs.setTabIcon(3, get_themed_icon("activity", is_dark, size=16))

    def _update_theme_combo(self):
        if not hasattr(self, "theme_combo"):
            return
        is_dark = self.is_dark_mode()
        cur_mode = self.theme_combo.currentData() if self.theme_combo.count() > 0 else self.get_theme_mode()
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        self.theme_combo.addItem(get_themed_icon("monitor", is_dark, size=14), t("app.theme_auto"), "auto")
        self.theme_combo.addItem(get_themed_icon("moon", is_dark, size=14), t("app.theme_dark"), "dark")
        self.theme_combo.addItem(get_themed_icon("sun", is_dark, size=14), t("app.theme_light"), "light")
        cur_idx = self.theme_combo.findData(cur_mode)
        if cur_idx >= 0:
            self.theme_combo.setCurrentIndex(cur_idx)
        self.theme_combo.blockSignals(False)

    def _update_lang_combo(self):
        if not hasattr(self, "lang_combo"):
            return
        is_dark = self.is_dark_mode()
        cur_lang = self.lang_combo.currentData() if self.lang_combo.count() > 0 else get_configured_language_setting()
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()
        self.lang_combo.addItem(get_themed_icon("globe", is_dark, size=14), t("app.lang_auto"), "auto")
        self.lang_combo.addItem(get_themed_icon("globe", is_dark, size=14), t("app.lang_es"), "es")
        self.lang_combo.addItem(get_themed_icon("globe", is_dark, size=14), t("app.lang_en"), "en")
        cur_idx = self.lang_combo.findData(cur_lang)
        if cur_idx >= 0:
            self.lang_combo.setCurrentIndex(cur_idx)
        self.lang_combo.blockSignals(False)

    def on_language_changed(self, index: int):
        lang_code = self.lang_combo.currentData()
        set_configured_language_setting(lang_code)
        self.retranslate_ui()
        self.language_changed.emit(lang_code)

    def retranslate_ui(self):
        """Refreshes all texts, tab titles, buttons, and child tabs dynamically."""
        self.setWindowTitle(t("app.window_title"))
        if hasattr(self, "sub_lbl"):
            self.sub_lbl.setText(t("app.subtitle"))
        if hasattr(self, "theme_combo"):
            self.theme_combo.setToolTip(t("app.theme_tooltip"))
            self._update_theme_combo()
        if hasattr(self, "lang_combo"):
            self.lang_combo.setToolTip(t("app.lang_tooltip"))
            self._update_lang_combo()
        if hasattr(self, "tabs") and self.tabs.count() >= 4:
            self.tabs.setTabText(0, t("tab.domains"))
            self.tabs.setTabText(1, t("tab.selective"))
            self.tabs.setTabText(2, t("tab.rules"))
            self.tabs.setTabText(3, t("tab.dashboard"))
        if hasattr(self, "close_btn"):
            self.close_btn.setText(t("app.btn_close"))
        if hasattr(self, "discard_btn"):
            self.discard_btn.setText(t("app.btn_discard"))
            self.discard_btn.setToolTip(t("app.btn_discard_tooltip"))
        if hasattr(self, "save_btn"):
            self.save_btn.setText(t("app.btn_save"))
        if hasattr(self, "save_feedback_lbl"):
            self.save_feedback_lbl.setText(t("app.sync_feedback"))

        if hasattr(self, "domains_tab") and hasattr(self.domains_tab, "retranslate_ui"):
            self.domains_tab.retranslate_ui()
        if hasattr(self, "selective_tab") and hasattr(self.selective_tab, "retranslate_ui"):
            self.selective_tab.retranslate_ui()
        if hasattr(self, "rules_tab") and hasattr(self.rules_tab, "retranslate_ui"):
            self.rules_tab.retranslate_ui()
        if hasattr(self, "dashboard_tab") and hasattr(self.dashboard_tab, "retranslate_ui"):
            self.dashboard_tab.retranslate_ui()

        self.refresh_live_status()

    def apply_theme_styles(self):
        is_dark = self.is_dark_mode()
        stylesheet = get_theme_stylesheet(is_dark, self.resource_dir)
        self.setStyleSheet(stylesheet)
        self._update_tab_icons()
        self._update_theme_combo()
        self._update_lang_combo()
        if hasattr(self, "discard_btn"):
            self.discard_btn.setIcon(get_themed_icon("undo", is_dark, role="secondary", size=14))
        if hasattr(self, "save_btn"):
            self.save_btn.setIcon(get_themed_icon("check", is_dark, role="white", size=14))
        if hasattr(self, "domains_tab") and hasattr(self.domains_tab, "update_icons"):
            self.domains_tab.update_icons(is_dark)
        if hasattr(self, "dashboard_tab") and hasattr(self.dashboard_tab, "update_icons"):
            self.dashboard_tab.update_icons(is_dark)
        if hasattr(self, "rules_tab") and hasattr(self.rules_tab, "update_icons"):
            self.rules_tab.update_icons(is_dark)
        if hasattr(self, "selective_tab") and hasattr(self.selective_tab, "update_icons"):
            self.selective_tab.update_icons(is_dark)

    def setup_header(self):
        header = QHBoxLayout()
        header.setSpacing(12)

        self.header_icon_lbl = QLabel()
        icon_path = os.path.join(self.resource_dir, "icon-active.svg")
        if os.path.exists(icon_path):
            self.header_icon_lbl.setPixmap(QIcon(icon_path).pixmap(28, 28))
        header.addWidget(self.header_icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_lbl = QLabel("Focus-Guard")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
        self.sub_lbl = QLabel(t("app.subtitle"))
        self.sub_lbl.setObjectName("cardDesc")
        title_box.addWidget(title_lbl)
        title_box.addWidget(self.sub_lbl)
        header.addLayout(title_box)

        header.addStretch()

        # Language selector with vector globe icon
        self.lang_combo = QComboBox()
        self.lang_combo.setToolTip(t("app.lang_tooltip"))
        self._update_lang_combo()
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
        header.addWidget(self.lang_combo)

        # Theme mode selector (Auto / Dark / Light) with vector icons
        self.theme_combo = QComboBox()
        self.theme_combo.setToolTip(t("app.theme_tooltip"))
        self._update_theme_combo()
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        header.addWidget(self.theme_combo)

        self.status_badge = QLabel(t("app.status_checking"))
        self.status_badge.setObjectName("statusBadge")
        header.addWidget(self.status_badge)

        self.main_layout.addLayout(header)

    def setup_bottom_bar(self):
        bottom = QHBoxLayout()
        bottom.setSpacing(10)

        self.save_feedback_lbl = QLabel(t("app.sync_feedback"))
        self.save_feedback_lbl.setObjectName("cardDesc")
        bottom.addWidget(self.save_feedback_lbl)

        bottom.addStretch()

        self.close_btn = QPushButton(t("app.btn_close"))
        self.close_btn.setObjectName("secondaryBtn")
        self.close_btn.clicked.connect(self.close)
        bottom.addWidget(self.close_btn)

        self.discard_btn = QPushButton(t("app.btn_discard"))
        self.discard_btn.setObjectName("secondaryBtn")
        self.discard_btn.setIcon(get_themed_icon("undo", self.is_dark_mode(), role="secondary", size=14))
        self.discard_btn.setToolTip(t("app.btn_discard_tooltip"))
        self.discard_btn.clicked.connect(self.on_discard_clicked)
        self.discard_btn.setVisible(False)
        bottom.addWidget(self.discard_btn)

        self.save_btn = QPushButton(t("app.btn_save"))
        self.save_btn.setObjectName("primaryBtn")
        self.save_btn.setIcon(get_themed_icon("check", self.is_dark_mode(), role="white", size=14))
        self.save_btn.clicked.connect(self.on_save_clicked)
        bottom.addWidget(self.save_btn)

        self.main_layout.addLayout(bottom)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+S"), self, self.on_save_clicked)
        QShortcut(QKeySequence("Escape"), self, self.close)
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self.tabs.setCurrentIndex(0))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self.tabs.setCurrentIndex(1))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self.tabs.setCurrentIndex(2))
        QShortcut(QKeySequence("Ctrl+4"), self, lambda: self.tabs.setCurrentIndex(3))
        QShortcut(QKeySequence("Ctrl+N"), self, self.focus_domain_input)
        QShortcut(QKeySequence("Ctrl+F"), self, self.focus_search_or_domain_input)

    def _connect_tab_signals(self):
        # Domains Tab
        self.domains_tab.domains_changed.connect(self.on_domains_changed)
        self.domains_tab.auto_save_requested.connect(self.on_domains_auto_save)

        # Selective Tab
        self.selective_tab.start_lock_requested.connect(self.on_start_selective_lock)
        self.selective_tab.cancel_lock_requested.connect(self.on_cancel_selective_lock)
        self.selective_tab.domain_added.connect(self.on_selective_domain_added)

        # Rules Tab
        self.rules_tab.rules_changed.connect(self.check_for_unsaved_changes)

        # Dashboard Tab
        self.dashboard_tab.focus_session_requested.connect(self.start_focus_session)
        self.dashboard_tab.primary_action_clicked.connect(self.on_primary_action_clicked)
        self.dashboard_tab.secondary_action_clicked.connect(self.on_secondary_action_clicked)
        self.dashboard_tab.stop_focus_clicked.connect(self.on_stop_focus_clicked)

    # -------------------------------------------------------------------------
    # Tab Events & Shortcuts
    # -------------------------------------------------------------------------
    def on_tab_changed(self, index: int):
        if index == 0:
            self.domains_tab.render_domains_list()
        elif index == 1:
            self.selective_tab.render_selective_domains_list()

    def focus_domain_input(self):
        self.tabs.setCurrentIndex(0)
        self.domains_tab.focus_domain_input()

    def focus_search_or_domain_input(self):
        self.tabs.setCurrentIndex(0)
        self.domains_tab.focus_search_or_domain_input()

    # -------------------------------------------------------------------------
    # Domains & Selective Synchronization
    # -------------------------------------------------------------------------
    def on_domains_changed(self, domains: List[str]):
        self.blocked_domains = list(domains)
        self.selective_tab.set_domains(self.blocked_domains)
        self.refresh_live_status()

    def on_domains_auto_save(self, domains: List[str], feedback_msg: str):
        self.blocked_domains = list(domains)
        self.config_data["blocked_domains"] = self.blocked_domains
        res = self.ipc.save_config(self.config_data)
        if res.get("status") == "ok":
            self.config_saved.emit()
            self.domains_tab.set_feedback_message(feedback_msg, is_success=True)
        else:
            self.domains_tab.set_feedback_message(t("app.sync_error"), is_success=False)
        self.selective_tab.set_domains(self.blocked_domains)

    def on_selective_domain_added(self, domain: str):
        if domain not in self.blocked_domains:
            self.blocked_domains.append(domain)
            self.config_data["blocked_domains"] = self.blocked_domains
            self.ipc.save_config(self.config_data)
            self.domains_tab.set_domains(self.blocked_domains)
            self.config_saved.emit()

    def on_start_selective_lock(self, domains: List[str], duration_minutes: int):
        res = self.ipc.request_selective_lock(domains, duration_minutes)
        if res.get("status") == "ok":
            plural = t("selective.plural_site") if len(domains) == 1 else t("selective.plural_sites")
            self.selective_tab.set_feedback(t("selective.feedback_lock_started", count=len(domains), plural=plural), is_success=True)
            self.refresh_live_status()
            self.config_saved.emit()
        else:
            err = res.get("message") or res.get("error") or t("selective.feedback_lock_error")
            self.selective_tab.set_feedback(f"{t('tray.notify_error_title')}: {err}", is_success=False)

    def on_cancel_selective_lock(self):
        res = self.ipc.cancel_selective_lock()
        if res.get("status") == "ok":
            self.selective_tab.set_feedback(t("selective.feedback_lock_cancelled"), is_success=True)
            self.refresh_live_status()
            self.config_saved.emit()
        else:
            err = res.get("message") or res.get("error") or t("selective.feedback_cancel_error")
            self.selective_tab.set_feedback(f"{t('tray.notify_error_title')}: {err}", is_success=False)

    # -------------------------------------------------------------------------
    # Dashboard Actions
    # -------------------------------------------------------------------------
    def start_focus_session(self, minutes: int):
        self.ipc.lock_now(duration_minutes=minutes)
        if minutes > 0:
            self.dashboard_tab.show_feedback(t("dash.feedback_session_started", minutes=minutes))
        else:
            self.dashboard_tab.show_feedback(t("dash.feedback_session_indef"))
        self.refresh_live_status()

    def on_primary_action_clicked(self):
        res = self.ipc.get_status()
        state = res.get("state", "UNLOCKED")
        reason = res.get("reason", "FREE_TIME")

        if state == "UNLOCKED":
            self.ipc.lock_now()
            self.dashboard_tab.show_feedback(t("dash.feedback_focus_active"))
        elif state == "BYPASS":
            self.ipc.cancel_bypass()
            self.dashboard_tab.show_feedback(t("dash.feedback_break_ended"))
        elif reason == "MANUAL_LOCK":
            self.ipc.unlock_now()
            self.dashboard_tab.show_feedback(t("dash.feedback_sites_unlocked"))

        self.refresh_live_status()

    def on_secondary_action_clicked(self):
        res = self.ipc.get_status()
        in_curfew = res.get("in_curfew", False)

        if in_curfew:
            rules = self.rules_tab.get_rules_dict()
            phrase = rules.get("bypasses", {}).get("emergency_phrase", "necesito desbloqueo de emergencia")
            dialog = EmergencyPromptDialog(phrase=phrase, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.confirmed:
                emerg_res = self.ipc.request_emergency_bypass(15)
                if emerg_res.get("status") == "ok":
                    self.dashboard_tab.show_feedback(t("dash.feedback_emergency_granted"))
                else:
                    self.dashboard_tab.show_feedback(t("dash.feedback_emergency_failed"))
        else:
            bypass_res = self.ipc.request_bypass(15)
            if bypass_res.get("status") == "ok":
                self.dashboard_tab.show_feedback(t("dash.feedback_break_started", minutes=15))
            else:
                self.dashboard_tab.show_feedback(bypass_res.get("message") or t("dash.feedback_break_failed"))

        self.refresh_live_status()

    def on_stop_focus_clicked(self):
        res_status = self.ipc.get_status()
        if res_status.get("is_selective"):
            res = self.ipc.cancel_selective_lock()
        else:
            res = self.ipc.unlock_now()
        if res.get("status") == "ok":
            self.dashboard_tab.show_feedback(t("dash.feedback_session_ended"))
            self.refresh_live_status()

    # -------------------------------------------------------------------------
    # Configuration Loading & Saving
    # -------------------------------------------------------------------------
    def load_configuration(self):
        res = self.ipc.get_config()
        if res.get("status") == "ok":
            self.config_data = res.get("config", {})
            self.blocked_domains = list(self.config_data.get("blocked_domains", []))
            self.domains_tab.set_domains(self.blocked_domains)
            self.selective_tab.set_domains(self.blocked_domains)
            self.rules_tab.load_rules(self.config_data)
            self.check_for_unsaved_changes()

    def on_save_clicked(self):
        rules_dict = self.rules_tab.get_rules_dict()
        updated_config = dict(self.config_data)
        updated_config["blocked_domains"] = self.blocked_domains
        updated_config["curfew"] = rules_dict.get("curfew", {})
        updated_config["boot_cooldown"] = rules_dict.get("boot_cooldown", {})
        updated_config["bypasses"] = rules_dict.get("bypasses", {})

        res = self.ipc.save_config(updated_config)
        if res.get("status") == "ok":
            self.config_data = updated_config
            self.rules_tab.load_rules(self.config_data)
            self.config_saved.emit()
            self.check_for_unsaved_changes()
            self.save_feedback_lbl.setStyleSheet("font-size: 11px; color: #2EA043; font-weight: 600;")
            self.save_feedback_lbl.setText(t("app.rules_saved_feedback"))
            QTimer.singleShot(3000, lambda: self.check_for_unsaved_changes())
        else:
            self.save_feedback_lbl.setStyleSheet("font-size: 11px; color: #F85149; font-weight: 600;")
            self.save_feedback_lbl.setText(f"{t('tray.notify_error_title')}: {res.get('error') or t('app.sync_error')}")

    def on_discard_clicked(self):
        """Reverts modified fields in the rules tab to loaded config."""
        if not hasattr(self, "config_data") or not self.config_data:
            return
        self.rules_tab.load_rules(self.config_data)
        self.check_for_unsaved_changes()
        self.save_feedback_lbl.setText(t("app.discard_feedback"))
        self.save_feedback_lbl.setStyleSheet("font-size: 11px; color: #8B949E; font-weight: 500;")
        QTimer.singleShot(2500, lambda: self.check_for_unsaved_changes())

    def has_unsaved_changes(self) -> bool:
        """Dynamically evaluates if rules form inputs differ from saved config."""
        if not hasattr(self, "rules_tab"):
            return False
        return self.rules_tab.has_unsaved_changes()

    def check_for_unsaved_changes(self):
        """Updates save and discard buttons and feedback according to current unsaved state."""
        has_unsaved = self.has_unsaved_changes()

        if has_unsaved:
            if hasattr(self, "discard_btn"):
                self.discard_btn.setVisible(True)
            self.save_btn.setEnabled(True)
            self.save_btn.setText(t("app.btn_save"))
            self.save_btn.setStyleSheet("")
            self.save_feedback_lbl.setText(t("app.unsaved_feedback"))
            self.save_feedback_lbl.setStyleSheet("font-size: 11px; color: #D29922; font-weight: 600;")
        else:
            if hasattr(self, "discard_btn"):
                self.discard_btn.setVisible(False)
            self.save_btn.setEnabled(False)
            self.save_btn.setText(t("app.btn_saved"))
            self.save_btn.setStyleSheet("")
            self.save_feedback_lbl.setText(t("app.sync_feedback"))
            self.save_feedback_lbl.setStyleSheet("font-size: 11px; color: #8B949E; font-weight: 500;")

    # -------------------------------------------------------------------------
    # Dialog Lifecycle & Unsaved Dialog Prompts
    # -------------------------------------------------------------------------
    def closeEvent(self, event):
        """Intercepts window close to prompt user about unsaved changes."""
        if self.has_unsaved_changes():
            dlg = UnsavedChangesDialog(parent=self)
            dlg.exec()
            if dlg.action == "save":
                self.on_save_clicked()
                event.accept()
            elif dlg.action == "discard":
                event.accept()
            else:
                event.ignore()
                return
        else:
            event.accept()

        if event.isAccepted():
            self.save_current_geometry()
            if hasattr(self, "poll_timer") and self.poll_timer.isActive():
                self.poll_timer.stop()
            app_inst = QApplication.instance()
            if app_inst and hasattr(self, "tooltip_filter"):
                try:
                    app_inst.removeEventFilter(self.tooltip_filter)
                except Exception:
                    pass

    def showEvent(self, event):
        """Ensures polling and event filter are active when window is displayed."""
        super().showEvent(event)
        if hasattr(self, "poll_timer") and not self.poll_timer.isActive():
            self.poll_timer.start(1500)
            self.refresh_live_status()
        app_inst = QApplication.instance()
        if app_inst and hasattr(self, "tooltip_filter"):
            app_inst.removeEventFilter(self.tooltip_filter)
            app_inst.installEventFilter(self.tooltip_filter)

    def reject(self):
        """Intercepts Escape key to prompt user about unsaved changes."""
        self.save_current_geometry()
        if self.has_unsaved_changes():
            dlg = UnsavedChangesDialog(parent=self)
            dlg.exec()
            if dlg.action == "save":
                self.on_save_clicked()
                super().reject()
            elif dlg.action == "discard":
                super().reject()
            else:
                return
        else:
            super().reject()

    def save_current_geometry(self):
        """Persists the current window geometry to QSettings."""
        try:
            settings = QSettings("FocusGuard", "FocusGuardTray")
            settings.setValue("window_geometry", self.saveGeometry())
        except Exception:
            pass

    def setup_adaptive_geometry(self):
        """Calculates optimal window sizing and positioning based on the active screen's available geometry."""
        screen = self.screen() or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        avail_w = max(640, avail.width())
        avail_h = max(480, avail.height())

        # Adaptive minimum dimensions:
        # Ensures window fits comfortably on compact screens (e.g. 1366x768 or 1080p @ 150%)
        # without pushing the bottom action bar below taskbars or screen edge.
        min_w = min(640, int(avail_w * 0.90))
        min_h = min(480, int(avail_h * 0.82))
        self.setMinimumSize(min_w, min_h)

        # Adaptive initial target dimensions:
        if avail_h <= 768 or avail_w <= 1366:
            # 768p / 720p / 150% scaled displays
            def_w = min(740, int(avail_w * 0.88))
            def_h = min(580, int(avail_h * 0.86))
        elif avail_w >= 2400 or avail_h >= 1300:
            # 2K / 4K / Ultrawide displays
            def_w = min(920, int(avail_w * 0.45))
            def_h = min(780, int(avail_h * 0.65))
        else:
            # Full HD (1080p @ 100% or 125%)
            def_w = min(800, int(avail_w * 0.60))
            def_h = min(680, int(avail_h * 0.75))

        # Check for user-persisted window geometry
        settings = QSettings("FocusGuard", "FocusGuardTray")
        saved_geom = settings.value("window_geometry")
        restored = False
        if saved_geom:
            try:
                if self.restoreGeometry(saved_geom):
                    frame = self.frameGeometry()
                    # Validate that the restored window is still within current screen limits
                    if (avail.intersects(frame) and
                            frame.width() <= avail_w and
                            frame.height() <= avail_h and
                            frame.width() >= min_w and
                            frame.height() >= min_h):
                        restored = True
            except Exception:
                restored = False

        if not restored:
            self.resize(def_w, def_h)
            # Center inside available screen bounds (respecting docks, taskbars)
            x = avail.x() + (avail_w - def_w) // 2
            y = avail.y() + (avail_h - def_h) // 2
            self.move(x, y)

    # -------------------------------------------------------------------------
    # Live Status Refresh
    # -------------------------------------------------------------------------
    def refresh_live_status(self):
        is_dark = self.is_dark_mode()
        res = self.ipc.get_status()
        if res.get("status") != "ok":
            self.status_badge.setText(t("app.status_offline"))
            self.status_badge.setStyleSheet(get_status_badge_style("OFFLINE", is_dark))
            icon_off = os.path.join(self.resource_dir, "icon-offline.svg")
            if os.path.exists(icon_off):
                self.header_icon_lbl.setPixmap(QIcon(icon_off).pixmap(28, 28))
            self.dashboard_tab.update_status(res, self.config_data, len(self.blocked_domains), False)
            return

        state = res.get("state", "UNLOCKED")
        reason = res.get("reason", "FREE_TIME")
        rem = res.get("remaining_seconds", 0)
        target = res.get("target_time_str", "")
        is_blocking = res.get("is_blocking", False)

        human_time = format_human_time(rem)

        # 1. Header Badge: UNLOCKED
        if state == "UNLOCKED":
            self.status_badge.setText(t("dash.status_free"))
            self.status_badge.setStyleSheet(get_status_badge_style("UNLOCKED", is_dark))
            icon_idle = os.path.join(self.resource_dir, "icon-idle.svg")
            if os.path.exists(icon_idle):
                self.header_icon_lbl.setPixmap(QIcon(icon_idle).pixmap(28, 28))

        # 2. Header Badge: BYPASS
        elif state == "BYPASS":
            self.status_badge.setText(t("dash.status_pause"))
            self.status_badge.setStyleSheet(get_status_badge_style("BYPASS", is_dark))
            icon_byp = os.path.join(self.resource_dir, "icon-bypass.svg")
            if os.path.exists(icon_byp):
                self.header_icon_lbl.setPixmap(QIcon(icon_byp).pixmap(28, 28))

        # 3. Header Badge: LOCKED
        elif is_blocking:
            if reason == "CURFEW":
                self.status_badge.setText(t("dash.status_curfew"))
                self.status_badge.setStyleSheet(get_status_badge_style("CURFEW", is_dark))
                icon_curf = os.path.join(self.resource_dir, "icon-curfew.svg")
                if os.path.exists(icon_curf):
                    self.header_icon_lbl.setPixmap(QIcon(icon_curf).pixmap(28, 28))
            elif reason == "BOOT_COOLDOWN":
                self.status_badge.setText(t("dash.status_boot"))
                self.status_badge.setStyleSheet(get_status_badge_style("BOOT_COOLDOWN", is_dark))
                icon_bt = os.path.join(self.resource_dir, "icon-boot.svg")
                if os.path.exists(icon_bt):
                    self.header_icon_lbl.setPixmap(QIcon(icon_bt).pixmap(28, 28))
            elif reason == "MANUAL_LOCK":
                self.status_badge.setText(t("dash.status_focus"))
                self.status_badge.setStyleSheet(get_status_badge_style("MANUAL_LOCK", is_dark))
                icon_act = os.path.join(self.resource_dir, "icon-active.svg")
                if os.path.exists(icon_act):
                    self.header_icon_lbl.setPixmap(QIcon(icon_act).pixmap(28, 28))
            elif reason == "SELECTIVE_LOCK":
                self.status_badge.setText(t("dash.status_selective"))
                self.status_badge.setStyleSheet(get_status_badge_style("SELECTIVE_LOCK", is_dark))
                icon_act = os.path.join(self.resource_dir, "icon-active.svg")
                if os.path.exists(icon_act):
                    self.header_icon_lbl.setPixmap(QIcon(icon_act).pixmap(28, 28))

        # Dashboard Tab Status Update
        rules = self.rules_tab.get_rules_dict()
        curfew_emerg = rules.get("bypasses", {}).get("allow_during_curfew", False)
        self.dashboard_tab.update_status(res, self.config_data, len(self.blocked_domains), curfew_emerg)

        # Selective Tab Status Update
        is_selective = res.get("is_selective", False)
        selective_domains = res.get("selective_domains", [])
        is_indefinite = res.get("is_indefinite", False)
        has_pending_sel = res.get("has_pending_selective", False)
        self.selective_tab.update_active_status(
            is_selective=is_selective,
            remaining_sec=rem,
            selective_domains=selective_domains,
            target_time=target,
            human_time=human_time,
            is_indefinite=is_indefinite,
            has_pending_selective=has_pending_sel
        )
