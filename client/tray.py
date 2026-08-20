"""
PyQt6 System Tray Applet for Focus-Guard.
State-specific icons, Pomodoro sessions, and bug-free submenus.
"""
import os
import sys
import logging
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QSystemTrayIcon, QMenu, QMessageBox, QApplication, QDialog
)
from PyQt6.QtGui import QIcon, QAction, QFont
from PyQt6.QtCore import QTimer, Qt

from client.ipc_client import FocusIPCClient
from client.settings_dialog import SettingsDialog, EmergencyPromptDialog, AboutDialog

logger = logging.getLogger("focus-guard.client.tray")


class FocusTrayApplet(QSystemTrayIcon):
    def __init__(self, ipc_client: FocusIPCClient, resource_dir: str, parent=None):
        super().__init__(parent)
        self.ipc = ipc_client
        self.resource_dir = resource_dir
        self.settings_dialog: Optional[SettingsDialog] = None

        # Load state-specific icons
        self.icon_active = QIcon(os.path.join(resource_dir, "icon-active.svg"))     # Green (Protected / Manual Focus)
        self.icon_curfew = QIcon(os.path.join(resource_dir, "icon-curfew.svg"))     # Purple Night Shield (Toque de Queda)
        self.icon_boot = QIcon(os.path.join(resource_dir, "icon-boot.svg"))         # Cyan Lightning Shield (Boot Focus)
        self.icon_bypass = QIcon(os.path.join(resource_dir, "icon-bypass.svg"))     # Amber Pause Shield (Descanso)
        self.icon_idle = QIcon(os.path.join(resource_dir, "icon-idle.svg"))         # Red Unlocked Shield (Libre / Off)
        self.icon_offline = QIcon(os.path.join(resource_dir, "icon-offline.svg"))   # Gray Shield (Offline)

        self.setIcon(self.icon_offline)
        self.setToolTip("Focus-Guard: Conectando con el servicio...")

        self.last_state: Optional[str] = None
        self.last_reason: Optional[str] = None
        self.last_is_blocking: Optional[bool] = None
        self.curfew_warned: bool = False

        self.menu = QMenu()
        self.setup_menu()
        self.setContextMenu(self.menu)

        self.activated.connect(self.on_tray_activated)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(2000)

        self.refresh_status()

    def setup_menu(self):
        """Constructs the clean, minimalist system tray context menu."""
        self.menu.clear()

        # 1. Header State Label
        self.status_action = QAction("Focus-Guard: Verificando...", self.menu)
        font = self.status_action.font()
        font.setBold(True)
        self.status_action.setFont(font)
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)

        # 2. Time Remaining / Target Label
        self.detail_action = QAction("", self.menu)
        self.detail_action.setEnabled(False)
        self.menu.addAction(self.detail_action)

        self.menu.addSeparator()

        # 3. Settings / Dashboard Action
        self.settings_action = QAction("Panel de Control y Reglas...", self.menu)
        self.settings_action.triggered.connect(self.show_settings_dialog)
        self.menu.addAction(self.settings_action)

        self.menu.addSeparator()

        # 4. Focus Sessions (Pomodoro & Indefinite) Submenu
        self.focus_menu = self.menu.addMenu("Sesión de Enfoque")
        
        self.focus_25_action = QAction("25 minutos (Pomodoro)", self.focus_menu)
        self.focus_25_action.triggered.connect(lambda: self.on_start_focus_session(25))
        self.focus_menu.addAction(self.focus_25_action)

        self.focus_50_action = QAction("50 minutos (Trabajo Profundo)", self.focus_menu)
        self.focus_50_action.triggered.connect(lambda: self.on_start_focus_session(50))
        self.focus_menu.addAction(self.focus_50_action)

        self.focus_indef_action = QAction("Bloqueo Indefinido", self.focus_menu)
        self.focus_indef_action.triggered.connect(lambda: self.on_start_focus_session(0))
        self.focus_menu.addAction(self.focus_indef_action)

        # 5. Standard Bypass Submenu
        self.bypass_menu = self.menu.addMenu("Pausa Temporal (Descanso)")
        
        self.bypass_15_action = QAction("15 minutos", self.bypass_menu)
        self.bypass_15_action.triggered.connect(lambda: self.on_bypass_clicked(15))
        self.bypass_menu.addAction(self.bypass_15_action)

        self.bypass_30_action = QAction("30 minutos", self.bypass_menu)
        self.bypass_30_action.triggered.connect(lambda: self.on_bypass_clicked(30))
        self.bypass_menu.addAction(self.bypass_30_action)

        self.bypass_45_action = QAction("45 minutos", self.bypass_menu)
        self.bypass_45_action.triggered.connect(lambda: self.on_bypass_clicked(45))
        self.bypass_menu.addAction(self.bypass_45_action)

        self.bypass_menu.addSeparator()
        self.cancel_bypass_action = QAction("Finalizar Pausa", self.bypass_menu)
        self.cancel_bypass_action.triggered.connect(self.on_cancel_bypass_clicked)
        self.bypass_menu.addAction(self.cancel_bypass_action)

        # 6. Emergency Bypass (for Curfew)
        self.emergency_action = QAction("Desbloqueo de Emergencia (15 min)...", self.menu)
        self.emergency_action.triggered.connect(self.on_emergency_bypass_clicked)
        self.emergency_action.setVisible(False)
        self.menu.addAction(self.emergency_action)

        # 7. Unlock Action
        self.unlock_action = QAction("Desbloquear Sitios", self.menu)
        self.unlock_action.triggered.connect(self.on_unlock_clicked)
        self.menu.addAction(self.unlock_action)

        self.menu.addSeparator()

        # 8. Information Action
        self.info_action = QAction("Acerca de Focus-Guard", self.menu)
        self.info_action.triggered.connect(self.show_info_dialog)
        self.menu.addAction(self.info_action)

        self.menu.addSeparator()

        # 10. Quit Action
        self.quit_action = QAction("Cerrar Focus-Guard", self.menu)
        self.quit_action.triggered.connect(QApplication.instance().quit)
        self.menu.addAction(self.quit_action)

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason):
        """Opens settings when tray icon is clicked."""
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_settings_dialog()

    def show_settings_dialog(self):
        """Displays or brings forward the settings window."""
        if not self.settings_dialog or not self.settings_dialog.isVisible():
            self.settings_dialog = SettingsDialog(
                ipc_client=self.ipc,
                resource_dir=self.resource_dir
            )
            self.settings_dialog.config_saved.connect(self.refresh_status)
            self.settings_dialog.show()
        else:
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()

    def _format_remaining_time(self, seconds: int) -> str:
        """Formats remaining seconds into a clean string."""
        if seconds <= 0:
            return ""
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours}h {mins}m {secs}s"
        elif mins > 0:
            return f"{mins}m {secs}s"
        else:
            return f"{secs}s"

    def refresh_status(self):
        """Fetches status from daemon and updates UI and notifications."""
        res = self.ipc.get_status()

        if res.get("status") != "ok":
            self.setIcon(self.icon_offline)
            self.setToolTip("Focus-Guard: Servicio no disponible\n(El demonio no está en ejecución)")
            self.status_action.setText("Servicio Fuera de Línea")
            self.detail_action.setText("Inicie el servicio focus-guard")
            self.detail_action.setVisible(True)
            self.focus_menu.menuAction().setVisible(False)
            self.bypass_menu.menuAction().setVisible(False)
            self.unlock_action.setVisible(False)
            self.emergency_action.setVisible(False)
            self.last_state = "OFFLINE"
            self.last_reason = None
            self.last_is_blocking = None
            return

        state = res.get("state", "UNLOCKED")
        reason = res.get("reason", "FREE_TIME")
        remaining = res.get("remaining_seconds", 0)
        target_time = res.get("target_time_str", "")
        message = res.get("message", "")
        is_blocking = res.get("is_blocking", False)
        bypasses_enabled = res.get("bypasses_enabled", True)
        in_curfew = res.get("in_curfew", False)
        curfew_warn = res.get("curfew_warning", False)
        curfew_warn_secs = res.get("curfew_warning_seconds", 0)
        time_str = self._format_remaining_time(remaining)

        # 1. Handle Curfew Warning Notification (10 mins before)
        if curfew_warn and not self.curfew_warned:
            mins_left = max(1, curfew_warn_secs // 60)
            self.showMessage(
                "Aviso de Toque de Queda",
                f"El Toque de Queda comenzará en {mins_left} minutos.",
                QSystemTrayIcon.MessageIcon.Warning,
                5000
            )
            self.curfew_warned = True
        elif not curfew_warn:
            self.curfew_warned = False

        # 2. Handle State Transition Notifications
        if self.last_reason is not None and self.last_reason != reason:
            if self.last_reason == "BOOT_COOLDOWN" and reason == "FREE_TIME":
                self.showMessage(
                    "Cooldown de Arranque Finalizado",
                    "Protección de inicio concluida. Modo Libre activo.",
                    QSystemTrayIcon.MessageIcon.Information,
                    4000
                )
            elif self.last_reason == "CURFEW" and reason == "FREE_TIME":
                self.showMessage(
                    "Toque de Queda Finalizado",
                    "Horario nocturno concluido. Modo Libre activo.",
                    QSystemTrayIcon.MessageIcon.Information,
                    4000
                )
            elif self.last_reason in ("USER_BYPASS", "EMERGENCY_BYPASS") and is_blocking:
                self.showMessage(
                    "Fin del Descanso",
                    "El descanso ha finalizado. Protección de Focus reactivada.",
                    QSystemTrayIcon.MessageIcon.Warning,
                    4000
                )
            elif reason == "CURFEW":
                self.showMessage(
                    "Toque de Queda Nocturno Iniciado",
                    f"Protección nocturna activa hasta las {target_time or '07:00'}.",
                    QSystemTrayIcon.MessageIcon.Warning,
                    5000
                )

        self.last_state = state
        self.last_reason = reason
        self.last_is_blocking = is_blocking

        # 3. State-Specific Icon & Rich Formatted Tooltip
        domains_num = res.get("domains_count", 0)
        if state == "LOCKED":
            if reason == "CURFEW":
                self.setIcon(self.icon_curfew)
                tooltip_txt = f"Focus-Guard — Protegido\nToque de Queda nocturno (hasta las {target_time or '07:00'})\nTiempo restante: {time_str or 'Activo'}\nSitios bloqueados: {domains_num}"
            elif reason == "BOOT_COOLDOWN":
                self.setIcon(self.icon_boot)
                tooltip_txt = f"Focus-Guard — Protegido\nFoco de Inicio de sesión (hasta las {target_time})\nTiempo restante: {time_str or 'Activo'}\nSitios bloqueados: {domains_num}"
            else:
                self.setIcon(self.icon_active)
                tooltip_txt = f"Focus-Guard — Protegido\nSesión de Enfoque Activa\nTiempo restante: {time_str or 'Activo'}\nSitios bloqueados: {domains_num}"
        elif state == "BYPASS":
            self.setIcon(self.icon_bypass)
            tooltip_txt = f"Focus-Guard — Pausa Temporal\nDescanso en curso\nTiempo restante: {time_str or 'Activo'}"
        else:
            self.setIcon(self.icon_idle)
            tooltip_txt = f"Focus-Guard — Modo Libre\nSitios en lista: {domains_num} (Desbloqueados)"

        self.setToolTip(tooltip_txt)

        # 4. Context-Aware Menu Items
        if state == "LOCKED":
            self.focus_menu.menuAction().setVisible(False)
            if reason == "CURFEW":
                self.status_action.setText("Toque de Queda Nocturno (Protegido)")
                self.bypass_menu.menuAction().setVisible(False)
                self.emergency_action.setVisible(True)
                self.unlock_action.setVisible(False)
            elif reason == "BOOT_COOLDOWN":
                self.status_action.setText("Cooldown de Arranque (Protegido)")
                self.bypass_menu.menuAction().setVisible(bypasses_enabled)
                self.bypass_menu.setEnabled(bypasses_enabled)
                self.emergency_action.setVisible(False)
                self.unlock_action.setVisible(False)
            else:
                self.status_action.setText("Modo Focus Manual (Protegido)")
                self.bypass_menu.menuAction().setVisible(bypasses_enabled)
                self.bypass_menu.setEnabled(bypasses_enabled)
                self.emergency_action.setVisible(False)
                self.unlock_action.setVisible(True)
                self.unlock_action.setEnabled(True)

        elif state == "BYPASS":
            self.focus_menu.menuAction().setVisible(False)
            if reason == "EMERGENCY_BYPASS":
                self.status_action.setText("Desbloqueo de Emergencia Activo")
            else:
                self.status_action.setText("Descanso Temporal Activo")
            self.bypass_menu.menuAction().setVisible(True)
            self.bypass_menu.setEnabled(True)
            self.emergency_action.setVisible(False)
            self.unlock_action.setVisible(False)

        else:
            self.status_action.setText("Modo Libre (Apagado / Desprotegido)")
            self.focus_menu.menuAction().setVisible(True)
            self.bypass_menu.menuAction().setVisible(False)
            self.emergency_action.setVisible(False)
            self.unlock_action.setVisible(False)

        # Detail text
        if target_time and time_str:
            self.detail_action.setText(f"Hasta las {target_time} ({time_str})")
            self.detail_action.setVisible(True)
        elif time_str:
            self.detail_action.setText(time_str)
            self.detail_action.setVisible(True)
        elif message:
            self.detail_action.setText(message)
            self.detail_action.setVisible(True)
        else:
            self.detail_action.setVisible(False)

        self.cancel_bypass_action.setEnabled(state == "BYPASS")

    def on_start_focus_session(self, minutes: int):
        """Starts a focus session."""
        self.ipc.lock_now(duration_minutes=minutes)
        if minutes > 0:
            self.showMessage(
                "Sesión de Enfoque Iniciada",
                f"Modo Focus activo por {minutes} minutos. Sitios bloqueados.",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
        else:
            self.showMessage(
                "Modo Focus Activado",
                "Sitios bloqueados indefinidamente.",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
        self.refresh_status()

    def on_bypass_clicked(self, minutes: int):
        """Handler for requesting standard bypass."""
        res = self.ipc.request_bypass(minutes)
        if res.get("status") == "ok":
            self.showMessage(
                "Descanso Activado",
                f"Sitios desbloqueados durante {minutes} minutos.",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
        else:
            err_msg = res.get("message") or res.get("error") or "No se pudo activar el bypass."
            self.showMessage("Bypass Denegado", err_msg, QSystemTrayIcon.MessageIcon.Warning, 4000)
        self.refresh_status()

    def on_emergency_bypass_clicked(self):
        """Opens anti-impulse confirmation dialog for emergency bypass during curfew."""
        cfg_res = self.ipc.send_command({"action": "get_config"})
        config = cfg_res.get("config", {})
        phrase = config.get("bypasses", {}).get("emergency_phrase", "necesito desbloqueo de emergencia")

        dialog = EmergencyPromptDialog(phrase=phrase)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.confirmed:
            res = self.ipc.request_emergency_bypass(15)
            if res.get("status") == "ok":
                self.showMessage(
                    "Desbloqueo de Emergencia Activado",
                    "15 minutos concedidos. Al finalizar, el Toque de Queda volverá a activarse.",
                    QSystemTrayIcon.MessageIcon.Warning,
                    4000
                )
            else:
                self.showMessage("Error", res.get("message", "No se pudo activar."), QSystemTrayIcon.MessageIcon.Critical, 3000)
        self.refresh_status()

    def on_cancel_bypass_clicked(self):
        """Handler for cancelling bypass."""
        self.ipc.cancel_bypass()
        self.refresh_status()

    def on_unlock_clicked(self):
        """Handler for manual unlock."""
        res = self.ipc.unlock_now()
        if res.get("status") != "ok":
            err_msg = res.get("message") or res.get("error") or "No se puede desbloquear en este momento."
            self.showMessage("Desbloqueo no permitido", err_msg, QSystemTrayIcon.MessageIcon.Warning, 3000)
        self.refresh_status()

    def show_info_dialog(self):
        """Displays the sleek custom About dialog."""
        cfg_res = self.ipc.send_command({"action": "get_config"})
        config = cfg_res.get("config", {})
        dialog = AboutDialog(resource_dir=self.resource_dir, config=config)
        dialog.exec()
