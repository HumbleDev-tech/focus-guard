"""
Focus-Guard Settings & Dashboard Dialog.
Unified KDE Plasma 6 / Wayland HIG Design System.
Modular Orchestrator coordinating Domains, Selective, Rules, and Dashboard tabs.
"""
import os
from typing import Dict, Any, List, Set

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QWidget, QApplication, QToolTip
)
from PyQt6.QtGui import QIcon, QPalette, QKeySequence, QShortcut
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QEvent

from client.ipc_client import FocusIPCClient
from client.autostart import (
    USER_AUTOSTART_PATH,
    SYSTEM_AUTOSTART_PATH,
    AUTOSTART_PATH,
    is_autostart_enabled,
    set_autostart_enabled,
)
from client.utils import sanitize_domain, format_human_time
from client.theme import get_theme_stylesheet
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

    def __init__(self, ipc_client: FocusIPCClient, resource_dir: str, parent=None):
        super().__init__(parent)
        self.ipc = ipc_client
        self.resource_dir = resource_dir
        self.config_data: Dict[str, Any] = {}
        self.blocked_domains: List[str] = []

        self.setWindowTitle("Panel de Control — Focus-Guard")
        self.setMinimumSize(720, 640)
        self.resize(760, 680)

        self.apply_theme_styles()

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
        
        self.domains_tab = DomainsTab(
            get_protection_status_fn=self.ipc.get_status,
            get_config_fn=self.ipc.get_config,
            parent=self
        )
        self.selective_tab = SelectiveTab(parent=self)
        self.rules_tab = RulesTab(parent=self)
        self.dashboard_tab = DashboardTab(parent=self)

        self.tabs.addTab(self.domains_tab, "Sitios Bloqueados")
        self.tabs.addTab(self.selective_tab, "Bloqueo Selectivo")
        self.tabs.addTab(self.rules_tab, "Horarios y Reglas")
        self.tabs.addTab(self.dashboard_tab, "Estado y Control")

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
    def is_dark_mode(self) -> bool:
        bg = self.palette().color(QPalette.ColorRole.Window)
        return bg.lightness() < 128

    def apply_theme_styles(self):
        stylesheet = get_theme_stylesheet(self.is_dark_mode(), self.resource_dir)
        self.setStyleSheet(stylesheet)

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
        sub_lbl = QLabel("Panel de Control y Reglas")
        sub_lbl.setObjectName("cardDesc")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header.addLayout(title_box)

        header.addStretch()

        self.status_badge = QLabel("VERIFICANDO")
        self.status_badge.setObjectName("statusBadge")
        header.addWidget(self.status_badge)

        self.main_layout.addLayout(header)

    def setup_bottom_bar(self):
        bottom = QHBoxLayout()
        bottom.setSpacing(10)

        self.save_feedback_lbl = QLabel("Cambios sincronizados con el demonio")
        self.save_feedback_lbl.setObjectName("cardDesc")
        bottom.addWidget(self.save_feedback_lbl)

        bottom.addStretch()

        close_btn = QPushButton("Cerrar (Esc)")
        close_btn.setObjectName("secondaryBtn")
        close_btn.clicked.connect(self.close)
        bottom.addWidget(close_btn)

        self.discard_btn = QPushButton("Descartar")
        self.discard_btn.setObjectName("secondaryBtn")
        self.discard_btn.setToolTip("Revertir y descartar las modificaciones no guardadas")
        self.discard_btn.clicked.connect(self.on_discard_clicked)
        self.discard_btn.setVisible(False)
        bottom.addWidget(self.discard_btn)

        self.save_btn = QPushButton("Guardar Reglas (Ctrl+S)")
        self.save_btn.setObjectName("primaryBtn")
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
            self.domains_tab.set_feedback_message("Error al sincronizar con el demonio", is_success=False)
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
            self.selective_tab.set_feedback(f"Bloqueo activado ({len(domains)} sitios)", is_success=True)
            self.refresh_live_status()
            self.config_saved.emit()
        else:
            err = res.get("message") or res.get("error") or "Error al activar el bloqueo"
            self.selective_tab.set_feedback(f"Error: {err}", is_success=False)

    def on_cancel_selective_lock(self):
        res = self.ipc.cancel_selective_lock()
        if res.get("status") == "ok":
            self.selective_tab.set_feedback("Bloqueo selectivo finalizado", is_success=True)
            self.refresh_live_status()
            self.config_saved.emit()
        else:
            err = res.get("message") or res.get("error") or "Error al finalizar el bloqueo"
            self.selective_tab.set_feedback(f"Error: {err}", is_success=False)

    # -------------------------------------------------------------------------
    # Dashboard Actions
    # -------------------------------------------------------------------------
    def start_focus_session(self, minutes: int):
        self.ipc.lock_now(duration_minutes=minutes)
        self.dashboard_tab.show_feedback(f"Sesión de enfoque de {minutes} minutos iniciada.")
        self.refresh_live_status()

    def on_primary_action_clicked(self):
        res = self.ipc.get_status()
        state = res.get("state", "UNLOCKED")
        reason = res.get("reason", "FREE_TIME")

        if state == "UNLOCKED":
            self.ipc.lock_now()
            self.dashboard_tab.show_feedback("Modo Focus activado.")
        elif state == "BYPASS":
            self.ipc.cancel_bypass()
            self.dashboard_tab.show_feedback("Descanso finalizado. Modo Focus reactivado.")
        elif reason == "MANUAL_LOCK":
            self.ipc.unlock_now()
            self.dashboard_tab.show_feedback("Sitios desbloqueados.")

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
                    self.dashboard_tab.show_feedback("Desbloqueo de emergencia concedido por 15 minutos.")
                else:
                    self.dashboard_tab.show_feedback("No se pudo activar el desbloqueo.")
        else:
            bypass_res = self.ipc.request_bypass(15)
            if bypass_res.get("status") == "ok":
                self.dashboard_tab.show_feedback("Descanso de 15 minutos activado.")
            else:
                self.dashboard_tab.show_feedback(bypass_res.get("message", "No se pudo activar."))

        self.refresh_live_status()

    def on_stop_focus_clicked(self):
        res_status = self.ipc.get_status()
        if res_status.get("is_selective"):
            res = self.ipc.cancel_selective_lock()
        else:
            res = self.ipc.unlock_now()
        if res.get("status") == "ok":
            self.dashboard_tab.show_feedback("Sesión finalizada")
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
            self.save_feedback_lbl.setText("Reglas guardadas y sincronizadas")
            QTimer.singleShot(3000, lambda: self.check_for_unsaved_changes())
        else:
            self.save_feedback_lbl.setStyleSheet("font-size: 11px; color: #F85149; font-weight: 600;")
            self.save_feedback_lbl.setText(f"Error: {res.get('error', 'No se pudo guardar')}")

    def on_discard_clicked(self):
        """Reverts modified fields in the rules tab to loaded config."""
        if not hasattr(self, "config_data") or not self.config_data:
            return
        self.rules_tab.load_rules(self.config_data)
        self.check_for_unsaved_changes()
        self.save_feedback_lbl.setText("Cambios descartados")
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
            self.save_btn.setText("Guardar Reglas (Ctrl+S)")
            self.save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #388BFD;
                    color: #FFFFFF;
                    font-weight: 600;
                    font-size: 12px;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 18px;
                }
                QPushButton:hover {
                    background-color: #1F6FEB;
                }
            """)
            self.save_feedback_lbl.setText("Cambios sin guardar")
            self.save_feedback_lbl.setStyleSheet("font-size: 11px; color: #D29922; font-weight: 600;")
        else:
            if hasattr(self, "discard_btn"):
                self.discard_btn.setVisible(False)
            self.save_btn.setEnabled(False)
            self.save_btn.setText("Guardado")
            self.save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #161B22;
                    color: #6E7681;
                    font-weight: 600;
                    font-size: 12px;
                    border: 1px solid #30363D;
                    border-radius: 6px;
                    padding: 8px 18px;
                }
            """)
            self.save_feedback_lbl.setText("Cambios sincronizados")
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
        else:
            event.accept()

    def reject(self):
        """Intercepts Escape key to prompt user about unsaved changes."""
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

    # -------------------------------------------------------------------------
    # Live Status Refresh
    # -------------------------------------------------------------------------
    def refresh_live_status(self):
        res = self.ipc.get_status()
        if res.get("status") != "ok":
            self.status_badge.setText("FUERA DE LÍNEA")
            self.status_badge.setStyleSheet(
                "background-color: rgba(110, 118, 129, 0.2); color: #8F98A0; font-weight: 700; "
                "padding: 4px 10px; border-radius: 12px; border: 1px solid #30363D;"
            )
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
            self.status_badge.setText("MODO LIBRE")
            self.status_badge.setStyleSheet(
                "background-color: rgba(46, 160, 67, 0.15); color: #3FB950; font-weight: 700; "
                "padding: 4px 10px; border-radius: 12px; border: 1px solid rgba(46, 160, 67, 0.3);"
            )
            icon_idle = os.path.join(self.resource_dir, "icon-idle.svg")
            if os.path.exists(icon_idle):
                self.header_icon_lbl.setPixmap(QIcon(icon_idle).pixmap(28, 28))

        # 2. Header Badge: BYPASS
        elif state == "BYPASS":
            self.status_badge.setText("EN DESCANSO")
            self.status_badge.setStyleSheet(
                "background-color: rgba(210, 153, 34, 0.15); color: #E3B341; font-weight: 700; "
                "padding: 4px 10px; border-radius: 12px; border: 1px solid rgba(210, 153, 34, 0.3);"
            )
            icon_byp = os.path.join(self.resource_dir, "icon-bypass.svg")
            if os.path.exists(icon_byp):
                self.header_icon_lbl.setPixmap(QIcon(icon_byp).pixmap(28, 28))

        # 3. Header Badge: LOCKED
        elif is_blocking:
            if reason == "CURFEW":
                self.status_badge.setText("TOQUE DE QUEDA")
                self.status_badge.setStyleSheet(
                    "background-color: rgba(137, 87, 229, 0.15); color: #D2A8FF; font-weight: 700; "
                    "padding: 4px 10px; border-radius: 12px; border: 1px solid rgba(137, 87, 229, 0.3);"
                )
                icon_curf = os.path.join(self.resource_dir, "icon-curfew.svg")
                if os.path.exists(icon_curf):
                    self.header_icon_lbl.setPixmap(QIcon(icon_curf).pixmap(28, 28))
            elif reason == "BOOT_COOLDOWN":
                self.status_badge.setText("FOCO DE INICIO")
                self.status_badge.setStyleSheet(
                    "background-color: rgba(56, 139, 253, 0.15); color: #58A6FF; font-weight: 700; "
                    "padding: 4px 10px; border-radius: 12px; border: 1px solid rgba(56, 139, 253, 0.3);"
                )
                icon_bt = os.path.join(self.resource_dir, "icon-boot.svg")
                if os.path.exists(icon_bt):
                    self.header_icon_lbl.setPixmap(QIcon(icon_bt).pixmap(28, 28))
            elif reason == "MANUAL_LOCK":
                self.status_badge.setText("ENFOQUE ACTIVO")
                self.status_badge.setStyleSheet(
                    "background-color: rgba(56, 139, 253, 0.15); color: #58A6FF; font-weight: 700; "
                    "padding: 4px 10px; border-radius: 12px; border: 1px solid rgba(56, 139, 253, 0.3);"
                )
                icon_act = os.path.join(self.resource_dir, "icon-active.svg")
                if os.path.exists(icon_act):
                    self.header_icon_lbl.setPixmap(QIcon(icon_act).pixmap(28, 28))
            elif reason == "SELECTIVE_LOCK":
                self.status_badge.setText("BLOQUEO SELECTIVO")
                self.status_badge.setStyleSheet(
                    "background-color: rgba(56, 139, 253, 0.15); color: #58A6FF; font-weight: 700; "
                    "padding: 4px 10px; border-radius: 12px; border: 1px solid rgba(56, 139, 253, 0.3);"
                )
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
        self.selective_tab.update_active_status(
            is_selective=is_selective,
            remaining_sec=rem,
            selective_domains=selective_domains,
            target_time=target,
            human_time=human_time
        )
