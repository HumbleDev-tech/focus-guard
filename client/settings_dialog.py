"""
Focus-Guard Settings & Dashboard Dialog.
Unified KDE Plasma 6 / Wayland HIG Design System.
Features: Auto-save, Category presets, Slim scrollbars, Pomodoro grid, Telemetry widgets, and Custom About Modal.
"""
import os
import re
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QTabWidget, QWidget, QCheckBox,
    QTimeEdit, QSpinBox, QFrame, QProgressBar, QGridLayout, QApplication,
    QScrollArea, QAbstractItemView, QToolTip
)
from PyQt6.QtGui import QIcon, QPalette, QKeySequence, QShortcut
from PyQt6.QtCore import Qt, QTime, QTimer, pyqtSignal, QSize, QObject, QEvent

from client.ipc_client import FocusIPCClient

USER_AUTOSTART_PATH = os.path.expanduser("~/.config/autostart/focus-guard.desktop")
SYSTEM_AUTOSTART_PATH = "/etc/xdg/autostart/focus-guard.desktop"
AUTOSTART_PATH = USER_AUTOSTART_PATH  # Backward compatibility



def is_autostart_enabled() -> bool:
    """Checks if autostart is enabled per XDG specifications."""
    if os.path.exists(USER_AUTOSTART_PATH):
        try:
            with open(USER_AUTOSTART_PATH, "r", encoding="utf-8") as f:
                content = f.read()
                if "Hidden=true" in content or "X-GNOME-Autostart-enabled=false" in content:
                    return False
                return True
        except Exception:
            return False
    return os.path.exists(SYSTEM_AUTOSTART_PATH)


