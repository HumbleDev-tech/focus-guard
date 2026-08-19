"""
Focus-Guard Settings & Dashboard Dialog.
Pure monochrome minimalism, pixel-perfect alignment, live domain filtering, and robust actions.
"""
import re
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QTabWidget, QWidget, QCheckBox,
    QTimeEdit, QSpinBox, QFrame, QMessageBox, QApplication, QGridLayout,
    QInputDialog
)
from PyQt6.QtGui import QIcon, QPalette
from PyQt6.QtCore import Qt, QTime, QTimer, pyqtSignal

from client.ipc_client import FocusIPCClient


def sanitize_domain(raw_input: str) -> Optional[str]:
    """Cleans up URLs and strings into a valid lowercase domain name."""
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


def format_human_time(seconds: int) -> str:
    """Formats remaining seconds into natural human time."""
    if seconds <= 0:
        return "0s"
    hours = seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        if mins > 0:
            return f"{hours}h {mins}m {secs}s"
        return f"{hours}h {secs}s"
    elif mins > 0:
        return f"{mins}m {secs}s"
    else:
        return f"{secs}s"


class SettingsDialog(QDialog):
    config_saved = pyqtSignal()

    def __init__(self, ipc_client: FocusIPCClient, resource_dir: str, parent=None):
        super().__init__(parent)
        self.ipc = ipc_client
        self.resource_dir = resource_dir
        self.config_data: Dict[str, Any] = {}
        self.blocked_domains: List[str] = []
        self.filter_text: str = ""

        self.setWindowTitle("Focus-Guard — Panel de Control y Ajustes")
        self.setMinimumSize(620, 560)
        self.resize(660, 590)

        # Apply strict monochrome theme
        self.apply_theme_styles()

        # Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(14)

        # 1. Header
        self.setup_header()

        # 2. Tabs
        self.tabs = QTabWidget()
        self.setup_domains_tab()
        self.setup_rules_tab()
        self.setup_dashboard_tab()
        self.main_layout.addWidget(self.tabs)

        # 3. Bottom Bar
        self.setup_bottom_bar()

        # Load config
        self.load_configuration()

        # Live poll timer
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.refresh_live_status)
        self.poll_timer.start(1500)

    def is_dark_mode(self) -> bool:
        """Checks if desktop is in dark mode."""
        bg = self.palette().color(QPalette.ColorRole.Window)
        return bg.lightness() < 128

    def apply_theme_styles(self):
        """Pure monochrome minimalist stylesheet."""
        is_dark = self.is_dark_mode()

        if is_dark:
            bg_window = "#121519"
            bg_card = "#181C22"
            bg_card_inner = "#1E232B"
            bg_input = "#222832"
            border_color = "#2F3746"
            text_primary = "#EDEDED"
            text_secondary = "#9AA2AF"
            accent_blue = "#3B82F6"
            accent_blue_hover = "#2563EB"
            tab_bg = "#15181E"
        else:
            bg_window = "#F4F5F7"
            bg_card = "#FFFFFF"
            bg_card_inner = "#F9FAFB"
            bg_input = "#FFFFFF"
            border_color = "#D1D5DB"
            text_primary = "#111827"
            text_secondary = "#4B5563"
            accent_blue = "#2563EB"
            accent_blue_hover = "#1D4ED8"
            tab_bg = "#E5E7EB"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_window};
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
                padding: 10px 18px;
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
            QLineEdit {{
                background-color: {bg_input};
                color: {text_primary};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {accent_blue};
            }}
            /* High contrast TimeEdit and SpinBox */
            QTimeEdit, QSpinBox {{
                background-color: {bg_input};
                color: {text_primary};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 600;
                min-height: 22px;
            }}
            QTimeEdit:focus, QSpinBox:focus {{
                border: 1px solid {accent_blue};
            }}
            QTimeEdit::up-button, QTimeEdit::down-button, QSpinBox::up-button, QSpinBox::down-button {{
                width: 20px;
                background-color: {bg_card_inner};
                border-left: 1px solid {border_color};
            }}
            QTimeEdit::up-button:hover, QTimeEdit::down-button:hover, QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {accent_blue};
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
                background-color: {bg_card_inner};
                color: {text_primary};
                border: 1px solid {border_color};
            }}
            QPushButton#secondaryBtn:hover {{
                border-color: {accent_blue};
            }}
            QPushButton#chipBtn {{
                background-color: transparent;
                color: {text_secondary};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 500;
            }}
            QPushButton#chipBtn:hover {{
                color: {text_primary};
                border-color: {text_primary};
            }}
            /* Clean ListWidget without double selection outline */
            QListWidget {{
                background-color: {bg_card_inner};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 4px;
                outline: none;
            }}
            QListWidget::item {{
                background-color: transparent;
                border: none;
                padding: 0px;
                margin-bottom: 2px;
            }}
            QListWidget::item:focus, QListWidget::item:selected {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QCheckBox {{
                color: {text_primary};
                font-size: 13px;
                font-weight: 600;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
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
        """Header with app title and status indicator."""
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_lbl = QLabel()
        icon_lbl.setPixmap(QIcon(f"{self.resource_dir}/icon-active.svg").pixmap(30, 30))
        header.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_lbl = QLabel("Focus-Guard")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
        sub_lbl = QLabel("Control de Reglas de Enfoque")
        sub_lbl.setStyleSheet("font-size: 12px; opacity: 0.65;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header.addLayout(title_box)

        header.addStretch()

        self.status_badge = QLabel("VERIFICANDO")
        self.status_badge.setStyleSheet("""
            background-color: #2F3746;
            color: #EDEDED;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
        """)
        header.addWidget(self.status_badge)

        self.main_layout.addLayout(header)

    def setup_domains_tab(self):
        """Tab 1: Blocked Domains with search filtering and monochrome card list."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Search / Filter bar + Add Row
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtrar sitios...")
        self.search_input.textChanged.connect(self.on_filter_changed)
        top_row.addWidget(self.search_input)

        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("Añadir dominio (ej: x.com)...")
        self.domain_input.returnPressed.connect(self.on_add_domain_clicked)
        top_row.addWidget(self.domain_input)

        add_btn = QPushButton("Añadir")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self.on_add_domain_clicked)
        top_row.addWidget(add_btn)
        layout.addLayout(top_row)

        # 2. Quick Presets Bar
        preset_bar = QHBoxLayout()
        preset_bar.setSpacing(6)
        preset_lbl = QLabel("Añadir lote:")
        preset_lbl.setStyleSheet("font-size: 11px; opacity: 0.65;")
        preset_bar.addWidget(preset_lbl)

        btn_social = QPushButton("+ Redes Sociales")
        btn_social.setObjectName("chipBtn")
        btn_social.clicked.connect(lambda: self.add_domain_preset(["x.com", "twitter.com", "instagram.com", "facebook.com", "tiktok.com", "threads.net"]))
        preset_bar.addWidget(btn_social)

        btn_video = QPushButton("+ Streaming")
        btn_video.setObjectName("chipBtn")
        btn_video.clicked.connect(lambda: self.add_domain_preset(["youtube.com", "twitch.tv", "netflix.com", "disneyplus.com", "primevideo.com"]))
        preset_bar.addWidget(btn_video)

        btn_distr = QPushButton("+ Foros y Ocio")
        btn_distr.setObjectName("chipBtn")
        btn_distr.clicked.connect(lambda: self.add_domain_preset(["reddit.com", "9gag.com", "pinterest.com", "discord.com"]))
        preset_bar.addWidget(btn_distr)

        preset_bar.addStretch()

        self.domains_count_lbl = QLabel("15 sitios")
        self.domains_count_lbl.setStyleSheet("font-size: 11px; opacity: 0.7; font-weight: 600;")
        preset_bar.addWidget(self.domains_count_lbl)

        layout.addLayout(preset_bar)

        # 3. Clean Monochrome Domains List
        self.domains_list = QListWidget()
        self.domains_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self.domains_list)

        self.tabs.addTab(tab, "Sitios Bloqueados")

    def setup_rules_tab(self):
        """Tab 2: Curfew and Boot Cooldown rules."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # 1. Curfew Card
        curfew_card = QFrame()
        curfew_card.setStyleSheet("QFrame { border: 1px solid rgba(128,128,128,0.2); border-radius: 6px; padding: 12px; }")
        curfew_layout = QVBoxLayout(curfew_card)
        curfew_layout.setSpacing(10)

        self.curfew_enabled_cb = QCheckBox("Toque de Queda Nocturno (Night Curfew)")
        curfew_layout.addWidget(self.curfew_enabled_cb)

        curfew_desc = QLabel("Bloquea automáticamente el acceso durante la noche para proteger el descanso.")
        curfew_desc.setStyleSheet("font-size: 12px; opacity: 0.7;")
        curfew_desc.setWordWrap(True)
        curfew_layout.addWidget(curfew_desc)

        time_row = QHBoxLayout()
        time_row.setSpacing(14)

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
        boot_card.setStyleSheet("QFrame { border: 1px solid rgba(128,128,128,0.2); border-radius: 6px; padding: 12px; }")
        boot_layout = QVBoxLayout(boot_card)
        boot_layout.setSpacing(10)

        self.boot_enabled_cb = QCheckBox("Cooldown al Iniciar el Sistema (Boot Focus)")
        boot_layout.addWidget(self.boot_enabled_cb)

        boot_desc = QLabel("Aplica un bloqueo temporal al encender el equipo para evitar distracciones tempranas.")
        boot_desc.setStyleSheet("font-size: 12px; opacity: 0.7;")
        boot_desc.setWordWrap(True)
        boot_layout.addWidget(boot_desc)

        dur_row = QHBoxLayout()
        dur_row.addWidget(QLabel("Duración:"))
        self.boot_duration_spin = QSpinBox()
        self.boot_duration_spin.setRange(5, 180)
        self.boot_duration_spin.setSingleStep(5)
        self.boot_duration_spin.setSuffix(" minutos")
        dur_row.addWidget(self.boot_duration_spin)
        dur_row.addStretch()
        boot_layout.addLayout(dur_row)

        layout.addWidget(boot_card)
        layout.addStretch()

        self.tabs.addTab(tab, "Horarios y Reglas")

    def setup_dashboard_tab(self):
        """Tab 3: Hero Dashboard with live status and working quick actions."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # Hero Status Card
        self.hero_card = QFrame()
        self.hero_card.setStyleSheet("QFrame { border: 1px solid rgba(128,128,128,0.25); border-radius: 6px; padding: 14px; }")
        hero_layout = QVBoxLayout(self.hero_card)
        hero_layout.setSpacing(8)

        top_row = QHBoxLayout()
        self.dash_state_title = QLabel("Estado Actual")
        self.dash_state_title.setStyleSheet("font-size: 15px; font-weight: 700;")
        top_row.addWidget(self.dash_state_title)
        top_row.addStretch()
        self.dash_state_pill = QLabel("ESTADO")
        self.dash_state_pill.setStyleSheet("font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(128,128,128,0.4);")
        top_row.addWidget(self.dash_state_pill)
        hero_layout.addLayout(top_row)

        self.dash_countdown_lbl = QLabel("Calculando tiempo...")
        self.dash_countdown_lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #3B82F6;")
        hero_layout.addWidget(self.dash_countdown_lbl)

        self.dash_desc_lbl = QLabel("")
        self.dash_desc_lbl.setStyleSheet("font-size: 12px; opacity: 0.75;")
        self.dash_desc_lbl.setWordWrap(True)
        hero_layout.addWidget(self.dash_desc_lbl)

        layout.addWidget(self.hero_card)

        # Quick Actions
        act_box = QVBoxLayout()
        act_box.setSpacing(8)
        act_box.addWidget(QLabel("Acciones Rápidas"))

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

        # Action feedback label
        self.dash_feedback_lbl = QLabel("")
        self.dash_feedback_lbl.setStyleSheet("font-size: 11px; color: #3B82F6; font-weight: 600;")
        layout.addWidget(self.dash_feedback_lbl)

        layout.addStretch()
        self.tabs.addTab(tab, "Estado y Control")

    def setup_bottom_bar(self):
        """Bottom bar."""
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
        """Fetches configuration from daemon."""
        res = self.ipc.get_config()
        if res.get("status") == "ok":
            self.config_data = res.get("config", {})
            self.blocked_domains = list(self.config_data.get("blocked_domains", []))
            self.render_domains_list()

            curfew = self.config_data.get("curfew", {})
            self.curfew_enabled_cb.setChecked(curfew.get("enabled", True))
            start_parts = [int(x) for x in curfew.get("start_time", "23:15").split(":")]
            end_parts = [int(x) for x in curfew.get("end_time", "07:00").split(":")]
            self.curfew_start_time.setTime(QTime(start_parts[0], start_parts[1]))
            self.curfew_end_time.setTime(QTime(end_parts[0], end_parts[1]))

            boot = self.config_data.get("boot_cooldown", {})
            self.boot_enabled_cb.setChecked(boot.get("enabled", True))
            self.boot_duration_spin.setValue(int(boot.get("duration_minutes", 30)))
        else:
            self.save_feedback_lbl.setText("Servicio fuera de línea.")

    def on_filter_changed(self, text: str):
        """Filters domain list in real time."""
        self.filter_text = text.strip().lower()
        self.render_domains_list()

    def render_domains_list(self):
        """Populates the list with clean, monochrome, perfectly aligned rows."""
        self.domains_list.clear()

        visible_domains = [d for d in self.blocked_domains if not self.filter_text or self.filter_text in d.lower()]
        self.domains_count_lbl.setText(f"{len(visible_domains)} de {len(self.blocked_domains)} sitios")

        is_dark = self.is_dark_mode()
        row_bg = "#181C22" if is_dark else "#FFFFFF"
        row_border = "#2B323F" if is_dark else "#E5E7EB"

        for domain in sorted(visible_domains):
            item = QListWidgetItem()
            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{
                    background-color: {row_bg};
                    border: 1px solid {row_border};
                    border-radius: 5px;
                    padding: 4px 10px;
                }}
                QFrame:hover {{
                    border-color: #3B82F6;
                }}
            """)

            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(6, 4, 6, 4)
            row_layout.setSpacing(10)

            name_lbl = QLabel(domain)
            name_lbl.setStyleSheet("font-weight: 500; font-size: 13px; border: none; background: transparent;")
            row_layout.addWidget(name_lbl)

            row_layout.addStretch()

            del_btn = QPushButton("Eliminar")
            del_btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background: transparent;
                    font-size: 11px;
                    font-weight: 500;
                    color: #8C96A5;
                    padding: 3px 6px;
                }
                QPushButton:hover {
                    color: #EF4444;
                }
            """)
            del_btn.clicked.connect(lambda _, d=domain: self.on_remove_domain(d))
            row_layout.addWidget(del_btn)

            item.setSizeHint(row.sizeHint())
            self.domains_list.addItem(item)
            self.domains_list.setItemWidget(item, row)

    def on_add_domain_clicked(self):
        """Adds cleaned domain."""
        raw = self.domain_input.text()
        domain = sanitize_domain(raw)
        if not domain:
            QMessageBox.warning(self, "Dominio Inválido", "Ingresa un nombre de dominio válido (ej: twitter.com).")
            return

        if domain in self.blocked_domains:
            QMessageBox.information(self, "Dominio Existente", f"'{domain}' ya está en la lista.")
            return

        self.blocked_domains.append(domain)
        self.domain_input.clear()
        self.render_domains_list()

    def add_domain_preset(self, domains: List[str]):
        """Adds preset list."""
        added = 0
        for d in domains:
            if d not in self.blocked_domains:
                self.blocked_domains.append(d)
                added += 1
        if added > 0:
            self.render_domains_list()

    def on_remove_domain(self, domain: str):
        """Removes a domain."""
        if domain in self.blocked_domains:
            self.blocked_domains.remove(domain)
            self.render_domains_list()

    def on_save_clicked(self):
        """Saves configuration to daemon."""
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
        """Updates live status in dashboard tab."""
        res = self.ipc.get_status()
        if res.get("status") != "ok":
            self.status_badge.setText("OFFLINE")
            self.dash_state_title.setText("Servicio Fuera de Línea")
            self.dash_countdown_lbl.setText("Inactivo")
            self.dash_desc_lbl.setText("Inicia el servicio focus-guard.")
            return

        state = res.get("state", "UNLOCKED")
        reason = res.get("reason", "FREE_TIME")
        message = res.get("message", "")
        rem = res.get("remaining_seconds", 0)
        target = res.get("target_time_str", "")
        is_blocking = res.get("is_blocking", False)

        human_time = format_human_time(rem)

        if is_blocking:
            self.status_badge.setText("BLOQUEADO")
            self.dash_state_pill.setText("BLOQUEADO")
            if reason == "CURFEW":
                self.dash_state_title.setText("Toque de Queda Nocturno")
            elif reason == "BOOT_COOLDOWN":
                self.dash_state_title.setText("Cooldown de Arranque")
            else:
                self.dash_state_title.setText("Modo Focus Manual")

            if rem > 0:
                self.dash_countdown_lbl.setText(f"{human_time} restantes")
            else:
                self.dash_countdown_lbl.setText("Bloqueo Activo")

        elif state == "BYPASS":
            self.status_badge.setText("DESCANSO")
            self.dash_state_pill.setText("DESCANSO")
            self.dash_state_title.setText("Descanso Temporal Activo")
            self.dash_countdown_lbl.setText(f"{human_time} restantes")
        else:
            self.status_badge.setText("LIBRE")
            self.dash_state_pill.setText("LIBRE")
            self.dash_state_title.setText("Modo Libre (Sin Restricciones)")
            self.dash_countdown_lbl.setText("Sitios Desbloqueados")

        self.dash_desc_lbl.setText(message + (f" (Hasta las {target})" if target else ""))

    def on_dash_lock_clicked(self):
        """Executes manual lock."""
        res = self.ipc.lock_now()
        self.dash_feedback_lbl.setText("Modo Focus activado.")
        QTimer.singleShot(3000, lambda: self.dash_feedback_lbl.setText(""))
        self.refresh_live_status()

    def on_dash_bypass_clicked(self, minutes: int):
        """Executes bypass request with emergency handling."""
        res = self.ipc.request_bypass(minutes)
        if res.get("status") == "ok":
            self.dash_feedback_lbl.setText(f"Descanso de {minutes}m activado.")
        else:
            # If rejected because of curfew, offer emergency prompt
            status = self.ipc.get_status()
            if status.get("in_curfew"):
                phrase = "necesito desbloqueo de emergencia"
                text, ok = QInputDialog.getText(
                    self,
                    "Desbloqueo de Emergencia (15m)",
                    f"El Toque de Queda está activo.\nPara confirmar la excepción de trabajo, escribe:\n<b>{phrase}</b>"
                )
                if ok and text.strip().lower() == phrase:
                    emerg_res = self.ipc.request_emergency_bypass(15)
                    if emerg_res.get("status") == "ok":
                        self.dash_feedback_lbl.setText("Desbloqueo de emergencia activado (15m).")
                    else:
                        self.dash_feedback_lbl.setText("No se pudo activar el desbloqueo.")
                elif ok:
                    self.dash_feedback_lbl.setText("Frase no coincide.")
            else:
                self.dash_feedback_lbl.setText(res.get("message", "Bypass denegado."))

        QTimer.singleShot(3000, lambda: self.dash_feedback_lbl.setText(""))
        self.refresh_live_status()

    def on_dash_unlock_clicked(self):
        """Executes manual unlock."""
        res = self.ipc.unlock_now()
        if res.get("status") == "ok":
            self.dash_feedback_lbl.setText("Sitios desbloqueados.")
        else:
            self.dash_feedback_lbl.setText(res.get("message", "No se puede desbloquear ahora."))
        QTimer.singleShot(3000, lambda: self.dash_feedback_lbl.setText(""))
        self.refresh_live_status()
