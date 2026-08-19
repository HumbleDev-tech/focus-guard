"""
PyQt6 System Tray Applet for Focus-Guard.
Optimized for KDE Plasma 6 (Wayland) StatusNotifierItem.
"""
import os
import sys
import logging
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QSystemTrayIcon, QMenu, QMessageBox, QApplication
)
from PyQt6.QtGui import QIcon, QAction, QFont
from PyQt6.QtCore import QTimer, Qt

from client.ipc_client import FocusIPCClient

logger = logging.getLogger("focus-guard.client.tray")


class FocusTrayApplet(QSystemTrayIcon):
    def __init__(self, ipc_client: FocusIPCClient, resource_dir: str, parent=None):
        super().__init__(parent)
        self.ipc = ipc_client
        self.resource_dir = resource_dir

        self.icon_active = QIcon(os.path.join(resource_dir, "icon-active.svg"))
        self.icon_idle = QIcon(os.path.join(resource_dir, "icon-idle.svg"))
        self.icon_offline = QIcon(os.path.join(resource_dir, "icon-offline.svg"))

        # Default icon
        self.setIcon(self.icon_offline)
        self.setToolTip("Focus-Guard: Conectando con el demonio...")

        self.last_state: Optional[str] = None
        self.last_is_blocking: Optional[bool] = None

        # Build Context Menu
        self.menu = QMenu()
        self.setup_menu()
        self.setContextMenu(self.menu)

        # Polling Timer for state updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(2500)  # Check every 2.5 seconds

        # Initial status query
        self.refresh_status()

    def setup_menu(self):
        """Constructs the system tray context menu."""
        self.menu.clear()

        # 1. Header State Label
        self.status_action = QAction("Focus-Guard: Verificando...", self.menu)
        font = self.status_action.font()
        font.setBold(True)
        self.status_action.setFont(font)
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)

        # 2. Time Remaining / Reason Label
        self.detail_action = QAction("", self.menu)
        self.detail_action.setEnabled(False)
        self.menu.addAction(self.detail_action)

        self.menu.addSeparator()

        # 3. Quick Lock Action
        self.lock_action = QAction("🔒 Bloquear Ahora (Modo Focus)", self.menu)
        self.lock_action.triggered.connect(self.on_lock_clicked)
        self.menu.addAction(self.lock_action)

        # 4. Bypass Submenu
        self.bypass_menu = self.menu.addMenu("☕ Bypass Temporal (Descanso)")
        
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
        self.cancel_bypass_action = QAction("✕ Cancelar Descanso y Volver a Focus", self.bypass_menu)
        self.cancel_bypass_action.triggered.connect(self.on_cancel_bypass_clicked)
        self.bypass_menu.addAction(self.cancel_bypass_action)

        # 5. Unlock Action (for manual unlock when permitted)
        self.unlock_action = QAction("🔓 Desbloquear Sitios", self.menu)
        self.unlock_action.triggered.connect(self.on_unlock_clicked)
        self.menu.addAction(self.unlock_action)

        self.menu.addSeparator()

        # 6. Information Action
        self.info_action = QAction("ℹ️ Ver Información y Reglas", self.menu)
        self.info_action.triggered.connect(self.show_info_dialog)
        self.menu.addAction(self.info_action)

        # 7. Refresh Action
        self.refresh_action = QAction("🔄 Actualizar", self.menu)
        self.refresh_action.triggered.connect(self.refresh_status)
        self.menu.addAction(self.refresh_action)

        self.menu.addSeparator()

        # 8. Quit Action
        self.quit_action = QAction("✕ Salir de la Bandeja", self.menu)
        self.quit_action.triggered.connect(QApplication.instance().quit)
        self.menu.addAction(self.quit_action)

    def _format_remaining_time(self, seconds: int) -> str:
        """Formats remaining seconds into a human-friendly string."""
        if seconds <= 0:
            return ""
        hours = seconds // 3600
        mins = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours}h {mins}m {secs}s restantes"
        elif mins > 0:
            return f"{mins}m {secs}s restantes"
        else:
            return f"{secs}s restantes"

    def refresh_status(self):
        """Fetches status from daemon and updates UI elements."""
        res = self.ipc.get_status()

        if res.get("status") != "ok":
            # Daemon is offline or unreachable
            self.setIcon(self.icon_offline)
            self.setToolTip("Focus-Guard: Demonio no disponible\n(El servicio no está en ejecución)")
            self.status_action.setText("⚠️ Demonio Fuera de Línea")
            self.detail_action.setText("Inicie el servicio focus-guard")
            self.detail_action.setVisible(True)
            self.bypass_menu.setEnabled(False)
            self.lock_action.setEnabled(False)
            self.unlock_action.setEnabled(False)
            self.last_state = "OFFLINE"
            self.last_is_blocking = None
            return

        # Daemon is OK
        state = res.get("state", "UNLOCKED")
        reason = res.get("reason", "FREE_TIME")
        remaining = res.get("remaining_seconds", 0)
        message = res.get("message", "")
        can_bypass = res.get("can_bypass", True)
        is_blocking = res.get("is_blocking", False)
        time_str = self._format_remaining_time(remaining)

        # Notify user on state changes
        if self.last_is_blocking is not None and self.last_is_blocking != is_blocking:
            if is_blocking:
                self.showMessage(
                    "Focus-Guard: Sitios Bloqueados",
                    f"Modo Focus activo: {message}",
                    QSystemTrayIcon.MessageIcon.Warning,
                    3000
                )
            else:
                self.showMessage(
                    "Focus-Guard: Sitios Desbloqueados",
                    f"Modo Libre activo: {message}",
                    QSystemTrayIcon.MessageIcon.Information,
                    3000
                )

        self.last_state = state
        self.last_is_blocking = is_blocking

        # Update Tray Icon & Tooltip
        if is_blocking:
            self.setIcon(self.icon_active)
            tooltip_txt = f"Focus-Guard: BLOQUEADO (Focus)\n{message}"
            if time_str:
                tooltip_txt += f"\n{time_str}"
            self.setToolTip(tooltip_txt)
        else:
            self.setIcon(self.icon_idle)
            tooltip_txt = f"Focus-Guard: LIBRE (Descanso)\n{message}"
            if time_str:
                tooltip_txt += f"\n{time_str}"
            self.setToolTip(tooltip_txt)

        # Update Menu Actions
        if state == "LOCKED":
            if reason == "CURFEW":
                self.status_action.setText("🌙 Toque de Queda Nocturno (Bloqueado)")
                self.bypass_menu.setEnabled(can_bypass)
            elif reason == "BOOT_COOLDOWN":
                self.status_action.setText("🚀 Cooldown de Arranque (Bloqueado)")
                self.bypass_menu.setEnabled(can_bypass)
            else:
                self.status_action.setText("🔒 Modo Enfoque Manual (Bloqueado)")
                self.bypass_menu.setEnabled(can_bypass)
        elif state == "BYPASS":
            self.status_action.setText("☕ Descanso Temporal Activo")
            self.bypass_menu.setEnabled(True)
        else:
            self.status_action.setText("🟢 Modo Libre (Sin Bloqueo)")
            self.bypass_menu.setEnabled(False)

        # Detail text
        if time_str:
            self.detail_action.setText(f"⏳ {time_str}")
            self.detail_action.setVisible(True)
        elif message:
            self.detail_action.setText(f"ℹ️ {message}")
            self.detail_action.setVisible(True)
        else:
            self.detail_action.setVisible(False)

        # Enable/Disable Buttons
        self.lock_action.setEnabled(state != "LOCKED" or state == "BYPASS")
        self.cancel_bypass_action.setEnabled(state == "BYPASS")
        self.unlock_action.setEnabled(reason == "MANUAL_LOCK")

    def on_bypass_clicked(self, minutes: int):
        """Handler for requesting a bypass."""
        res = self.ipc.request_bypass(minutes)
        if res.get("status") == "ok":
            self.showMessage(
                "Bypass Activado",
                f"Sitios desbloqueados por {minutes} minutos. ¡Aprovecha el descanso!",
                QSystemTrayIcon.MessageIcon.Information,
                3000
            )
        else:
            err_msg = res.get("message") or res.get("error") or "No se pudo activar el bypass."
            self.showMessage(
                "Bypass Denegado",
                err_msg,
                QSystemTrayIcon.MessageIcon.Warning,
                4000
            )
        self.refresh_status()

    def on_cancel_bypass_clicked(self):
        """Handler for cancelling bypass."""
        res = self.ipc.cancel_bypass()
        self.refresh_status()

    def on_lock_clicked(self):
        """Handler for manual lock."""
        res = self.ipc.lock_now()
        self.refresh_status()

    def on_unlock_clicked(self):
        """Handler for manual unlock."""
        res = self.ipc.unlock_now()
        if res.get("status") != "ok":
            err_msg = res.get("message") or res.get("error") or "No se puede desbloquear en este momento."
            self.showMessage("Desbloqueo no permitido", err_msg, QSystemTrayIcon.MessageIcon.Warning, 3000)
        self.refresh_status()

    def show_info_dialog(self):
        """Displays status and configuration dialog."""
        cfg_res = self.ipc.send_command({"action": "get_config"})
        config = cfg_res.get("config", {})
        domains = config.get("blocked_domains", [])
        curfew = config.get("curfew", {})
        boot = config.get("boot_cooldown", {})

        curfew_text = f"{curfew.get('start_time', '23:15')} a {curfew.get('end_time', '07:00')} (Innegociable)" if curfew.get('enabled') else "Desactivado"
        boot_text = f"{boot.get('duration_minutes', 30)} minutos" if boot.get('enabled') else "Desactivado"
        domains_text = ", ".join(domains[:12])
        if len(domains) > 12:
            domains_text += f" (+{len(domains)-12} más)"

        info = (
            "<h3>🛡️ Focus-Guard</h3>"
            "<p>Bloqueador de distracciones a nivel de sistema para Linux.</p>"
            "<hr>"
            f"<b>🌙 Toque de Queda:</b> {curfew_text}<br>"
            f"<b>🚀 Cooldown al Iniciar:</b> {boot_text}<br>"
            f"<b>🌐 Sitios configurados ({len(domains)}):</b><br>"
            f"<i>{domains_text}</i><br><br>"
            "<small>Para editar sitios o reglas, modifica <code>/etc/focus-guard/config.json</code></small>"
        )

        msg_box = QMessageBox()
        msg_box.setWindowTitle("Información de Focus-Guard")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(info)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()