def set_autostart_enabled(enabled: bool) -> bool:
    """Enables or disables desktop autostart conforming to XDG Desktop specifications."""
    try:
        os.makedirs(os.path.dirname(USER_AUTOSTART_PATH), exist_ok=True)
        if enabled:
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
                "Hidden=false\n"
                "X-GNOME-Autostart-enabled=true\n"
            )
            with open(USER_AUTOSTART_PATH, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            if os.path.exists(SYSTEM_AUTOSTART_PATH):
                content = (
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    "Name=Focus-Guard\n"
                    "Hidden=true\n"
                    "X-GNOME-Autostart-enabled=false\n"
                )
                with open(USER_AUTOSTART_PATH, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                if os.path.exists(USER_AUTOSTART_PATH):
                    os.unlink(USER_AUTOSTART_PATH)
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
    """Custom dialog for emergency unlock verification without broken HTML."""
    def __init__(self, phrase: str, parent=None):
        super().__init__(parent)
        self.phrase = phrase.strip()
        self.confirmed = False

        self.setWindowTitle("Desbloqueo de Emergencia")
        self.setMinimumWidth(440)
        self.setStyleSheet("""
            QDialog {
                background-color: #0D1117;
                color: #F0F6FC;
                font-family: system-ui, -apple-system, sans-serif;
            }
            QLineEdit {
                background-color: #161B22;
                color: #F0F6FC;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QPushButton#primaryBtn {
                background-color: #388BFD;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton#secondaryBtn {
                background-color: #161B22;
                color: #F0F6FC;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Toque de Queda Nocturno Activo")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #F0F6FC;")
        layout.addWidget(title)

        desc = QLabel("Para confirmar una excepción de trabajo real, escribe la frase de confirmación:")
        desc.setStyleSheet("font-size: 12px; color: #8B949E;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        phrase_container = QFrame()
        phrase_container.setStyleSheet("""
            QFrame {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 6px;
            }
        """)
        phrase_box_layout = QHBoxLayout(phrase_container)
        phrase_box_layout.setContentsMargins(10, 6, 8, 6)
        phrase_box_layout.setSpacing(10)

        phrase_box = QLabel(self.phrase)
        phrase_box.setStyleSheet("""
            background: transparent;
            border: none;
            font-family: monospace;
            font-size: 12.5px;
            font-weight: 600;
            color: #58A6FF;
        """)
        phrase_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        phrase_box_layout.addWidget(phrase_box)

        phrase_box_layout.addStretch()

        self.copy_btn = QPushButton("Copiar Frase")
        self.copy_btn.setObjectName("secondaryBtn")
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262D;
                border: 1px solid #30363D;
                color: #F0F6FC;
                font-size: 11px;
                font-weight: 600;
                border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: #30363D;
                color: #58A6FF;
                border-color: #58A6FF;
            }
        """)
        self.copy_btn.setToolTip("Copiar frase al portapapeles")
        self.copy_btn.clicked.connect(self.on_copy_phrase)
        phrase_box_layout.addWidget(self.copy_btn)

        layout.addWidget(phrase_container)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Escribe o pega la frase exactamente aquí...")
        self.input_field.returnPressed.connect(self.on_confirm)
        layout.addWidget(self.input_field)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        confirm_btn = QPushButton("Confirmar Desbloqueo (15 min)")
        confirm_btn.setObjectName("primaryBtn")
        confirm_btn.clicked.connect(self.on_confirm)
        btn_row.addWidget(confirm_btn)

        layout.addLayout(btn_row)

    def on_copy_phrase(self):
        QApplication.clipboard().setText(self.phrase)
        if hasattr(self, "copy_btn"):
            self.copy_btn.setText("Copiado")
            QTimer.singleShot(2000, lambda: self.copy_btn.setText("Copiar Frase"))
        if hasattr(self, "input_field") and self.input_field:
            self.input_field.setFocus()

    def on_confirm(self):
        if not self.phrase or not self.input_field:
            self.confirmed = True
            self.accept()
            return
        entered = self.input_field.text().strip().lower()
        if entered == self.phrase.lower():
            self.confirmed = True
            self.accept()
        else:
            self.input_field.setStyleSheet("border: 1px solid #F85149;")


class ConfirmDomainRemovalDialog(QDialog):
    """Friction modal to prevent impulsive deletion of blocked sites during active protection."""
    def __init__(self, domain: str, reason_str: str, phrase: str, parent=None):
        super().__init__(parent)
        self.domain = domain
        self.phrase = phrase.strip()
        self.confirmed = False

        self.setWindowTitle("Protección contra Impulsos")
        self.setMinimumWidth(440)
        self.setStyleSheet("""
            QDialog {
                background-color: #0D1117;
                color: #F0F6FC;
                font-family: system-ui, -apple-system, sans-serif;
            }
            QLineEdit {
                background-color: #161B22;
                color: #F0F6FC;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QPushButton#dangerBtn {
                background-color: #DA3633;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton#dangerBtn:hover {
                background-color: #F85149;
            }
            QPushButton#secondaryBtn {
                background-color: #161B22;
                color: #F0F6FC;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(f"Protección de Enfoque Activa")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #F0F6FC;")
        layout.addWidget(title)

        desc = QLabel(
            f"El escudo de protección está activo actualmente (<b>{reason_str}</b>). "
            f"Eliminar <b>{self.domain}</b> ahora desbloqueará el sitio de forma inmediata."
        )
        desc.setStyleSheet("font-size: 12px; color: #8B949E; line-height: 1.4;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        if self.phrase:
            instruction = QLabel("Para confirmar que no es un impulso y eliminar el sitio, escribe la frase de seguridad:")
            instruction.setStyleSheet("font-size: 12px; color: #F0F6FC; font-weight: 500;")
            instruction.setWordWrap(True)
            layout.addWidget(instruction)

            phrase_container = QFrame()
            phrase_container.setStyleSheet("""
                QFrame {
                    background-color: #161B22;
                    border: 1px solid #30363D;
                    border-radius: 6px;
                }
            """)
            phrase_box_layout = QHBoxLayout(phrase_container)
            phrase_box_layout.setContentsMargins(10, 6, 8, 6)
            phrase_box_layout.setSpacing(10)

            phrase_box = QLabel(self.phrase)
            phrase_box.setStyleSheet("""
                background: transparent;
                border: none;
                font-family: monospace;
                font-size: 12.5px;
                font-weight: 600;
                color: #58A6FF;
            """)
            phrase_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
            phrase_box_layout.addWidget(phrase_box)

            phrase_box_layout.addStretch()

            self.copy_btn = QPushButton("Copiar Frase")
            self.copy_btn.setObjectName("secondaryBtn")
            self.copy_btn.setStyleSheet("""
                QPushButton {
                    background-color: #21262D;
                    border: 1px solid #30363D;
                    color: #F0F6FC;
                    font-size: 11px;
                    font-weight: 600;
                    border-radius: 4px;
                    padding: 4px 10px;
                }
                QPushButton:hover {
                    background-color: #30363D;
                    color: #58A6FF;
                    border-color: #58A6FF;
                }
            """)
            self.copy_btn.setToolTip("Copiar frase al portapapeles")
            self.copy_btn.clicked.connect(self.on_copy_phrase)
            phrase_box_layout.addWidget(self.copy_btn)

            layout.addWidget(phrase_container)

            self.input_field = QLineEdit()
            self.input_field.setPlaceholderText("Escribe o pega la frase exactamente aquí...")
            self.input_field.returnPressed.connect(self.on_confirm)
            layout.addWidget(self.input_field)
        else:
            self.input_field = None

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        del_btn = QPushButton(f"Eliminar {self.domain}")
        del_btn.setObjectName("dangerBtn")
        del_btn.clicked.connect(self.on_confirm)
        btn_row.addWidget(del_btn)

        layout.addLayout(btn_row)

    def on_copy_phrase(self):
        QApplication.clipboard().setText(self.phrase)
        if hasattr(self, "copy_btn"):
            self.copy_btn.setText("Copiado")
            QTimer.singleShot(2000, lambda: self.copy_btn.setText("Copiar Frase"))
        if hasattr(self, "input_field") and self.input_field:
            self.input_field.setFocus()

    def on_confirm(self):
        if self.input_field:
            entered = self.input_field.text().strip().lower()
            if entered == self.phrase.lower():
                self.confirmed = True
                self.accept()
            else:
                self.input_field.setStyleSheet("border: 1px solid #F85149; background-color: #161B22; color: #F0F6FC; border-radius: 6px; padding: 8px 12px;")
        else:
            self.confirmed = True
            self.accept()


class AboutDialog(QDialog):
    """Sleek modern About dialog matching KDE Plasma 6 dark aesthetic."""
    def __init__(self, resource_dir: str, config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Acerca de Focus-Guard")
        self.setFixedSize(480, 420)
        self.setStyleSheet("""
            QDialog {
                background-color: #0D1117;
                color: #F0F6FC;
                font-family: system-ui, -apple-system, sans-serif;
            }
            QPushButton#primaryBtn {
                background-color: #388BFD;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton#primaryBtn:hover {
                background-color: #1F6FEB;
            }
            QFrame#infoCard {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 14px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(14)

        # Header with Logo
        header = QHBoxLayout()
        header.setSpacing(14)

        icon_lbl = QLabel()
        icon_path = os.path.join(resource_dir, "icon-active.svg")
        if os.path.exists(icon_path):
            icon_lbl.setPixmap(QIcon(icon_path).pixmap(48, 48))
        header.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        app_name = QLabel("Focus-Guard")
        app_name.setStyleSheet("font-size: 18px; font-weight: 800; color: #F0F6FC;")
        app_ver = QLabel("Versión 1.0.0 (Linux Edition) • KDE Plasma 6 / Wayland")
        app_ver.setStyleSheet("font-size: 11px; color: #8B949E; font-weight: 500;")
        title_box.addWidget(app_name)
        title_box.addWidget(app_ver)
        header.addLayout(title_box)
        header.addStretch()
        layout.addLayout(header)

        desc = QLabel("Anti-procrastinación y regulador de dopamina a nivel de sistema. Bloquea distracciones en /etc/hosts con separación estricta de privilegios.")
        desc.setStyleSheet("font-size: 12px; color: #8B949E; line-height: 1.4;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Architecture and Rules Card
        card = QFrame()
        card.setObjectName("infoCard")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)

        curfew = config.get("curfew", {})
        boot = config.get("boot_cooldown", {})
        domains = config.get("blocked_domains", [])

        curfew_txt = f"{curfew.get('start_time', '23:15')} a {curfew.get('end_time', '07:00')}" if curfew.get('enabled') else "Desactivado"
        boot_txt = f"{boot.get('duration_minutes', 30)} minutos" if boot.get('enabled') else "Desactivado"

        def make_row(lbl_txt, val_txt):
            r = QHBoxLayout()
            l = QLabel(lbl_txt)
            l.setStyleSheet("font-size: 12px; color: #8B949E; font-weight: 500;")
            v = QLabel(val_txt)
            v.setStyleSheet("font-size: 12px; color: #F0F6FC; font-weight: 600;")
            r.addWidget(l)
            r.addStretch()
            r.addWidget(v)
            return r

        card_layout.addLayout(make_row("Toque de Queda Nocturno:", curfew_txt))
        card_layout.addLayout(make_row("Foco de Inicio de sesión:", boot_txt))
        card_layout.addLayout(make_row("Sitios Bloqueados:", f"{len(domains)} dominios"))
        card_layout.addLayout(make_row("Nivel de Redirección:", "0.0.0.0 (Directo)"))

        layout.addWidget(card)

        layout.addStretch()

        # Bottom OK button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("Entendido")
        ok_btn.setObjectName("primaryBtn")
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)


class UnsavedChangesDialog(QDialog):
    """Modern modal asking to save unsaved rule changes before closing."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.action = "cancel"  # 'save', 'discard', 'cancel'
        self.setWindowTitle("Cambios sin guardar")
        self.setFixedWidth(420)
        self.setStyleSheet("""
            QDialog {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 8px;
            }
            QLabel {
                color: #F0F6FC;
            }
            QPushButton {
                border-radius: 6px;
                padding: 7px 14px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton#primaryBtn {
                background-color: #388BFD;
                color: #FFFFFF;
                border: none;
            }
            QPushButton#primaryBtn:hover {
                background-color: #1F6FEB;
            }
            QPushButton#dangerBtn {
                background-color: #21262D;
                color: #F85149;
                border: 1px solid #30363D;
            }
            QPushButton#dangerBtn:hover {
                background-color: #DA3633;
                color: #FFFFFF;
                border-color: #F85149;
            }
            QPushButton#secondaryBtn {
                background-color: #21262D;
                color: #8B949E;
                border: 1px solid #30363D;
            }
            QPushButton#secondaryBtn:hover {
                color: #F0F6FC;
                border-color: #8B949E;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("¿Guardar cambios antes de salir?")
        title.setStyleSheet("font-size: 15px; font-weight: 700; color: #F0F6FC;")
        layout.addWidget(title)

        desc = QLabel("Has modificado horarios o reglas del sistema. Si sales sin guardar, los cambios se descartarán.")
        desc.setStyleSheet("font-size: 12px; color: #8B949E; line-height: 1.4;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.on_cancel)
        btn_row.addWidget(cancel_btn)

        btn_row.addStretch()

        discard_btn = QPushButton("Descartar")
        discard_btn.setObjectName("dangerBtn")
        discard_btn.clicked.connect(self.on_discard)
        btn_row.addWidget(discard_btn)

        save_btn = QPushButton("Guardar y Salir")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self.on_save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def on_save(self):
        self.action = "save"
        self.accept()

    def on_discard(self):
        self.action = "discard"
        self.accept()

    def on_cancel(self):
        self.action = "cancel"
        self.reject()


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
    config_saved = pyqtSignal()

    def __init__(self, ipc_client: FocusIPCClient, resource_dir: str, parent=None):
        super().__init__(parent)
        self.ipc = ipc_client
        self.resource_dir = resource_dir
        self.config_data: Dict[str, Any] = {}
        self.blocked_domains: List[str] = []

        self.setWindowTitle("Panel de Control — Focus-Guard")
        self.setMinimumSize(640, 620)
        self.resize(680, 660)

        self.apply_theme_styles()

        # Tooltip filter for disabled widgets
        self.tooltip_filter = UniversalToolTipFilter(self)
        app_inst = QApplication.instance()
        if app_inst:
            app_inst.installEventFilter(self.tooltip_filter)

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
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self.tabs.setCurrentIndex(0))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self.tabs.setCurrentIndex(1))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self.tabs.setCurrentIndex(2))
        QShortcut(QKeySequence("Ctrl+N"), self, self.focus_domain_input)
        QShortcut(QKeySequence("Ctrl+F"), self, self.focus_search_or_domain_input)

        # Load initial config
        self.load_configuration()
        self.refresh_live_status()

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
            bg_window = "#0D1117"
            bg_card = "#161B22"
            bg_card_inner = "#1C2128"
            bg_input = "#161B22"
            border_color = "#30363D"
            border_subtle = "#21262D"
            text_primary = "#F0F6FC"
            text_secondary = "#8B949E"
            accent_blue = "#388BFD"
            accent_blue_hover = "#1F6FEB"
            tab_bg = "#111419"
        else:
            bg_window = "#F6F8FA"
            bg_card = "#FFFFFF"
            bg_card_inner = "#F3F4F6"
            bg_input = "#FFFFFF"
            border_color = "#D0D7DE"
            border_subtle = "#E1E4E8"
            text_primary = "#1F2328"
            text_secondary = "#656D76"
            accent_blue = "#0969DA"
            accent_blue_hover = "#0550AE"
            tab_bg = "#EAECEF"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_window};
                color: {text_primary};
            }}
            QToolTip {{
                background-color: {bg_card};
                color: {text_primary};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11.5px;
                font-weight: 500;
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
                padding: 4px 8px;
                font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", monospace;
                font-size: 13px;
                font-weight: 700;
                min-height: 24px;
            }}
            QTimeEdit:focus, QSpinBox:focus {{
                border: 1px solid {accent_blue};
            }}
            QTimeEdit::up-button, QTimeEdit::down-button,
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 0px;
                height: 0px;
                border: none;
                background: transparent;
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
            QPushButton#primaryBtn:disabled {{
                background-color: #161B22;
                color: #484F58;
                border: 1px solid #21262D;
            }}
            QPushButton#secondaryBtn {{
                background-color: {bg_card_inner};
                color: {text_primary};
                border: 1px solid {border_color};
            }}
            QPushButton#secondaryBtn:hover {{
                border-color: {accent_blue};
                background-color: {bg_card};
            }}
            QPushButton#secondaryBtn:disabled {{
                background-color: #0D1117;
                color: #484F58;
                border: 1px solid #21262D;
            }}
            QPushButton#stepBtn {{
                background-color: {bg_card_inner};
                color: {text_primary};
                border: 1px solid {border_color};
                border-radius: 6px;
                font-size: 14px;
                font-weight: 700;
                padding: 0px;
                min-width: 28px;
                max-width: 28px;
                min-height: 26px;
                max-height: 26px;
            }}
            QPushButton#stepBtn:hover {{
                background-color: {accent_blue};
                color: #FFFFFF;
                border-color: {accent_blue};
            }}
            QPushButton#presetChipSmall {{
                background-color: {bg_input};
                color: {text_secondary};
                border: 1px solid {border_subtle};
                border-radius: 12px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton#presetChipSmall:hover {{
                border-color: {accent_blue};
                color: {accent_blue};
                background-color: {bg_card_inner};
            }}
            QLabel#summaryPill {{
                font-size: 11.5px;
                color: #58A6FF;
                background-color: rgba(56, 139, 253, 0.08);
                border: 1px solid rgba(56, 139, 253, 0.25);
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
            }}
            QPushButton:disabled {{
                opacity: 0.45;
                color: #6E7681;
                background-color: {bg_card_inner};
                border: 1px solid {border_color};
            }}
            QListWidget {{
                background-color: {bg_card_inner};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 2px;
                outline: none;
            }}
            QListWidget::item {{
                background-color: transparent;
                border: none;
                padding: 0px;
                margin-bottom: 1px;
            }}
            QListWidget::item:focus, QListWidget::item:selected {{
                background-color: transparent;
                border: none;
                outline: none;
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 6px;
                margin: 4px 2px 4px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: #30363D;
                min-height: 24px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #58A6FF;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QCheckBox {{
                color: {text_primary};
                font-size: 13px;
                font-weight: 600;
                spacing: 10px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid {border_color};
                background-color: {bg_input};
            }}
            QCheckBox::indicator:hover {{
                border-color: {accent_blue};
            }}
            QCheckBox::indicator:checked {{
                background-color: {accent_blue};
                border-color: {accent_blue};
                image: url({os.path.join(self.resource_dir, 'checkbox-check.svg')});
            }}
            QCheckBox::indicator:disabled {{
                background-color: {bg_card_inner};
                border-color: {border_subtle};
            }}
            QFrame#settingsCard {{
                background-color: {bg_card_inner};
                border: 1px solid {border_subtle};
                border-radius: 8px;
            }}
            QFrame#heroCard {{
                background-color: {bg_card_inner};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 16px;
            }}
            QFrame#telemetryCard {{
                background-color: {bg_card_inner};
                border: 1px solid {border_subtle};
                border-radius: 8px;
                padding: 12px;
            }}
            QLabel#cardDesc {{
                font-size: 12px;
                color: {text_secondary};
                background: transparent;
                border: none;
                padding: 2px 0px;
            }}
            QLabel#fieldLabel {{
                font-size: 12px;
                font-weight: 500;
                color: {text_primary};
                background: transparent;
                border: none;
                padding: 0px;
            }}
            QProgressBar {{
                background-color: {bg_input};
                border: 1px solid {border_subtle};
                border-radius: 4px;
                height: 8px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: #2EA043;
                border-radius: 3px;
            }}
        """)

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
        title_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #F0F6FC;")
        sub_lbl = QLabel("Panel de Control y Reglas")
        sub_lbl.setStyleSheet("font-size: 12px; color: #8B949E;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header.addLayout(title_box)

        header.addStretch()

        # Status Pill
        self.status_badge = QLabel("VERIFICANDO")
        self.status_badge.setStyleSheet("""
            background-color: rgba(110, 118, 129, 0.15);
            color: #8B949E;
            border: 1px solid #30363D;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 12px;
        """)
        header.addWidget(self.status_badge)

        self.main_layout.addLayout(header)

    def setup_domains_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # 1. Direct Input Row
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("Ingresa un dominio a bloquear (ej: twitter.com o enlace)...")
        self.domain_input.returnPressed.connect(self.on_add_domain_clicked)
        self.domain_input.textChanged.connect(self.on_domain_input_changed)
        top_row.addWidget(self.domain_input)

        add_btn = QPushButton("Añadir")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self.on_add_domain_clicked)
        top_row.addWidget(add_btn)
        layout.addLayout(top_row)

        # Live preview chip
        self.domain_preview_lbl = QLabel("")
        self.domain_preview_lbl.setStyleSheet("font-size: 11px; font-weight: 600; padding-left: 2px;")
        layout.addWidget(self.domain_preview_lbl)

        # 2. Header with counter, search filter and inline auto-save feedback
        count_row = QHBoxLayout()
        count_row.setSpacing(10)
        self.domains_count_lbl = QLabel("Sitios Bloqueados")
        self.domains_count_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #8B949E;")
        count_row.addWidget(self.domains_count_lbl)

        count_row.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtrar sitios...")
        self.search_input.setFixedWidth(140)
        self.search_input.setStyleSheet("padding: 3px 8px; font-size: 11px; border-radius: 4px;")
        self.search_input.textChanged.connect(lambda: self.render_domains_list())
        count_row.addWidget(self.search_input)

        self.domain_auto_feedback_lbl = QLabel("")
        self.domain_auto_feedback_lbl.setStyleSheet("font-size: 11px; color: #2EA043; font-weight: 600;")
        count_row.addWidget(self.domain_auto_feedback_lbl)
        layout.addLayout(count_row)

        # 3. Clean List with Fluid Rows
        self.domains_list = QListWidget()
        self.domains_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.domains_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.domains_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.domains_list)

        self.tabs.addTab(tab, "Sitios Bloqueados")

    def setup_rules_tab(self):
        # Container with Scroll Area to avoid text compression or clipping
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        # 1. Boot Focus Card
        boot_card = QFrame()
        boot_card.setObjectName("settingsCard")
        boot_layout = QVBoxLayout(boot_card)
        boot_layout.setContentsMargins(16, 14, 16, 14)
        boot_layout.setSpacing(10)

        self.boot_enabled_cb = QCheckBox("Foco al Iniciar el Equipo (Boot Focus)")
        self.boot_enabled_cb.setStyleSheet("font-weight: 700; font-size: 13px;")
        boot_layout.addWidget(self.boot_enabled_cb)

        boot_desc = QLabel("Aplica un bloqueo temporal en los sitios distractores durante los primeros minutos tras encender el PC para iniciar tu jornada con concentración.")
        boot_desc.setObjectName("cardDesc")
        boot_desc.setWordWrap(True)
        boot_layout.addWidget(boot_desc)

        dur_row = QHBoxLayout()
        dur_row.setContentsMargins(0, 4, 0, 0)
        dur_row.setSpacing(6)

        dur_label = QLabel("Duración inicial:")
        dur_label.setObjectName("fieldLabel")
        dur_row.addWidget(dur_label)

        step_minus = QPushButton("−")
        step_minus.setObjectName("stepBtn")
        step_minus.setToolTip("Disminuir 5 minutos")
        step_minus.clicked.connect(lambda: self.step_boot_duration(-5))
        dur_row.addWidget(step_minus)

        self.boot_duration_spin = QSpinBox()
        self.boot_duration_spin.setRange(5, 180)
        self.boot_duration_spin.setSingleStep(5)
        self.boot_duration_spin.setSuffix(" min")
        self.boot_duration_spin.setFixedWidth(80)
        self.boot_duration_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dur_row.addWidget(self.boot_duration_spin)

        step_plus = QPushButton("+")
        step_plus.setObjectName("stepBtn")
        step_plus.setToolTip("Aumentar 5 minutos")
        step_plus.clicked.connect(lambda: self.step_boot_duration(5))
        dur_row.addWidget(step_plus)

        dur_row.addSpacing(10)

        for m in [15, 30, 45, 60]:
            pill = QPushButton(f"{m}m")
            pill.setObjectName("presetChipSmall")
            pill.clicked.connect(lambda _, mins=m: self.boot_duration_spin.setValue(mins))
            dur_row.addWidget(pill)

        dur_row.addStretch()
        boot_layout.addLayout(dur_row)
        layout.addWidget(boot_card)

        # 2. Curfew Card
        curfew_card = QFrame()
        curfew_card.setObjectName("settingsCard")
        curfew_layout = QVBoxLayout(curfew_card)
        curfew_layout.setContentsMargins(16, 14, 16, 14)
        curfew_layout.setSpacing(10)

        self.curfew_enabled_cb = QCheckBox("Toque de Queda Nocturno (Night Curfew)")
        self.curfew_enabled_cb.setStyleSheet("font-weight: 700; font-size: 13px;")
        curfew_layout.addWidget(self.curfew_enabled_cb)

        curfew_desc = QLabel("Bloquea automáticamente los sitios distractores durante la noche para proteger las horas de descanso y sueño.")
        curfew_desc.setObjectName("cardDesc")
        curfew_desc.setWordWrap(True)
        curfew_layout.addWidget(curfew_desc)

        time_row = QHBoxLayout()
        time_row.setContentsMargins(0, 4, 0, 0)
        time_row.setSpacing(6)

        start_lbl = QLabel("Bloquear desde:")
        start_lbl.setObjectName("fieldLabel")
        time_row.addWidget(start_lbl)

        start_minus = QPushButton("−")
        start_minus.setObjectName("stepBtn")
        start_minus.setToolTip("Restar 15 minutos")
        start_minus.clicked.connect(lambda: self.step_curfew_start(-15))
        time_row.addWidget(start_minus)

        self.curfew_start_time = QTimeEdit()
        self.curfew_start_time.setDisplayFormat("HH:mm")
        self.curfew_start_time.setFixedWidth(75)
        self.curfew_start_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.curfew_start_time.timeChanged.connect(self.update_curfew_summary)
        time_row.addWidget(self.curfew_start_time)

        start_plus = QPushButton("+")
        start_plus.setObjectName("stepBtn")
        start_plus.setToolTip("Sumar 15 minutos")
        start_plus.clicked.connect(lambda: self.step_curfew_start(15))
        time_row.addWidget(start_plus)

        time_row.addSpacing(14)

        end_lbl = QLabel("Hasta las:")
        end_lbl.setObjectName("fieldLabel")
        time_row.addWidget(end_lbl)

        end_minus = QPushButton("−")
        end_minus.setObjectName("stepBtn")
        end_minus.setToolTip("Restar 15 minutos")
        end_minus.clicked.connect(lambda: self.step_curfew_end(-15))
        time_row.addWidget(end_minus)

        self.curfew_end_time = QTimeEdit()
        self.curfew_end_time.setDisplayFormat("HH:mm")
        self.curfew_end_time.setFixedWidth(75)
        self.curfew_end_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.curfew_end_time.timeChanged.connect(self.update_curfew_summary)
        time_row.addWidget(self.curfew_end_time)

        end_plus = QPushButton("+")
        end_plus.setObjectName("stepBtn")
        end_plus.setToolTip("Sumar 15 minutos")
        end_plus.clicked.connect(lambda: self.step_curfew_end(15))
        time_row.addWidget(end_plus)

        time_row.addStretch()
        curfew_layout.addLayout(time_row)

        # Dynamic human summary pill
        self.curfew_summary_lbl = QLabel("")
        self.curfew_summary_lbl.setObjectName("summaryPill")
        curfew_layout.addWidget(self.curfew_summary_lbl)

        # Quick schedule preset pills
        sched_row = QHBoxLayout()
        sched_row.setSpacing(6)
        sched_lbl = QLabel("Horarios habituales:")
        sched_lbl.setStyleSheet("font-size: 11px; color: #8B949E; font-weight: 500;")
        sched_row.addWidget(sched_lbl)

        curfew_presets = [
            ("23:00 a 07:00", (23, 0), (7, 0)),
            ("23:30 a 07:30", (23, 30), (7, 30)),
            ("00:00 a 08:00", (0, 0), (8, 0)),
            ("01:00 a 07:00", (1, 0), (7, 0))
        ]
        for p_title, p_start, p_end in curfew_presets:
            p_btn = QPushButton(p_title)
            p_btn.setObjectName("presetChipSmall")
            p_btn.clicked.connect(lambda _, s=p_start, e=p_end: self.set_curfew_times(s, e))
            sched_row.addWidget(p_btn)

        sched_row.addStretch()
        curfew_layout.addLayout(sched_row)

        # Informative notice about desktop warning
        curfew_notice = QLabel("Aviso: Recibirás una notificación en tu escritorio 10 minutos antes del Toque de Queda para cerrar tus pestañas con calma.")
        curfew_notice.setStyleSheet("font-size: 11px; color: #58A6FF; font-weight: 500; padding: 2px 0px;")
        curfew_notice.setWordWrap(True)
        curfew_layout.addWidget(curfew_notice)

        layout.addWidget(curfew_card)

        # 3. Configurable Bypasses & Emergency Rules Card
        bypass_card = QFrame()
        bypass_card.setObjectName("settingsCard")
        bypass_layout = QVBoxLayout(bypass_card)
        bypass_layout.setContentsMargins(16, 14, 16, 14)
        bypass_layout.setSpacing(10)

        self.bypasses_enabled_cb = QCheckBox("Permitir pausas temporales (Descansos de 15, 30 o 45 min)")
        self.bypasses_enabled_cb.setStyleSheet("font-weight: 700; font-size: 13px;")
        bypass_layout.addWidget(self.bypasses_enabled_cb)

        byp_desc = QLabel("Permite solicitar pausas de navegación desde el icono de la bandeja durante tus sesiones de trabajo.")
        byp_desc.setObjectName("cardDesc")
        byp_desc.setWordWrap(True)
        bypass_layout.addWidget(byp_desc)

        # Emergency sub-option container
        emerg_container = QWidget()
        emerg_layout = QVBoxLayout(emerg_container)
        emerg_layout.setContentsMargins(20, 0, 0, 0)
        emerg_layout.setSpacing(8)

        self.curfew_emerg_cb = QCheckBox("Permitir desbloqueo de emergencia durante el Toque de Queda")
        self.curfew_emerg_cb.setStyleSheet("font-size: 12px; font-weight: 600;")
        emerg_layout.addWidget(self.curfew_emerg_cb)

        phrase_row = QHBoxLayout()
        phrase_row.setSpacing(8)

        phrase_lbl = QLabel("Frase de confirmación:")
        phrase_lbl.setObjectName("fieldLabel")
        phrase_row.addWidget(phrase_lbl)

        self.emergency_phrase_input = QLineEdit()
        self.emergency_phrase_input.setPlaceholderText("ej: necesito desbloqueo de emergencia")
        phrase_row.addWidget(self.emergency_phrase_input)

        self.copy_phrase_btn = QPushButton("Copiar Frase")
        self.copy_phrase_btn.setObjectName("secondaryBtn")
        self.copy_phrase_btn.setToolTip("Copiar frase al portapapeles")
        self.copy_phrase_btn.clicked.connect(self.on_copy_phrase_clicked)
        phrase_row.addWidget(self.copy_phrase_btn)

        emerg_layout.addLayout(phrase_row)

        bypass_layout.addWidget(emerg_container)
        layout.addWidget(bypass_card)

        # 4. Desktop Tray Applet Autostart Card
        sys_card = QFrame()
        sys_card.setObjectName("settingsCard")
        sys_layout = QVBoxLayout(sys_card)
        sys_layout.setContentsMargins(16, 14, 16, 14)
        sys_layout.setSpacing(6)

        self.autostart_cb = QCheckBox("Iniciar icono en la bandeja del sistema con el escritorio (KDE Plasma)")
        self.autostart_cb.setStyleSheet("font-weight: 700; font-size: 13px;")
        self.autostart_cb.setChecked(is_autostart_enabled())
        self.autostart_cb.toggled.connect(self.on_autostart_toggled)
        sys_layout.addWidget(self.autostart_cb)

        sys_desc = QLabel("Inicia el icono en la bandeja del sistema al entrar a tu sesión de escritorio para consultar el estado y pedir descansos.")
        sys_desc.setObjectName("cardDesc")
        sys_desc.setWordWrap(True)
        sys_layout.addWidget(sys_desc)

        layout.addWidget(sys_card)

        # Dynamic state linkage
        self.boot_enabled_cb.toggled.connect(self.boot_duration_spin.setEnabled)
        self.curfew_enabled_cb.toggled.connect(self.curfew_start_time.setEnabled)
        self.curfew_enabled_cb.toggled.connect(self.curfew_end_time.setEnabled)
        self.curfew_emerg_cb.toggled.connect(self.emergency_phrase_input.setEnabled)

        # Unsaved changes dirty state listeners
        self.boot_enabled_cb.toggled.connect(self.check_for_unsaved_changes)
        self.boot_duration_spin.valueChanged.connect(self.check_for_unsaved_changes)
        self.curfew_enabled_cb.toggled.connect(self.check_for_unsaved_changes)
        self.curfew_start_time.timeChanged.connect(self.check_for_unsaved_changes)
        self.curfew_end_time.timeChanged.connect(self.check_for_unsaved_changes)
        self.bypasses_enabled_cb.toggled.connect(self.check_for_unsaved_changes)
        self.curfew_emerg_cb.toggled.connect(self.check_for_unsaved_changes)
        self.emergency_phrase_input.textChanged.connect(self.check_for_unsaved_changes)

        layout.addStretch()
        scroll.setWidget(container)

        tab_widget = QWidget()
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        self.tabs.addTab(tab_widget, "Horarios y Reglas")

    def setup_dashboard_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Hero Status Card with Progress Bar
        self.hero_card = QFrame()
        self.hero_card.setObjectName("heroCard")
        hero_layout = QVBoxLayout(self.hero_card)
        hero_layout.setSpacing(8)

        top_row = QHBoxLayout()
        self.dash_state_title = QLabel("Estado Actual")
        self.dash_state_title.setStyleSheet("font-size: 15px; font-weight: 700; color: #F0F6FC;")
        top_row.addWidget(self.dash_state_title)
        top_row.addStretch()

        self.dash_state_pill = QLabel("ESTADO")
        self.dash_state_pill.setStyleSheet("font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px; border: 1px solid #30363D;")
        top_row.addWidget(self.dash_state_pill)
        hero_layout.addLayout(top_row)

        self.dash_countdown_lbl = QLabel("Calculando tiempo...")
        self.dash_countdown_lbl.setStyleSheet("""
            font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", "Cascadia Code", "Fira Code", monospace;
            font-size: 22px;
            font-weight: 700;
            color: #2EA043;
            letter-spacing: -0.5px;
        """)
        hero_layout.addWidget(self.dash_countdown_lbl)

        # Visual progress bar
        self.dash_progress_bar = QProgressBar()
        self.dash_progress_bar.setRange(0, 100)
        self.dash_progress_bar.setValue(100)
        self.dash_progress_bar.setTextVisible(False)
        self.dash_progress_bar.setFixedHeight(6)
        hero_layout.addWidget(self.dash_progress_bar)

        self.dash_desc_lbl = QLabel("")
        self.dash_desc_lbl.setStyleSheet("font-size: 12px; color: #8B949E;")
        self.dash_desc_lbl.setWordWrap(True)
        hero_layout.addWidget(self.dash_desc_lbl)

        layout.addWidget(self.hero_card)

        # 2. Quick Focus Sessions Grid (Pomodoro)
        act_box = QVBoxLayout()
        act_box.setSpacing(8)
        
        act_title = QLabel("Sesiones de Enfoque y Control")
        act_title.setStyleSheet("font-size: 13px; font-weight: 700; color: #F0F6FC;")
        act_box.addWidget(act_title)

        grid = QGridLayout()
        grid.setSpacing(8)

        self.btn_pomodoro_25 = QPushButton("Pomodoro (25 min)")
        self.btn_pomodoro_25.setObjectName("secondaryBtn")
        self.btn_pomodoro_25.clicked.connect(lambda: self.start_focus_session(25))
        grid.addWidget(self.btn_pomodoro_25, 0, 0)

        self.btn_pomodoro_50 = QPushButton("Trabajo Profundo (50 min)")
        self.btn_pomodoro_50.setObjectName("secondaryBtn")
        self.btn_pomodoro_50.clicked.connect(lambda: self.start_focus_session(50))
        grid.addWidget(self.btn_pomodoro_50, 0, 1)

        self.btn_primary_action = QPushButton("Bloquear Ahora")
        self.btn_primary_action.setObjectName("primaryBtn")
        self.btn_primary_action.clicked.connect(self.on_primary_action_clicked)
        grid.addWidget(self.btn_primary_action, 1, 0)

        self.btn_secondary_action = QPushButton("Pausa Temporal (15 min)")
        self.btn_secondary_action.setObjectName("secondaryBtn")
        self.btn_secondary_action.clicked.connect(self.on_secondary_action_clicked)
        grid.addWidget(self.btn_secondary_action, 1, 1)

        act_box.addLayout(grid)

        # Stop manual focus button
        self.btn_stop_focus = QPushButton("Finalizar Sesión de Enfoque")
        self.btn_stop_focus.setObjectName("secondaryBtn")
        self.btn_stop_focus.setVisible(False)
        self.btn_stop_focus.clicked.connect(self.on_stop_focus_clicked)
        act_box.addWidget(self.btn_stop_focus)

        layout.addLayout(act_box)

        # 3. Telemetry / Active Rules Summary Card (Fills empty space)
        self.telemetry_card = QFrame()
        self.telemetry_card.setObjectName("telemetryCard")
        telemetry_layout = QVBoxLayout(self.telemetry_card)
        telemetry_layout.setSpacing(6)

        telem_title = QLabel("Resumen de Configuración")
        telem_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #8B949E;")
        telemetry_layout.addWidget(telem_title)

        self.telem_domains_lbl = QLabel("• Sitios protegidos: Calculando...")
        self.telem_domains_lbl.setStyleSheet("font-size: 12px; color: #F0F6FC;")
        telemetry_layout.addWidget(self.telem_domains_lbl)

        self.telem_curfew_lbl = QLabel("• Toque de Queda: 23:15 a 07:00")
        self.telem_curfew_lbl.setStyleSheet("font-size: 12px; color: #F0F6FC;")
        telemetry_layout.addWidget(self.telem_curfew_lbl)

        self.telem_boot_lbl = QLabel("• Cooldown de Inicio: 30 minutos")
        self.telem_boot_lbl.setStyleSheet("font-size: 12px; color: #F0F6FC;")
        telemetry_layout.addWidget(self.telem_boot_lbl)

        layout.addWidget(self.telemetry_card)

        # Action feedback label
        self.dash_feedback_lbl = QLabel("")
        self.dash_feedback_lbl.setStyleSheet("font-size: 11px; color: #2EA043; font-weight: 600;")
        layout.addWidget(self.dash_feedback_lbl)

        layout.addStretch()
        self.tabs.addTab(tab, "Estado y Control")

    def setup_bottom_bar(self):
        bottom = QHBoxLayout()
        bottom.setSpacing(10)

        self.save_feedback_lbl = QLabel("Cambios sincronizados con el demonio")
        self.save_feedback_lbl.setStyleSheet("font-size: 11px; color: #8B949E; font-weight: 500;")
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
            self.curfew_start_time.setEnabled(self.curfew_enabled_cb.isChecked())
            self.curfew_end_time.setEnabled(self.curfew_enabled_cb.isChecked())
            self.update_curfew_summary()

            boot = self.config_data.get("boot_cooldown", {})
            self.boot_enabled_cb.setChecked(boot.get("enabled", True))
            self.boot_duration_spin.setValue(int(boot.get("duration_minutes", 30)))
            self.boot_duration_spin.setEnabled(self.boot_enabled_cb.isChecked())

            bypasses = self.config_data.get("bypasses", {})
            self.bypasses_enabled_cb.setChecked(bypasses.get("enabled", True))
            self.curfew_emerg_cb.setChecked(bypasses.get("allow_during_curfew", False))
            self.emergency_phrase_input.setText(bypasses.get("emergency_phrase", "necesito desbloqueo de emergencia"))
            self.emergency_phrase_input.setEnabled(self.curfew_emerg_cb.isChecked())

            self.check_for_unsaved_changes()
        else:
            self.save_feedback_lbl.setText("Servicio fuera de línea.")

    def step_boot_duration(self, delta: int):
        """Increments or decrements boot focus duration by delta minutes."""
        val = max(5, min(180, self.boot_duration_spin.value() + delta))
        self.boot_duration_spin.setValue(val)

    def step_curfew_start(self, delta_minutes: int):
        """Steps curfew start time by minutes."""
        t = self.curfew_start_time.time().addSecs(delta_minutes * 60)
        self.curfew_start_time.setTime(t)

    def step_curfew_end(self, delta_minutes: int):
        """Steps curfew end time by minutes."""
        t = self.curfew_end_time.time().addSecs(delta_minutes * 60)
        self.curfew_end_time.setTime(t)

    def set_curfew_times(self, start_tuple, end_tuple):
        """Sets curfew start and end from preset."""
        self.curfew_start_time.setTime(QTime(start_tuple[0], start_tuple[1]))
        self.curfew_end_time.setTime(QTime(end_tuple[0], end_tuple[1]))
        self.update_curfew_summary()

    def update_curfew_summary(self):
        """Calculates and displays a human-friendly description of curfew."""
        start = self.curfew_start_time.time()
        end = self.curfew_end_time.time()

        start_12h = start.toString("h:mm AP")
        end_12h = end.toString("h:mm AP")

        start_mins = start.hour() * 60 + start.minute()
        end_mins = end.hour() * 60 + end.minute()

        if end_mins <= start_mins:
            total_mins = (1440 - start_mins) + end_mins
        else:
            total_mins = end_mins - start_mins

        hours = total_mins // 60
        mins = total_mins % 60
        span_str = f"{hours}h {mins}m" if mins > 0 else f"{hours} horas"

        self.curfew_summary_lbl.setText(f"Horario: {start_12h} hasta {end_12h} ({span_str} de descanso)")

    def on_autostart_toggled(self, checked: bool):
        """Manages autostart desktop file."""
        set_autostart_enabled(checked)


    def focus_domain_input(self):
        self.tabs.setCurrentIndex(0)
        self.domain_input.setFocus()
        self.domain_input.selectAll()

    def focus_search_or_domain_input(self):
        self.tabs.setCurrentIndex(0)
        if hasattr(self, "search_input") and self.search_input.isVisible():
            self.search_input.setFocus()
            self.search_input.selectAll()
        else:
            self.domain_input.setFocus()
            self.domain_input.selectAll()

    def on_copy_phrase_clicked(self):
        phrase = self.emergency_phrase_input.text().strip() or "necesito desbloqueo de emergencia"
        QApplication.clipboard().setText(phrase)
        self.copy_phrase_btn.setText("Copiado")
        QTimer.singleShot(2000, lambda: self.copy_phrase_btn.setText("Copiar Frase"))

    def on_stop_focus_clicked(self):
        res = self.ipc.unlock()
        if res.get("status") == "ok":
            self.dash_feedback_lbl.setText("Sesión finalizada")
            self.refresh_live_status()
            QTimer.singleShot(2500, lambda: self.dash_feedback_lbl.setText(""))

    def on_domain_input_changed(self, text: str):
        raw = text.strip()
        if not raw:
            self.domain_preview_lbl.setText("")
            return
        clean = sanitize_domain(raw)
        if clean:
            if clean in self.blocked_domains:
                self.domain_preview_lbl.setStyleSheet("font-size: 11px; color: #D29922; font-weight: 600;")
                self.domain_preview_lbl.setText(f"Dominio ya presente en la lista: {clean}")
            else:
                self.domain_preview_lbl.setStyleSheet("font-size: 11px; color: #58A6FF; font-weight: 600;")
                self.domain_preview_lbl.setText(f"Se bloqueará: {clean}")
        else:
            self.domain_preview_lbl.setStyleSheet("font-size: 11px; color: #F85149; font-weight: 600;")
            self.domain_preview_lbl.setText("Formato de dominio no reconocido (ej: twitter.com)")

    def render_domains_list(self):
        self.domains_list.clear()
        total_cnt = len(self.blocked_domains)
        filter_text = self.search_input.text().strip().lower() if hasattr(self, "search_input") else ""
        filtered_domains = [d for d in self.blocked_domains if (not filter_text or filter_text in d.lower())]

        if filter_text:
            self.domains_count_lbl.setText(f"Sitios ({len(filtered_domains)} de {total_cnt})")
        else:
            self.domains_count_lbl.setText(f"Sitios Bloqueados ({total_cnt})")

        if hasattr(self, "search_input"):
            self.search_input.setVisible(total_cnt > 5)

        is_dark = self.is_dark_mode()
        hover_bg = "rgba(255,255,255,0.04)" if is_dark else "rgba(0,0,0,0.04)"
        sep_color = "#21262D" if is_dark else "#E1E4E8"

        if total_cnt == 0:
            # Modern Minimalist Empty State
            item = QListWidgetItem()
            empty_box = QFrame()
            empty_layout = QVBoxLayout(empty_box)
            empty_layout.setContentsMargins(20, 36, 20, 36)
            empty_layout.setSpacing(6)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            title = QLabel("Sin sitios en la lista")
            title.setStyleSheet("font-size: 13px; font-weight: 700; color: #F0F6FC; background: transparent; border: none;")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(title)

            sub = QLabel("Ingresa dominios arriba (ej: youtube.com) para activar la protección.")
            sub.setStyleSheet("font-size: 11px; color: #8B949E; background: transparent; border: none;")
            sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(sub)

            item.setSizeHint(empty_box.sizeHint())
            self.domains_list.addItem(item)
            self.domains_list.setItemWidget(item, empty_box)
            return

        for domain in sorted(filtered_domains):
            item = QListWidgetItem()
            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{
                    background-color: transparent;
                    border-bottom: 1px solid {sep_color};
                    border-radius: 4px;
                }}
                QFrame:hover {{
                    background-color: {hover_bg};
                }}
            """)

            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 4, 20, 4)
            row_layout.setSpacing(10)

            dot_lbl = QLabel("•")
            dot_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #58A6FF; border: none; background: transparent;")
            row_layout.addWidget(dot_lbl)

            name_lbl = QLabel(domain)
            name_lbl.setStyleSheet("font-weight: 600; font-size: 13px; border: none; background: transparent; color: #F0F6FC;")
            row_layout.addWidget(name_lbl)

            row_layout.addStretch()

            # Elegant minimalist remove button
            del_btn = QPushButton("×")
            del_btn.setToolTip(f"Eliminar {domain}")
            del_btn.setFixedSize(26, 26)
            del_btn.setStyleSheet("""
                QPushButton {
                    border: 1px solid #30363D;
                    background-color: #21262D;
                    color: #8B949E;
                    font-size: 15px;
                    font-weight: 600;
                    border-radius: 4px;
                    padding: 0px;
                }
                QPushButton:hover {
                    color: #FFFFFF;
                    background-color: #DA3633;
                    border-color: #F85149;
                }
            """)
            del_btn.clicked.connect(lambda _, d=domain: self.on_remove_domain(d))
            row_layout.addWidget(del_btn)

            item.setSizeHint(QSize(0, 42))
            self.domains_list.addItem(item)
            self.domains_list.setItemWidget(item, row)

    def on_add_domain_clicked(self):
        raw = self.domain_input.text()
        domain = sanitize_domain(raw)
        if not domain:
            self.domain_auto_feedback_lbl.setStyleSheet("font-size: 11px; color: #F85149; font-weight: 600;")
            self.domain_auto_feedback_lbl.setText("Dominio inválido")
            QTimer.singleShot(2500, lambda: self.domain_auto_feedback_lbl.setText(""))
            return

        if domain in self.blocked_domains:
            self.domain_auto_feedback_lbl.setStyleSheet("font-size: 11px; color: #D29922; font-weight: 600;")
            self.domain_auto_feedback_lbl.setText("Ya está en la lista")
            QTimer.singleShot(2500, lambda: self.domain_auto_feedback_lbl.setText(""))
            return

        self.blocked_domains.append(domain)
        self.domain_input.clear()
        self.render_domains_list()

        # Instant Auto-Save on Add
        self.auto_save_domains(feedback_text=f"'{domain}' añadido y guardado")

    def on_remove_domain(self, domain: str):
        if domain not in self.blocked_domains:
            return

        # Check if active protection is running (Curfew, Boot Cooldown, or Manual Lock)
        status_res = self.ipc.get_status()
        is_blocking = status_res.get("is_blocking", False) if status_res.get("status") == "ok" else False
        reason_msg = status_res.get("message", "Bloqueo activo")

        if is_blocking:
            phrase = self.config_data.get("bypasses", {}).get("emergency_phrase", "necesito desbloqueo de emergencia")
            dlg = ConfirmDomainRemovalDialog(domain=domain, reason_str=reason_msg, phrase=phrase, parent=self)
            dlg.exec()
            if not dlg.confirmed:
                return

        self.blocked_domains.remove(domain)
        self.render_domains_list()
        self.auto_save_domains(feedback_text=f"'{domain}' eliminado")

    def auto_save_domains(self, feedback_text: str = "Guardado"):
        """Silently auto-saves domain modifications to daemon."""
        updated_config = dict(self.config_data)
        updated_config["blocked_domains"] = self.blocked_domains

        res = self.ipc.save_config(updated_config)
        if res.get("status") == "ok":
            self.config_data = updated_config
            self.config_saved.emit()
            self.domain_auto_feedback_lbl.setStyleSheet("font-size: 11px; color: #2EA043; font-weight: 600;")
            self.domain_auto_feedback_lbl.setText(feedback_text)
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
            self.config_data = updated_config
            self.config_saved.emit()
            self.check_for_unsaved_changes()
            self.save_feedback_lbl.setStyleSheet("font-size: 11px; color: #2EA043; font-weight: 600;")
            self.save_feedback_lbl.setText("Reglas guardadas y sincronizadas")
            QTimer.singleShot(3000, lambda: self.check_for_unsaved_changes())
        else:
            self.save_feedback_lbl.setStyleSheet("font-size: 11px; color: #F85149; font-weight: 600;")
            self.save_feedback_lbl.setText(f"Error: {res.get('error', 'No se pudo guardar')}")

    def on_discard_clicked(self):
        """Reverts modified fields to the active loaded configuration."""
        if not hasattr(self, "config_data") or not self.config_data:
            return

        curfew = self.config_data.get("curfew", {})
        self.curfew_enabled_cb.setChecked(curfew.get("enabled", True))
        start_parts = [int(x) for x in curfew.get("start_time", "23:15").split(":")]
        end_parts = [int(x) for x in curfew.get("end_time", "07:00").split(":")]
        self.curfew_start_time.setTime(QTime(start_parts[0], start_parts[1]))
        self.curfew_end_time.setTime(QTime(end_parts[0], end_parts[1]))
        self.curfew_start_time.setEnabled(self.curfew_enabled_cb.isChecked())
        self.curfew_end_time.setEnabled(self.curfew_enabled_cb.isChecked())
        self.update_curfew_summary()

        boot = self.config_data.get("boot_cooldown", {})
        self.boot_enabled_cb.setChecked(boot.get("enabled", True))
        self.boot_duration_spin.setValue(int(boot.get("duration_minutes", 30)))
        self.boot_duration_spin.setEnabled(self.boot_enabled_cb.isChecked())

        bypasses = self.config_data.get("bypasses", {})
        self.bypasses_enabled_cb.setChecked(bypasses.get("enabled", True))
        self.curfew_emerg_cb.setChecked(bypasses.get("allow_during_curfew", False))
        self.emergency_phrase_input.setText(bypasses.get("emergency_phrase", "necesito desbloqueo de emergencia"))
        self.emergency_phrase_input.setEnabled(self.curfew_emerg_cb.isChecked())

        self.check_for_unsaved_changes()
        self.save_feedback_lbl.setText("Cambios descartados")
        self.save_feedback_lbl.setStyleSheet("font-size: 11px; color: #8B949E; font-weight: 500;")
        QTimer.singleShot(2500, lambda: self.check_for_unsaved_changes())

    def has_unsaved_changes(self) -> bool:
        """Dynamically evaluates if form inputs differ from saved config."""
        if not hasattr(self, "config_data") or not self.config_data:
            return False

        curfew = self.config_data.get("curfew", {})
        boot = self.config_data.get("boot_cooldown", {})
        bypasses = self.config_data.get("bypasses", {})

        curfew_changed = (
            self.curfew_enabled_cb.isChecked() != curfew.get("enabled", True) or
            self.curfew_start_time.time().toString("HH:mm") != curfew.get("start_time", "23:15") or
            self.curfew_end_time.time().toString("HH:mm") != curfew.get("end_time", "07:00")
        )

        boot_changed = (
            self.boot_enabled_cb.isChecked() != boot.get("enabled", True) or
            self.boot_duration_spin.value() != int(boot.get("duration_minutes", 30))
        )

        bypasses_changed = (
            self.bypasses_enabled_cb.isChecked() != bypasses.get("enabled", True) or
            self.curfew_emerg_cb.isChecked() != bypasses.get("allow_during_curfew", False) or
            self.emergency_phrase_input.text().strip() != bypasses.get("emergency_phrase", "necesito desbloqueo de emergencia").strip()
        )

        return curfew_changed or boot_changed or bypasses_changed

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
                    font-weight: 700;
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

    def refresh_live_status(self):
        res = self.ipc.get_status()
        if res.get("status") != "ok":
            self.status_badge.setText("● FUERA DE LÍNEA")
            self.status_badge.setStyleSheet("background-color: rgba(110, 118, 129, 0.2); color: #8B949E; font-weight: 700; padding: 4px 10px; border-radius: 12px; border: 1px solid #30363D;")
            icon_off = os.path.join(self.resource_dir, "icon-offline.svg")
            if os.path.exists(icon_off):
                self.header_icon_lbl.setPixmap(QIcon(icon_off).pixmap(28, 28))
            self.dash_state_title.setText("Servicio Fuera de Línea")
            self.dash_countdown_lbl.setText("Inactivo")
            self.dash_desc_lbl.setText("Inicia el servicio focus-guard para habilitar la protección.")
            self.dash_progress_bar.setValue(0)
            self.btn_primary_action.setEnabled(False)
            self.btn_primary_action.setToolTip("El servicio focus-guard está fuera de línea.")
            self.btn_pomodoro_25.setEnabled(False)
            self.btn_pomodoro_25.setToolTip("El servicio focus-guard está fuera de línea.")
            self.btn_pomodoro_50.setEnabled(False)
            self.btn_pomodoro_50.setToolTip("El servicio focus-guard está fuera de línea.")
            self.btn_secondary_action.setEnabled(False)
            self.btn_secondary_action.setToolTip("El servicio focus-guard está fuera de línea.")
            return

        state = res.get("state", "UNLOCKED")
        reason = res.get("reason", "FREE_TIME")
        message = res.get("message", "")
        rem = res.get("remaining_seconds", 0)
        target = res.get("target_time_str", "")
        is_blocking = res.get("is_blocking", False)
        bypasses_enabled = res.get("bypasses_enabled", True)
        domains_cnt = res.get("domains_count", len(self.blocked_domains))

        human_time = format_human_time(rem)

        # Update Telemetry Widget
        self.telem_domains_lbl.setText(f"• Sitios protegidos: {domains_cnt} dominios")
        curfew = self.config_data.get("curfew", {})
        curfew_str = f"{curfew.get('start_time', '23:15')} a {curfew.get('end_time', '07:00')}" if curfew.get('enabled') else "Desactivado"
        self.telem_curfew_lbl.setText(f"• Toque de Queda: {curfew_str}")
        boot = self.config_data.get("boot_cooldown", {})
        boot_str = f"{boot.get('duration_minutes', 30)}m (Activo)" if (reason == "BOOT_COOLDOWN") else (f"{boot.get('duration_minutes', 30)}m" if boot.get('enabled') else "Desactivado")
        self.telem_boot_lbl.setText(f"• Cooldown de Inicio: {boot_str}")

        # 1. State: UNLOCKED / FREE TIME (Emerald Green)
        if state == "UNLOCKED":
            self.status_badge.setText("MODO LIBRE")
            self.status_badge.setStyleSheet("background-color: rgba(46, 160, 67, 0.15); color: #3FB950; font-weight: 700; padding: 4px 10px; border-radius: 12px; border: 1px solid rgba(46, 160, 67, 0.3);")
            icon_idle = os.path.join(self.resource_dir, "icon-idle.svg")
            if os.path.exists(icon_idle):
                self.header_icon_lbl.setPixmap(QIcon(icon_idle).pixmap(28, 28))
            self.dash_state_pill.setText("MODO LIBRE")
            self.dash_state_pill.setStyleSheet("border: 1px solid #2EA043; color: #3FB950; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px; background-color: rgba(46, 160, 67, 0.12);")
            self.dash_state_title.setText("Modo Libre (Navegación Abierta)")
            self.dash_countdown_lbl.setText("Sitios Desbloqueados")
            self.dash_countdown_lbl.setStyleSheet("font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; font-size: 20px; font-weight: 700; color: #3FB950;")
            self.dash_desc_lbl.setText("El bloqueo no está activo. Puedes iniciar una sesión de enfoque cuando gustes.")
            self.dash_progress_bar.setValue(0)
            self.dash_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #2EA043; }")
            self.btn_stop_focus.setVisible(False)

            self.btn_primary_action.setText("Bloquear Ahora")
            self.btn_primary_action.setEnabled(True)
            self.btn_primary_action.setToolTip("Activar bloqueo manual de sitios distractores.")
            self.btn_pomodoro_25.setEnabled(True)
            self.btn_pomodoro_25.setToolTip("Iniciar sesión de concentración de 25 minutos.")
            self.btn_pomodoro_50.setEnabled(True)
            self.btn_pomodoro_50.setToolTip("Iniciar sesión de trabajo profundo de 50 minutos.")
            self.btn_secondary_action.setText("Pausa Temporal (15 min)")
            self.btn_secondary_action.setEnabled(False)
            self.btn_secondary_action.setToolTip("Las pausas temporales solo están disponibles cuando hay un bloqueo activo.")

        # 2. State: BYPASS / BREAK (Amber Gold)
        elif state == "BYPASS":
            self.status_badge.setText("EN DESCANSO")
            self.status_badge.setStyleSheet("background-color: rgba(210, 153, 34, 0.15); color: #E3B341; font-weight: 700; padding: 4px 10px; border-radius: 12px; border: 1px solid rgba(210, 153, 34, 0.3);")
            icon_byp = os.path.join(self.resource_dir, "icon-bypass.svg")
            if os.path.exists(icon_byp):
                self.header_icon_lbl.setPixmap(QIcon(icon_byp).pixmap(28, 28))
            self.dash_state_pill.setText("PAUSA TEMPORAL")
            self.dash_state_pill.setStyleSheet("border: 1px solid #D29922; color: #E3B341; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px; background-color: rgba(210, 153, 34, 0.12);")
            self.dash_state_title.setText("Pausa Temporal Activa")
            self.dash_countdown_lbl.setText(f"{human_time}")
            self.dash_countdown_lbl.setStyleSheet("font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; font-size: 22px; font-weight: 700; color: #E3B341;")
            self.dash_desc_lbl.setText("Acceso concedido temporalmente. Los sitios se bloquearán al finalizar.")
            self.dash_progress_bar.setValue(max(5, min(100, int((rem / 900) * 100))))
            self.dash_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #D29922; }")
            self.btn_stop_focus.setVisible(False)

            self.btn_primary_action.setText("Terminar Descanso")
            self.btn_primary_action.setEnabled(True)
            self.btn_primary_action.setToolTip("Finalizar la pausa y reactivar el bloqueo inmediatamente.")
            self.btn_pomodoro_25.setEnabled(False)
            self.btn_pomodoro_25.setToolTip("No disponible durante una pausa temporal.")
            self.btn_pomodoro_50.setEnabled(False)
            self.btn_pomodoro_50.setToolTip("No disponible durante una pausa temporal.")
            self.btn_secondary_action.setText("Pausa en Curso")
            self.btn_secondary_action.setEnabled(False)
            self.btn_secondary_action.setToolTip("La pausa temporal ya está activa.")

        # 3. State: LOCKED / ACTIVE PROTECTION
        elif is_blocking:
            if reason == "CURFEW":
                self.status_badge.setText("TOQUE DE QUEDA")
                self.status_badge.setStyleSheet("background-color: rgba(137, 87, 229, 0.15); color: #D2A8FF; font-weight: 700; padding: 4px 10px; border-radius: 12px; border: 1px solid rgba(137, 87, 229, 0.3);")
                icon_curf = os.path.join(self.resource_dir, "icon-curfew.svg")
                if os.path.exists(icon_curf):
                    self.header_icon_lbl.setPixmap(QIcon(icon_curf).pixmap(28, 28))
                self.dash_state_pill.setText("NOCHE PROTEGIDA")
                self.dash_state_pill.setStyleSheet("border: 1px solid #8957E5; color: #D2A8FF; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px; background-color: rgba(137, 87, 229, 0.12);")
                self.dash_state_title.setText("Toque de Queda Nocturno")
                self.dash_desc_lbl.setText(f"Protección nocturna activa hasta las {target}.")
                self.dash_countdown_lbl.setStyleSheet("font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; font-size: 22px; font-weight: 700; color: #D2A8FF;")
                self.dash_progress_bar.setValue(100)
                self.dash_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #8957E5; }")
                self.btn_stop_focus.setVisible(False)

                self.btn_primary_action.setText("Bloqueo Nocturno")
                self.btn_primary_action.setEnabled(False)
                self.btn_primary_action.setToolTip("El Toque de Queda está activo y protege tus horas de descanso.")
                self.btn_pomodoro_25.setEnabled(False)
                self.btn_pomodoro_25.setToolTip("Las sesiones de enfoque no se pueden iniciar durante el Toque de Queda.")
                self.btn_pomodoro_50.setEnabled(False)
                self.btn_pomodoro_50.setToolTip("Las sesiones de enfoque no se pueden iniciar durante el Toque de Queda.")

                if self.curfew_emerg_cb.isChecked():
                    self.btn_secondary_action.setText("Desbloqueo de Emergencia")
                    self.btn_secondary_action.setEnabled(True)
                    self.btn_secondary_action.setToolTip("Solicitar 15 minutos de emergencia mediante frase de seguridad.")
                else:
                    self.btn_secondary_action.setText("Descanso Desactivado")
                    self.btn_secondary_action.setEnabled(False)
                    self.btn_secondary_action.setToolTip("Los descansos nocturnos están deshabilitados. Puedes habilitar la opción de emergencia en Horarios y Reglas.")

            elif reason == "BOOT_COOLDOWN":
                self.status_badge.setText("FOCO DE INICIO")
                self.status_badge.setStyleSheet("background-color: rgba(56, 139, 253, 0.15); color: #58A6FF; font-weight: 700; padding: 4px 10px; border-radius: 12px; border: 1px solid rgba(56, 139, 253, 0.3);")
                icon_bt = os.path.join(self.resource_dir, "icon-boot.svg")
                if os.path.exists(icon_bt):
                    self.header_icon_lbl.setPixmap(QIcon(icon_bt).pixmap(28, 28))
                self.dash_state_pill.setText("BOOT FOCUS")
                self.dash_state_pill.setStyleSheet("border: 1px solid #388BFD; color: #58A6FF; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px; background-color: rgba(56, 139, 253, 0.12);")
                self.dash_state_title.setText("Cooldown de Arranque")
                self.dash_desc_lbl.setText(f"Protección de inicio activa hasta las {target}.")
                self.dash_countdown_lbl.setStyleSheet("font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; font-size: 22px; font-weight: 700; color: #58A6FF;")
                total_boot = max(1, self.config_data.get("boot_cooldown", {}).get("duration_minutes", 30) * 60)
                self.dash_progress_bar.setValue(max(5, min(100, int((rem / total_boot) * 100))))
                self.dash_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #388BFD; }")
                self.btn_stop_focus.setVisible(False)

                self.btn_primary_action.setText("Inicio Activo")
                self.btn_primary_action.setEnabled(False)
                self.btn_primary_action.setToolTip("La protección de inicio de sesión está activa.")
                self.btn_pomodoro_25.setEnabled(False)
                self.btn_pomodoro_25.setToolTip("El equipo se encuentra en período de foco de arranque.")
                self.btn_pomodoro_50.setEnabled(False)
                self.btn_pomodoro_50.setToolTip("El equipo se encuentra en período de foco de arranque.")

                if bypasses_enabled:
                    self.btn_secondary_action.setText("Pausa Temporal (15 min)")
                    self.btn_secondary_action.setEnabled(True)
                    self.btn_secondary_action.setToolTip("Solicitar 15 minutos de descanso temporal.")
                else:
                    self.btn_secondary_action.setText("Descanso Desactivado")
                    self.btn_secondary_action.setEnabled(False)
                    self.btn_secondary_action.setToolTip("Las pausas temporales están desactivadas en la configuración.")

            elif reason == "MANUAL_LOCK":
                self.status_badge.setText("ENFOQUE ACTIVO")
                self.status_badge.setStyleSheet("background-color: rgba(56, 139, 253, 0.15); color: #58A6FF; font-weight: 700; padding: 4px 10px; border-radius: 12px; border: 1px solid rgba(56, 139, 253, 0.3);")
                icon_act = os.path.join(self.resource_dir, "icon-active.svg")
                if os.path.exists(icon_act):
                    self.header_icon_lbl.setPixmap(QIcon(icon_act).pixmap(28, 28))
                self.dash_state_pill.setText("ENFOQUE MANUAL")
                self.dash_state_pill.setStyleSheet("border: 1px solid #388BFD; color: #58A6FF; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px; background-color: rgba(56, 139, 253, 0.12);")
                self.dash_state_title.setText("Modo Focus / Pomodoro")
                self.dash_desc_lbl.setText("Sesión de concentración manual en curso.")
                self.dash_countdown_lbl.setStyleSheet("font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; font-size: 22px; font-weight: 700; color: #58A6FF;")
                self.dash_progress_bar.setValue(100)
                self.dash_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #388BFD; }")
                self.btn_stop_focus.setVisible(True)
                self.btn_stop_focus.setToolTip("Finalizar la sesión de enfoque actual y desbloquear los sitios.")

                self.btn_primary_action.setText("Enfoque en Curso")
                self.btn_primary_action.setEnabled(False)
                self.btn_primary_action.setToolTip("Ya hay una sesión de concentración manual en curso.")
                self.btn_pomodoro_25.setEnabled(False)
                self.btn_pomodoro_25.setToolTip("Ya hay una sesión de concentración activa.")
                self.btn_pomodoro_50.setEnabled(False)
                self.btn_pomodoro_50.setToolTip("Ya hay una sesión de concentración activa.")

                if bypasses_enabled:
                    self.btn_secondary_action.setText("Pausa Temporal (15 min)")
                    self.btn_secondary_action.setEnabled(True)
                    self.btn_secondary_action.setToolTip("Solicitar 15 minutos de pausa temporal.")
                else:
                    self.btn_secondary_action.setText("Descanso Desactivado")
                    self.btn_secondary_action.setEnabled(False)
                    self.btn_secondary_action.setToolTip("Las pausas temporales están desactivadas en la configuración.")

            if rem > 0:
                self.dash_countdown_lbl.setText(f"{human_time}")
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
