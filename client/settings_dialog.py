"""
Focus-Guard Settings & Dashboard Dialog.
Features: Auto-save, Autostart management, Pomodoro focus sessions, keyboard shortcuts, and zero data loss.
"""
import os
import re
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QTabWidget, QWidget, QCheckBox,
    QTimeEdit, QSpinBox, QFrame, QMessageBox, QApplication, QMenu
)
from PyQt6.QtGui import QIcon, QPalette, QKeySequence, QShortcut
from PyQt6.QtCore import Qt, QTime, QTimer, pyqtSignal

from client.ipc_client import FocusIPCClient

AUTOSTART_PATH = os.path.expanduser("~/.config/autostart/focus-guard.desktop")


def is_autostart_enabled() -> bool:
    """Checks if autostart desktop entry exists for the current user."""
    return os.path.exists(AUTOSTART_PATH)


def set_autostart_enabled(enabled: bool) -> bool:
    """Enables or disables desktop autostart for the current user."""
    try:
        if enabled:
            os.makedirs(os.path.dirname(AUTOSTART_PATH), exist_ok=True)
            content = (
                "[Desktop Entry]\n"
                "Name=Focus-Guard\n"
                "Comment=Anti-procrastination website blocker and focus regulator\n"
                "Exec=python3 /opt/focus-guard/client/main.py\n"
                "Icon=/opt/focus-guard/resources/icon-active.svg\n"
                "Terminal=false\n"
                "Type=Application\n"
                "Categories=Utility;System;\n"
                "StartupNotify=false\n"
                "X-GNOME-Autostart-enabled=true\n"
            )
            with open(AUTOSTART_PATH, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            if os.path.exists(AUTOSTART_PATH):
                os.unlink(AUTOSTART_PATH)
        return True
    except Exception as e:
        return False


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


class EmergencyPromptDialog(QDialog):
    """Clean custom dialog for emergency unlock verification without broken HTML."""
    def __init__(self, phrase: str, parent=None):
        super().__init__(parent)
        self.phrase = phrase.strip()
        self.confirmed = False

        self.setWindowTitle("Desbloqueo de Emergencia")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Toque de Queda Nocturno Activo")
        title.setStyleSheet("font-size: 14px; font-weight: 700;")
        layout.addWidget(title)

        desc = QLabel("Para confirmar una excepción de trabajo real, escribe la frase de confirmación:")
        desc.setStyleSheet("font-size: 12px; opacity: 0.8;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        phrase_box = QLabel(self.phrase)
        phrase_box.setStyleSheet("""
            background-color: #1E232B;
            border: 1px solid #2F3746;
            border-radius: 4px;
            padding: 8px 12px;
            font-family: monospace;
            font-size: 12px;
            font-weight: 600;
            color: #3B82F6;
        """)
        phrase_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(phrase_box)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Escribe la frase aquí...")
        self.input_field.returnPressed.connect(self.on_confirm)
        layout.addWidget(self.input_field)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        confirm_btn = QPushButton("Confirmar Desbloqueo (15m)")
        confirm_btn.setObjectName("primaryBtn")
        confirm_btn.clicked.connect(self.on_confirm)
        btn_row.addWidget(confirm_btn)

        layout.addLayout(btn_row)

    def on_confirm(self):
        entered = self.input_field.text().strip().lower()
        if entered == self.phrase.lower():
            self.confirmed = True
            self.accept()
        else:
            QMessageBox.warning(self, "Frase Incorrecta", "La frase ingresada no coincide exactamente. El bloqueo nocturno se mantiene.")


class SettingsDialog(QDialog):
    config_saved = pyqtSignal()

    def __init__(self, ipc_client: FocusIPCClient, resource_dir: str, parent=None):
        super().__init__(parent)
        self.ipc = ipc_client
        self.resource_dir = resource_dir
        self.config_data: Dict[str, Any] = {}
        self.blocked_domains: List[str] = []

        self.setWindowTitle("Focus-Guard — Panel de Control y Ajustes")
        self.setMinimumSize(600, 560)
        self.resize(640, 580)

        self.apply_theme_styles()

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

        # 4. Keyboard Shortcuts
        QShortcut(QKeySequence("Ctrl+S"), self, self.on_save_clicked)
        QShortcut(QKeySequence("Escape"), self, self.close)

        # Load initial config
        self.load_configuration()

        # Live poll timer
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.refresh_live_status)
        self.poll_timer.start(1500)

    def is_dark_mode(self) -> bool:
        bg = self.palette().color(QPalette.ColorRole.Window)
        return bg.lightness() < 128

    def apply_theme_styles(self):
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
            QPushButton:disabled {{
                opacity: 0.5;
                color: #6B7280;
                background-color: {bg_card_inner};
                border: 1px solid {border_color};
            }}
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
        header = QHBoxLayout()
        header.setSpacing(12)

        self.header_icon_lbl = QLabel()
        self.header_icon_lbl.setPixmap(QIcon(os.path.join(self.resource_dir, "icon-active.svg")).pixmap(30, 30))
        header.addWidget(self.header_icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title_lbl = QLabel("Focus-Guard")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700;")
        sub_lbl = QLabel("Control de Reglas y Dominios")
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
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Direct Input Row
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("Ingresa un dominio a bloquear (ej: twitter.com)...")
        self.domain_input.returnPressed.connect(self.on_add_domain_clicked)
        top_row.addWidget(self.domain_input)

        add_btn = QPushButton("Añadir")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self.on_add_domain_clicked)
        top_row.addWidget(add_btn)
        layout.addLayout(top_row)

        # Header with counter and inline auto-save feedback
        count_row = QHBoxLayout()
        self.domains_count_lbl = QLabel("Sitios Bloqueados")
        self.domains_count_lbl.setStyleSheet("font-size: 12px; font-weight: 600; opacity: 0.8;")
        count_row.addWidget(self.domains_count_lbl)

        count_row.addStretch()

        self.domain_auto_feedback_lbl = QLabel("")
        self.domain_auto_feedback_lbl.setStyleSheet("font-size: 11px; color: #10B981; font-weight: 600;")
        count_row.addWidget(self.domain_auto_feedback_lbl)
        layout.addLayout(count_row)

        # Clean List
        self.domains_list = QListWidget()
        self.domains_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        layout.addWidget(self.domains_list)

        self.tabs.addTab(tab, "Sitios Bloqueados")

    def setup_rules_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        # 1. System Integration Card
        sys_card = QFrame()
        sys_card.setStyleSheet("QFrame { border: 1px solid rgba(128,128,128,0.2); border-radius: 6px; padding: 12px; }")
        sys_layout = QVBoxLayout(sys_card)
        sys_layout.setSpacing(6)

        self.autostart_cb = QCheckBox("Iniciar Focus-Guard automáticamente al encender el equipo")
        self.autostart_cb.setChecked(is_autostart_enabled())
        self.autostart_cb.toggled.connect(self.on_autostart_toggled)
        sys_layout.addWidget(self.autostart_cb)
        layout.addWidget(sys_card)

        # 2. Curfew Card
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

        # 3. Boot Cooldown Card
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

        # 4. Configurable Bypasses & Emergency Rules Card
        bypass_card = QFrame()
        bypass_card.setStyleSheet("QFrame { border: 1px solid rgba(128,128,128,0.2); border-radius: 6px; padding: 12px; }")
        bypass_layout = QVBoxLayout(bypass_card)
        bypass_layout.setSpacing(10)

        self.bypasses_enabled_cb = QCheckBox("Permitir descansos temporales (Bypass de 15/30m)")
        bypass_layout.addWidget(self.bypasses_enabled_cb)

        self.curfew_emerg_cb = QCheckBox("Permitir desbloqueo de emergencia durante Toque de Queda")
        bypass_layout.addWidget(self.curfew_emerg_cb)

        phrase_row = QHBoxLayout()
        phrase_lbl = QLabel("Frase de confirmación para emergencias:")
        phrase_lbl.setStyleSheet("font-size: 12px; opacity: 0.8;")
        phrase_row.addWidget(phrase_lbl)

        self.emergency_phrase_input = QLineEdit()
        self.emergency_phrase_input.setPlaceholderText("ej: necesito desbloqueo de emergencia")
        phrase_row.addWidget(self.emergency_phrase_input)
        bypass_layout.addLayout(phrase_row)

        layout.addWidget(bypass_card)

        layout.addStretch()
        self.tabs.addTab(tab, "Horarios y Reglas")

    def setup_dashboard_tab(self):
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
        self.dash_countdown_lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #10B981;")
        hero_layout.addWidget(self.dash_countdown_lbl)

        self.dash_desc_lbl = QLabel("")
        self.dash_desc_lbl.setStyleSheet("font-size: 12px; opacity: 0.75;")
        self.dash_desc_lbl.setWordWrap(True)
        hero_layout.addWidget(self.dash_desc_lbl)

        layout.addWidget(self.hero_card)

        # Contextual Action Area with Focus Sessions (Pomodoro)
        act_box = QVBoxLayout()
        act_box.setSpacing(8)
        act_box.addWidget(QLabel("Sesiones de Enfoque y Control"))

        self.action_btn_row = QHBoxLayout()
        self.action_btn_row.setSpacing(8)

        self.btn_primary_action = QPushButton("Bloquear Ahora")
        self.btn_primary_action.setObjectName("primaryBtn")
        self.btn_primary_action.clicked.connect(self.on_primary_action_clicked)
        self.action_btn_row.addWidget(self.btn_primary_action)

        self.btn_pomodoro_25 = QPushButton("Pomodoro (25m)")
        self.btn_pomodoro_25.setObjectName("secondaryBtn")
        self.btn_pomodoro_25.clicked.connect(lambda: self.start_focus_session(25))
        self.action_btn_row.addWidget(self.btn_pomodoro_25)

        self.btn_pomodoro_50 = QPushButton("Enfoque (50m)")
        self.btn_pomodoro_50.setObjectName("secondaryBtn")
        self.btn_pomodoro_50.clicked.connect(lambda: self.start_focus_session(50))
        self.action_btn_row.addWidget(self.btn_pomodoro_50)

        self.btn_secondary_action = QPushButton("Descanso (15m)")
        self.btn_secondary_action.setObjectName("secondaryBtn")
        self.btn_secondary_action.clicked.connect(self.on_secondary_action_clicked)
        self.action_btn_row.addWidget(self.btn_secondary_action)

        act_box.addLayout(self.action_btn_row)
        layout.addLayout(act_box)

        # Action feedback label
        self.dash_feedback_lbl = QLabel("")
        self.dash_feedback_lbl.setStyleSheet("font-size: 11px; color: #10B981; font-weight: 600;")
        layout.addWidget(self.dash_feedback_lbl)

        layout.addStretch()
        self.tabs.addTab(tab, "Estado y Control")

    def setup_bottom_bar(self):
        bottom = QHBoxLayout()
        bottom.setSpacing(10)

        self.save_feedback_lbl = QLabel("")
        self.save_feedback_lbl.setStyleSheet("font-size: 12px; color: #10B981; font-weight: 600;")
        bottom.addWidget(self.save_feedback_lbl)

        bottom.addStretch()

        close_btn = QPushButton("Cerrar (Esc)")
        close_btn.setObjectName("secondaryBtn")
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)

        self.save_btn = QPushButton("Guardar Cambios (Ctrl+S)")
        self.save_btn.setObjectName("primaryBtn")
        self.save_btn.clicked.connect(self.on_save_clicked)
        bottom.addWidget(self.save_btn)

        self.main_layout.addLayout(bottom)

    def load_configuration(self):
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

            bypasses = self.config_data.get("bypasses", {})
            self.bypasses_enabled_cb.setChecked(bypasses.get("enabled", True))
            self.curfew_emerg_cb.setChecked(bypasses.get("allow_during_curfew", False))
            self.emergency_phrase_input.setText(bypasses.get("emergency_phrase", "necesito desbloqueo de emergencia"))
        else:
            self.save_feedback_lbl.setText("Servicio fuera de línea.")

    def on_autostart_toggled(self, checked: bool):
        """Manages autostart desktop file."""
        set_autostart_enabled(checked)

    def render_domains_list(self):
        self.domains_list.clear()
        self.domains_count_lbl.setText(f"Sitios Bloqueados ({len(self.blocked_domains)})")

        is_dark = self.is_dark_mode()
        row_bg = "#181C22" if is_dark else "#FFFFFF"
        row_border = "#2B323F" if is_dark else "#E5E7EB"

        for domain in sorted(self.blocked_domains):
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
            row_layout.setContentsMargins(8, 4, 8, 4)
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
        raw = self.domain_input.text()
        domain = sanitize_domain(raw)
        if not domain:
            self.domain_auto_feedback_lbl.setStyleSheet("font-size: 11px; color: #EF4444; font-weight: 600;")
            self.domain_auto_feedback_lbl.setText("Dominio inválido")
            QTimer.singleShot(2500, lambda: self.domain_auto_feedback_lbl.setText(""))
            return

        if domain in self.blocked_domains:
            self.domain_auto_feedback_lbl.setStyleSheet("font-size: 11px; color: #F59E0B; font-weight: 600;")
            self.domain_auto_feedback_lbl.setText("Ya está en la lista")
            QTimer.singleShot(2500, lambda: self.domain_auto_feedback_lbl.setText(""))
            return

        self.blocked_domains.append(domain)
        self.domain_input.clear()
        self.render_domains_list()

        # Instant Auto-Save on Add
        self.auto_save_domains(feedback_text=f"'{domain}' añadido y guardado")

    def on_remove_domain(self, domain: str):
        if domain in self.blocked_domains:
            self.blocked_domains.remove(domain)
            self.render_domains_list()
            # Instant Auto-Save on Remove
            self.auto_save_domains(feedback_text=f"'{domain}' eliminado")

    def auto_save_domains(self, feedback_text: str = "Guardado"):
        """Silently auto-saves domain modifications to daemon."""
        updated_config = dict(self.config_data)
        updated_config["blocked_domains"] = self.blocked_domains

        res = self.ipc.save_config(updated_config)
        if res.get("status") == "ok":
            self.config_data = updated_config
            self.config_saved.emit()
            self.domain_auto_feedback_lbl.setStyleSheet("font-size: 11px; color: #10B981; font-weight: 600;")
            self.domain_auto_feedback_lbl.setText(f"✓ {feedback_text}")
            QTimer.singleShot(2500, lambda: self.domain_auto_feedback_lbl.setText(""))

    def on_save_clicked(self):
        curfew_cfg = {
            "enabled": self.curfew_enabled_cb.isChecked(),
            "start_time": self.curfew_start_time.time().toString("HH:mm"),
            "end_time": self.curfew_end_time.time().toString("HH:mm")
        }

        boot_cfg = {
            "enabled": self.boot_enabled_cb.isChecked(),
            "duration_minutes": self.boot_duration_spin.value()
        }

        bypasses_cfg = {
            "enabled": self.bypasses_enabled_cb.isChecked(),
            "allow_during_curfew": self.curfew_emerg_cb.isChecked(),
            "emergency_phrase": self.emergency_phrase_input.text().strip() or "necesito desbloqueo de emergencia"
        }

        updated_config = dict(self.config_data)
        updated_config["blocked_domains"] = self.blocked_domains
        updated_config["curfew"] = curfew_cfg
        updated_config["boot_cooldown"] = boot_cfg
        updated_config["bypasses"] = bypasses_cfg

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
        res = self.ipc.get_status()
        if res.get("status") != "ok":
            self.status_badge.setText("OFFLINE")
            self.status_badge.setStyleSheet("background-color: #4B5563; color: #FFF; font-weight: 700; padding: 4px 10px; border-radius: 6px;")
            self.header_icon_lbl.setPixmap(QIcon(os.path.join(self.resource_dir, "icon-offline.svg")).pixmap(30, 30))
            self.dash_state_title.setText("Servicio Fuera de Línea")
            self.dash_countdown_lbl.setText("Inactivo")
            self.dash_desc_lbl.setText("Inicia el servicio focus-guard.")
            self.btn_primary_action.setEnabled(False)
            self.btn_pomodoro_25.setVisible(False)
            self.btn_pomodoro_50.setVisible(False)
            self.btn_secondary_action.setEnabled(False)
            return

        state = res.get("state", "UNLOCKED")
        reason = res.get("reason", "FREE_TIME")
        message = res.get("message", "")
        rem = res.get("remaining_seconds", 0)
        target = res.get("target_time_str", "")
        is_blocking = res.get("is_blocking", False)
        bypasses_enabled = res.get("bypasses_enabled", True)

        human_time = format_human_time(rem)

        # Inverted Guard Logic: Green = Protected, Red = Inactive/Free, Amber = Break
        if state == "UNLOCKED":
            self.status_badge.setText("APAGADO / LIBRE")
            self.status_badge.setStyleSheet("background-color: #EF4444; color: #FFF; font-weight: 700; padding: 4px 10px; border-radius: 6px;")
            self.header_icon_lbl.setPixmap(QIcon(os.path.join(self.resource_dir, "icon-idle.svg")).pixmap(30, 30))
            self.dash_state_pill.setText("DESPROTEGIDO")
            self.dash_state_pill.setStyleSheet("border-color: #EF4444; color: #EF4444; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px;")
            self.dash_state_title.setText("Modo Libre (Sin Protección)")
            self.dash_countdown_lbl.setText("Sitios Desbloqueados")
            self.dash_countdown_lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #EF4444;")
            self.dash_desc_lbl.setText("El bloqueo no está activo. Puedes iniciar una sesión de enfoque cuando gustes.")

            self.btn_primary_action.setText("Bloquear Indefinido")
            self.btn_primary_action.setEnabled(True)
            self.btn_pomodoro_25.setVisible(True)
            self.btn_pomodoro_50.setVisible(True)
            self.btn_secondary_action.setVisible(False)

        elif state == "BYPASS":
            self.status_badge.setText("DESCANSO")
            self.status_badge.setStyleSheet("background-color: #F59E0B; color: #FFF; font-weight: 700; padding: 4px 10px; border-radius: 6px;")
            self.header_icon_lbl.setPixmap(QIcon(os.path.join(self.resource_dir, "icon-bypass.svg")).pixmap(30, 30))
            self.dash_state_pill.setText("PAUSA")
            self.dash_state_pill.setStyleSheet("border-color: #F59E0B; color: #F59E0B; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px;")
            self.dash_state_title.setText("Descanso Temporal Activo")
            self.dash_countdown_lbl.setText(f"{human_time} restantes")
            self.dash_countdown_lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #F59E0B;")
            self.dash_desc_lbl.setText("Acceso concedido temporalmente.")

            self.btn_primary_action.setText("Terminar Descanso y Bloquear")
            self.btn_primary_action.setEnabled(True)
            self.btn_pomodoro_25.setVisible(False)
            self.btn_pomodoro_50.setVisible(False)
            self.btn_secondary_action.setVisible(False)

        elif is_blocking:
            self.status_badge.setText("PROTEGIDO")
            self.status_badge.setStyleSheet("background-color: #10B981; color: #FFF; font-weight: 700; padding: 4px 10px; border-radius: 6px;")
            self.dash_state_pill.setText("ACTIVO")
            self.dash_state_pill.setStyleSheet("border-color: #10B981; color: #10B981; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px;")
            self.dash_countdown_lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #10B981;")
            self.btn_pomodoro_25.setVisible(False)
            self.btn_pomodoro_50.setVisible(False)

            if reason == "CURFEW":
                self.header_icon_lbl.setPixmap(QIcon(os.path.join(self.resource_dir, "icon-curfew.svg")).pixmap(30, 30))
                self.dash_state_title.setText("Toque de Queda Nocturno")
                self.dash_desc_lbl.setText(f"Protección nocturna activa hasta las {target}.")
                self.btn_primary_action.setText("Bloqueo Nocturno Activo")
                self.btn_primary_action.setEnabled(False)

                if self.curfew_emerg_cb.isChecked():
                    self.btn_secondary_action.setText("Desbloqueo de Emergencia (15m)")
                    self.btn_secondary_action.setVisible(True)
                    self.btn_secondary_action.setEnabled(True)
                else:
                    self.btn_secondary_action.setVisible(False)

            elif reason == "BOOT_COOLDOWN":
                self.header_icon_lbl.setPixmap(QIcon(os.path.join(self.resource_dir, "icon-boot.svg")).pixmap(30, 30))
                self.dash_state_title.setText("Cooldown de Arranque")
                self.dash_desc_lbl.setText(f"Protección de inicio activa hasta las {target}.")
                self.btn_primary_action.setText("Bloqueo de Inicio Activo")
                self.btn_primary_action.setEnabled(False)

                if bypasses_enabled:
                    self.btn_secondary_action.setText("Tomar Descanso (15m)")
                    self.btn_secondary_action.setVisible(True)
                    self.btn_secondary_action.setEnabled(True)
                else:
                    self.btn_secondary_action.setVisible(False)

            elif reason == "MANUAL_LOCK":
                self.header_icon_lbl.setPixmap(QIcon(os.path.join(self.resource_dir, "icon-active.svg")).pixmap(30, 30))
                self.dash_state_title.setText("Modo Focus Manual")
                self.dash_desc_lbl.setText("Protección activada manualmente.")
                self.btn_primary_action.setText("Desbloquear Sitios")
                self.btn_primary_action.setEnabled(True)

                if bypasses_enabled:
                    self.btn_secondary_action.setText("Tomar Descanso (15m)")
                    self.btn_secondary_action.setVisible(True)
                    self.btn_secondary_action.setEnabled(True)
                else:
                    self.btn_secondary_action.setVisible(False)

            if rem > 0:
                self.dash_countdown_lbl.setText(f"{human_time} restantes")
            else:
                self.dash_countdown_lbl.setText("Protección Activa")

    def start_focus_session(self, minutes: int):
        """Starts a timed focus session (Pomodoro)."""
        self.ipc.lock_now(duration_minutes=minutes)
        self.dash_feedback_lbl.setText(f"Sesión de enfoque de {minutes} minutos iniciada.")
        QTimer.singleShot(3000, lambda: self.dash_feedback_lbl.setText(""))
        self.refresh_live_status()

    def on_primary_action_clicked(self):
        res = self.ipc.get_status()
        state = res.get("state", "UNLOCKED")
        reason = res.get("reason", "FREE_TIME")

        if state == "UNLOCKED":
            self.ipc.lock_now()
            self.dash_feedback_lbl.setText("Modo Focus activado.")
        elif state == "BYPASS":
            self.ipc.cancel_bypass()
            self.dash_feedback_lbl.setText("Descanso finalizado. Modo Focus reactivado.")
        elif reason == "MANUAL_LOCK":
            self.ipc.unlock_now()
            self.dash_feedback_lbl.setText("Sitios desbloqueados.")

        QTimer.singleShot(3000, lambda: self.dash_feedback_lbl.setText(""))
        self.refresh_live_status()

    def on_secondary_action_clicked(self):
        res = self.ipc.get_status()
        in_curfew = res.get("in_curfew", False)

        if in_curfew:
            phrase = self.emergency_phrase_input.text().strip() or "necesito desbloqueo de emergencia"
            dialog = EmergencyPromptDialog(phrase=phrase, parent=self)
            if dialog.exec() == QDialog.DialogCode.Accepted and dialog.confirmed:
                emerg_res = self.ipc.request_emergency_bypass(15)
                if emerg_res.get("status") == "ok":
                    self.dash_feedback_lbl.setText("Desbloqueo de emergencia concedido por 15 minutos.")
                else:
                    self.dash_feedback_lbl.setText("No se pudo activar el desbloqueo.")
        else:
            bypass_res = self.ipc.request_bypass(15)
            if bypass_res.get("status") == "ok":
                self.dash_feedback_lbl.setText("Descanso de 15 minutos activado.")
            else:
                self.dash_feedback_lbl.setText(bypass_res.get("message", "No se pudo activar."))

        QTimer.singleShot(3000, lambda: self.dash_feedback_lbl.setText(""))
        self.refresh_live_status()
