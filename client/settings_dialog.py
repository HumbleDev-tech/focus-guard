"""
Focus-Guard Settings & Dashboard Dialog.
Minimalist, typography-driven, and adaptive to KDE Plasma 6 Light & Dark themes.
"""
import re
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QTabWidget, QWidget, QCheckBox,
    QTimeEdit, QSpinBox, QFrame, QMessageBox, QApplication
)
from PyQt6.QtGui import QIcon, QFont, QColor, QPalette
from PyQt6.QtCore import Qt, QTime, QTimer, pyqtSignal

from client.ipc_client import FocusIPCClient


def sanitize_domain(raw_input: str) -> Optional[str]:
    """Cleans up URLs and strings into a clean domain name."""
    raw = raw_input.strip().lower()
    if not raw:
        return None

    if not raw.startswith("http://") and not raw.startswith("https://"):
        raw = "http://" + raw

    try:
        parsed = urlparse(raw)
        host = parsed.netloc or parsed.path
        host = host.split(":")[0]
        if host.startswith("www."):
            host = host[4:]
        if re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", host):
            return host
    except Exception:
        pass
    return None


class SettingsDialog(QDialog):
    config_saved = pyqtSignal()

    def __init__(self, ipc_client: FocusIPCClient, resource_dir: str, parent=None):
        super().__init__(parent)
        self.ipc = ipc_client
        self.resource_dir = resource_dir
        self.config_data: Dict[str, Any] = {}
        self.blocked_domains: List[str] = []

        self.setWindowTitle("Focus-Guard — Panel de Control y Ajustes")
        self.setMinimumSize(580, 520)
        self.resize(640, 560)

        # Apply adaptive palette styles
        self.apply_theme_styles()

        # Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(14)

        # 1. Header
        self.setup_header()

        # 2. Tab Widget
        self.tabs = QTabWidget()
        self.setup_domains_tab()
        self.setup_rules_tab()
        self.setup_dashboard_tab()
        self.main_layout.addWidget(self.tabs)

        # 3. Bottom Action Bar
        self.setup_bottom_bar()

        # Load initial config
        self.load_configuration()

        # Live poll timer for dashboard tab
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.refresh_live_status)
        self.poll_timer.start(2000)

    def is_dark_mode(self) -> bool:
        """Determines if the system is currently using a dark theme."""
        bg = self.palette().color(QPalette.ColorRole.Window)
        return bg.lightness() < 128

    def apply_theme_styles(self):
        """Sets modern, minimalist styling respecting system palette."""
        is_dark = self.is_dark_mode()

        if is_dark:
            bg_card = "#1F232A"
            bg_input = "#16191D"
            border_color = "#323842"
            text_primary = "#F3F4F6"
            text_secondary = "#9CA3AF"
            accent_blue = "#3B82F6"
            accent_blue_hover = "#2563EB"
            tab_bg = "#111418"
        else:
            bg_card = "#FFFFFF"
            bg_input = "#F9FAFB"
            border_color = "#E5E7EB"
            text_primary = "#111827"
            text_secondary = "#6B7280"
            accent_blue = "#2563EB"
            accent_blue_hover = "#1D4ED8"
            tab_bg = "#F3F4F6"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.palette().color(QPalette.ColorRole.Window).name()};
                color: {text_primary};
                font-family: system-ui, -apple-system, sans-serif;
            }}
            QTabWidget::pane {{
                border: 1px solid {border_color};
                border-radius: 8px;
                background-color: {bg_card};
                top: -1px;
            }}
            QTabBar::tab {{
                background: {tab_bg};
                color: {text_secondary};
                padding: 9px 16px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: 600;
                font-size: 12px;
            }}
            QTabBar::tab:selected {{
                background: {bg_card};
                color: {text_primary};
                border-top: 2px solid {accent_blue};
            }}
            QLineEdit, QTimeEdit, QSpinBox {{
                background-color: {bg_input};
                color: {text_primary};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus, QTimeEdit:focus, QSpinBox:focus {{
                border: 1px solid {accent_blue};
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                font-size: 12px;
            }}
            QPushButton#primaryBtn {{
                background-color: {accent_blue};
                color: #FFFFFF;
                border: none;
            }}
            QPushButton#primaryBtn:hover {{
                background-color: {accent_blue_hover};
            }}
            QPushButton#secondaryBtn {{
                background-color: transparent;
                color: {text_secondary};
                border: 1px solid {border_color};
            }}
            QPushButton#secondaryBtn:hover {{
                background-color: {tab_bg};
                color: {text_primary};
            }}
            QPushButton#chipBtn {{
                background-color: {tab_bg};
                color: {text_primary};
                border: 1px solid {border_color};
                border-radius: 12px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton#chipBtn:hover {{
                background-color: {accent_blue};
                color: #FFFFFF;
                border-color: {accent_blue};
            }}
            QListWidget {{
                background-color: {bg_input};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {border_color};
            }}
            QListWidget::item:selected {{
                background-color: transparent;
            }}
            QCheckBox {{
                color: {text_primary};
                font-size: 13px;
                font-weight: 600;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid {border_color};
                background: {bg_input};
            }}
            QCheckBox::indicator:checked {{
                background-color: {accent_blue};
                border-color: {accent_blue};
            }}
        """)

    def setup_header(self):
        """Header with logo, title, and live status badge."""
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(QIcon(f"{self.resource_dir}/icon-active.svg").pixmap(32, 32))
        header.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_lbl = QLabel("Focus-Guard")
        title_lbl.setStyleSheet("font-size: 17px; font-weight: 700; letter-spacing: 0.5px;")
        sub_lbl = QLabel("Configuracion del Sistema y Reglas de Bloqueo")
        sub_lbl.setStyleSheet("font-size: 12px; opacity: 0.7;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header.addLayout(title_box)

        header.addStretch()

        self.status_badge = QLabel("Verificando...")
        self.status_badge.setStyleSheet("""
            background-color: #374151;
            color: #FFFFFF;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 10px;
            letter-spacing: 0.5px;
        """)
        header.addWidget(self.status_badge)

        self.main_layout.addLayout(header)

    def setup_domains_tab(self):
        """Tab 1: Blocked Domains management."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        top_bar = QHBoxLayout()
        self.domains_count_lbl = QLabel("Sitios Bloqueados")
        self.domains_count_lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
        top_bar.addWidget(self.domains_count_lbl)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # Add Domain Input Bar
        add_bar = QHBoxLayout()
        add_bar.setSpacing(8)
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("Ingresa un dominio (ej: twitter.com) o pega una URL...")
        self.domain_input.returnPressed.connect(self.on_add_domain_clicked)
        add_bar.addWidget(self.domain_input)

        add_btn = QPushButton("Añadir")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self.on_add_domain_clicked)
        add_bar.addWidget(add_btn)
        layout.addLayout(add_bar)

        # Preset Quick Chips
        preset_bar = QHBoxLayout()
        preset_bar.setSpacing(6)
        preset_lbl = QLabel("Añadir categoria:")
        preset_lbl.setStyleSheet("font-size: 11px; opacity: 0.7;")
        preset_bar.addWidget(preset_lbl)

        btn_social = QPushButton("Redes Sociales")
        btn_social.setObjectName("chipBtn")
        btn_social.clicked.connect(lambda: self.add_domain_preset(["x.com", "twitter.com", "instagram.com", "facebook.com", "tiktok.com", "threads.net"]))
        preset_bar.addWidget(btn_social)

        btn_video = QPushButton("Streaming y Video")
        btn_video.setObjectName("chipBtn")
        btn_video.clicked.connect(lambda: self.add_domain_preset(["youtube.com", "twitch.tv", "netflix.com", "disneyplus.com", "primevideo.com"]))
        preset_bar.addWidget(btn_video)

        btn_distr = QPushButton("Foros y Ocio")
        btn_distr.setObjectName("chipBtn")
        btn_distr.clicked.connect(lambda: self.add_domain_preset(["reddit.com", "9gag.com", "pinterest.com", "discord.com"]))
        preset_bar.addWidget(btn_distr)

        preset_bar.addStretch()
        layout.addLayout(preset_bar)

        # Domains List Widget
        self.domains_list = QListWidget()
        self.domains_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self.domains_list)

        self.tabs.addTab(tab, "Sitios Bloqueados")

    def setup_rules_tab(self):
        """Tab 2: Curfew and Boot Cooldown rules."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # 1. Curfew Card
        curfew_card = QFrame()
        curfew_card.setStyleSheet("QFrame { border: 1px solid rgba(128,128,128,0.2); border-radius: 8px; padding: 12px; }")
        curfew_layout = QVBoxLayout(curfew_card)
        curfew_layout.setSpacing(10)

        self.curfew_enabled_cb = QCheckBox("Toque de Queda Nocturno (Night Curfew)")
        curfew_layout.addWidget(self.curfew_enabled_cb)

        curfew_desc = QLabel("Bloqueo estricto durante la noche para proteger tus horas de descanso.")
        curfew_desc.setStyleSheet("font-size: 12px; opacity: 0.75;")
        curfew_desc.setWordWrap(True)
        curfew_layout.addWidget(curfew_desc)

        time_row = QHBoxLayout()
        time_row.setSpacing(12)

        start_box = QVBoxLayout()
        start_box.addWidget(QLabel("Hora de Inicio:"))
        self.curfew_start_time = QTimeEdit()
        self.curfew_start_time.setDisplayFormat("HH:mm")
        start_box.addWidget(self.curfew_start_time)
        time_row.addLayout(start_box)

        end_box = QVBoxLayout()
        end_box.addWidget(QLabel("Hora de Fin:"))
        self.curfew_end_time = QTimeEdit()
        self.curfew_end_time.setDisplayFormat("HH:mm")
        end_box.addWidget(self.curfew_end_time)
        time_row.addLayout(end_box)

        curfew_layout.addLayout(time_row)
        layout.addWidget(curfew_card)

        # 2. Boot Cooldown Card
        boot_card = QFrame()
        boot_card.setStyleSheet("QFrame { border: 1px solid rgba(128,128,128,0.2); border-radius: 8px; padding: 12px; }")
        boot_layout = QVBoxLayout(boot_card)
        boot_layout.setSpacing(10)

        self.boot_enabled_cb = QCheckBox("Cooldown al Iniciar el Sistema (Boot Focus)")
        boot_layout.addWidget(self.boot_enabled_cb)

        boot_desc = QLabel("Activa un bloqueo temporal al encender el equipo para evitar distracciones tempranas.")
        boot_desc.setStyleSheet("font-size: 12px; opacity: 0.75;")
        boot_desc.setWordWrap(True)
        boot_layout.addWidget(boot_desc)

        dur_row = QHBoxLayout()
        dur_row.addWidget(QLabel("Duracion (minutos):"))
        self.boot_duration_spin = QSpinBox()
        self.boot_duration_spin.setRange(5, 180)
        self.boot_duration_spin.setSingleStep(5)
        dur_row.addWidget(self.boot_duration_spin)
        dur_row.addStretch()
        boot_layout.addLayout(dur_row)

        layout.addWidget(boot_card)
        layout.addStretch()

        self.tabs.addTab(tab, "Horarios y Reglas")

    def setup_dashboard_tab(self):
        """Tab 3: Live Status & Quick Actions."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Status Card
        self.dash_card = QFrame()
        self.dash_card.setStyleSheet("QFrame { border: 1px solid rgba(128,128,128,0.2); border-radius: 8px; padding: 16px; }")
        dash_layout = QVBoxLayout(self.dash_card)
        dash_layout.setSpacing(8)

        self.dash_state_lbl = QLabel("Estado: Desconocido")
        self.dash_state_lbl.setStyleSheet("font-size: 15px; font-weight: 700;")
        dash_layout.addWidget(self.dash_state_lbl)

        self.dash_time_lbl = QLabel("")
        self.dash_time_lbl.setStyleSheet("font-size: 13px; opacity: 0.8;")
        dash_layout.addWidget(self.dash_time_lbl)

        self.dash_desc_lbl = QLabel("")
        self.dash_desc_lbl.setStyleSheet("font-size: 12px; opacity: 0.7;")
        self.dash_desc_lbl.setWordWrap(True)
        dash_layout.addWidget(self.dash_desc_lbl)

        layout.addWidget(self.dash_card)

        # Quick Actions Box
        act_box = QVBoxLayout()
        act_box.setSpacing(8)
        act_lbl = QLabel("Acciones Rapidas")
        act_lbl.setStyleSheet("font-weight: 600; font-size: 13px;")
        act_box.addWidget(act_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_dash_lock = QPushButton("Bloquear Ahora")
        self.btn_dash_lock.setObjectName("primaryBtn")
        self.btn_dash_lock.clicked.connect(self.on_dash_lock_clicked)
        btn_row.addWidget(self.btn_dash_lock)

        self.btn_dash_bypass15 = QPushButton("Descanso (15m)")
        self.btn_dash_bypass15.setObjectName("secondaryBtn")
        self.btn_dash_bypass15.clicked.connect(lambda: self.on_dash_bypass_clicked(15))
        btn_row.addWidget(self.btn_dash_bypass15)

        self.btn_dash_unlock = QPushButton("Desbloquear")
        self.btn_dash_unlock.setObjectName("secondaryBtn")
        self.btn_dash_unlock.clicked.connect(self.on_dash_unlock_clicked)
        btn_row.addWidget(self.btn_dash_unlock)

        act_box.addLayout(btn_row)
        layout.addLayout(act_box)

        layout.addStretch()
        self.tabs.addTab(tab, "Estado y Control")

    def setup_bottom_bar(self):
        """Bottom bar with Save, Feedback and Close buttons."""
        bottom = QHBoxLayout()
        bottom.setSpacing(10)

        self.save_feedback_lbl = QLabel("")
        self.save_feedback_lbl.setStyleSheet("font-size: 12px; color: #10B981; font-weight: 600;")
        bottom.addWidget(self.save_feedback_lbl)

        bottom.addStretch()

        close_btn = QPushButton("Cerrar")
        close_btn.setObjectName("secondaryBtn")
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)

        self.save_btn = QPushButton("Guardar Cambios")
        self.save_btn.setObjectName("primaryBtn")
        self.save_btn.clicked.connect(self.on_save_clicked)
        bottom.addWidget(self.save_btn)

        self.main_layout.addLayout(bottom)

    def load_configuration(self):
        """Fetches current configuration from daemon."""
        res = self.ipc.get_config()
        if res.get("status") == "ok":
            self.config_data = res.get("config", {})
            self.blocked_domains = list(self.config_data.get("blocked_domains", []))
            self.render_domains_list()

            # Curfew
            curfew = self.config_data.get("curfew", {})
            self.curfew_enabled_cb.setChecked(curfew.get("enabled", True))
            start_parts = [int(x) for x in curfew.get("start_time", "23:15").split(":")]
            end_parts = [int(x) for x in curfew.get("end_time", "07:00").split(":")]
            self.curfew_start_time.setTime(QTime(start_parts[0], start_parts[1]))
            self.curfew_end_time.setTime(QTime(end_parts[0], end_parts[1]))

            # Boot Cooldown
            boot = self.config_data.get("boot_cooldown", {})
            self.boot_enabled_cb.setChecked(boot.get("enabled", True))
            self.boot_duration_spin.setValue(int(boot.get("duration_minutes", 30)))
        else:
            self.save_feedback_lbl.setText("Servicio fuera de linea.")

    def render_domains_list(self):
        """Populates the blocked domains list widget."""
        self.domains_list.clear()
        self.domains_count_lbl.setText(f"Sitios Bloqueados ({len(self.blocked_domains)})")

        for domain in sorted(self.blocked_domains):
            item = QListWidgetItem()
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(6, 2, 6, 2)

            name_lbl = QLabel(domain)
            name_lbl.setStyleSheet("font-weight: 500; font-size: 13px;")
            row_layout.addWidget(name_lbl)

            row_layout.addStretch()

            del_btn = QPushButton("✕")
            del_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background: transparent;
                    font-size: 13px;
                    font-weight: 700;
                    color: #9CA3AF;
                    padding: 2px 6px;
                }
                QPushButton:hover {
                    color: #EF4444;
                }
            """)
            del_btn.setToolTip("Eliminar dominio")
            del_btn.clicked.connect(lambda _, d=domain: self.on_remove_domain(d))
            row_layout.addWidget(del_btn)

            item.setSizeHint(row.sizeHint())
            self.domains_list.addItem(item)
            self.domains_list.setItemWidget(item, row)

    def on_add_domain_clicked(self):
        """Adds cleaned domain to local list."""
        raw = self.domain_input.text()
        domain = sanitize_domain(raw)
        if not domain:
            QMessageBox.warning(self, "Dominio Invalido", "Por favor ingresa un nombre de dominio valido (ej: twitter.com).")
            return

        if domain in self.blocked_domains:
            QMessageBox.information(self, "Dominio Existente", f"'{domain}' ya esta incluido en la lista.")
            return

        self.blocked_domains.append(domain)
        self.domain_input.clear()
        self.render_domains_list()

    def add_domain_preset(self, domains: List[str]):
        """Adds a list of domains from quick category chips."""
        added = 0
        for d in domains:
            if d not in self.blocked_domains:
                self.blocked_domains.append(d)
                added += 1
        if added > 0:
            self.render_domains_list()

    def on_remove_domain(self, domain: str):
        """Removes a domain from the list."""
        if domain in self.blocked_domains:
            self.blocked_domains.remove(domain)
            self.render_domains_list()

    def on_save_clicked(self):
        """Packages configuration and sends to daemon."""
        curfew_cfg = {
            "enabled": self.curfew_enabled_cb.isChecked(),
            "start_time": self.curfew_start_time.time().toString("HH:mm"),
            "end_time": self.curfew_end_time.time().toString("HH:mm"),
            "allow_bypass": self.config_data.get("curfew", {}).get("allow_bypass", False)
        }

        boot_cfg = {
            "enabled": self.boot_enabled_cb.isChecked(),
            "duration_minutes": self.boot_duration_spin.value()
        }

        updated_config = dict(self.config_data)
        updated_config["blocked_domains"] = self.blocked_domains
        updated_config["curfew"] = curfew_cfg
        updated_config["boot_cooldown"] = boot_cfg

        res = self.ipc.save_config(updated_config)
        if res.get("status") == "ok":
            self.save_feedback_lbl.setStyleSheet("font-size: 12px; color: #10B981; font-weight: 600;")
            self.save_feedback_lbl.setText("Cambios guardados correctamente")
            self.config_data = updated_config
            self.config_saved.emit()
            QTimer.singleShot(3000, lambda: self.save_feedback_lbl.setText(""))
        else:
            self.save_feedback_lbl.setStyleSheet("font-size: 12px; color: #EF4444; font-weight: 600;")
            self.save_feedback_lbl.setText(f"Error: {res.get('error', 'No se pudo guardar')}")

    def refresh_live_status(self):
        """Updates the dashboard tab with real-time daemon state."""
        res = self.ipc.get_status()
        if res.get("status") != "ok":
            self.status_badge.setText("OFFLINE")
            self.status_badge.setStyleSheet("background-color: #6B7280; color: #FFF; border-radius: 10px; padding: 4px 10px; font-weight: 700;")
            self.dash_state_lbl.setText("Servicio Fuera de Linea")
            self.dash_time_lbl.setText("")
            self.dash_desc_lbl.setText("El servicio focus-guard no se encuentra en ejecucion.")
            return

        state = res.get("state", "UNLOCKED")
        reason = res.get("reason", "FREE_TIME")
        message = res.get("message", "")
        rem = res.get("remaining_seconds", 0)
        target = res.get("target_time_str", "")
        is_blocking = res.get("is_blocking", False)

        if is_blocking:
            self.status_badge.setText("BLOQUEADO")
            self.status_badge.setStyleSheet("background-color: #EF4444; color: #FFF; font-weight: 700; border-radius: 10px; padding: 4px 10px;")
            self.dash_state_lbl.setText(f"Modo Focus Activo ({reason})")
        elif state == "BYPASS":
            self.status_badge.setText("DESCANSO")
            self.status_badge.setStyleSheet("background-color: #F59E0B; color: #FFF; font-weight: 700; border-radius: 10px; padding: 4px 10px;")
            self.dash_state_lbl.setText("Descanso Temporal Activo")
        else:
            self.status_badge.setText("LIBRE")
            self.status_badge.setStyleSheet("background-color: #10B981; color: #FFF; font-weight: 700; border-radius: 10px; padding: 4px 10px;")
            self.dash_state_lbl.setText("Sitios Web Desbloqueados")

        if rem > 0:
            mins = rem // 60
            secs = rem % 60
            self.dash_time_lbl.setText(f"Tiempo restante: {mins}m {secs}s" + (f" (Hasta las {target})" if target else ""))
        else:
            self.dash_time_lbl.setText("")

        self.dash_desc_lbl.setText(message)

    def on_dash_lock_clicked(self):
        self.ipc.lock_now()
        self.refresh_live_status()

    def on_dash_bypass_clicked(self, minutes: int):
        self.ipc.request_bypass(minutes)
        self.refresh_live_status()

    def on_dash_unlock_clicked(self):
        self.ipc.unlock_now()
        self.refresh_live_status()
