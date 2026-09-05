"""
Focus-Guard Settings & Dashboard Dialog.
Unified KDE Plasma 6 / Wayland HIG Design System.
Features: Auto-save, Category presets, Slim scrollbars, Pomodoro grid, Telemetry widgets, and Custom About Modal.
"""
import os
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional, Set

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QTabWidget, QWidget, QCheckBox,
    QTimeEdit, QSpinBox, QFrame, QProgressBar, QGridLayout, QApplication,
    QScrollArea, QAbstractItemView, QToolTip
)
from PyQt6.QtGui import QIcon, QPalette, QKeySequence, QShortcut
from PyQt6.QtCore import Qt, QTime, QTimer, pyqtSignal, QSize, QObject, QEvent

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
    config_saved = pyqtSignal()

    def __init__(self, ipc_client: FocusIPCClient, resource_dir: str, parent=None):
        super().__init__(parent)
        self.ipc = ipc_client
        self.resource_dir = resource_dir
        self.config_data: Dict[str, Any] = {}
        self.blocked_domains: List[str] = []
        self.selected_selective_domains: Set[str] = set()
        self.domain_tile_widgets: Dict[str, Any] = {}

        self.setWindowTitle("Panel de Control — Focus-Guard")
        self.setMinimumSize(720, 640)
        self.resize(760, 680)

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
        self.setup_selective_tab()
        self.setup_rules_tab()
        self.setup_dashboard_tab()
        self.tabs.currentChanged.connect(self.on_tab_changed)
        self.main_layout.addWidget(self.tabs)

        # 3. Bottom Bar
        self.setup_bottom_bar()

        # 4. Keyboard Shortcuts
        QShortcut(QKeySequence("Ctrl+S"), self, self.on_save_clicked)
        QShortcut(QKeySequence("Escape"), self, self.close)
        QShortcut(QKeySequence("Ctrl+1"), self, lambda: self.tabs.setCurrentIndex(0))
        QShortcut(QKeySequence("Ctrl+2"), self, lambda: self.tabs.setCurrentIndex(1))
        QShortcut(QKeySequence("Ctrl+3"), self, lambda: self.tabs.setCurrentIndex(2))
        QShortcut(QKeySequence("Ctrl+4"), self, lambda: self.tabs.setCurrentIndex(3))
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

        # Status Pill
        self.status_badge = QLabel("VERIFICANDO")
        self.status_badge.setObjectName("statusBadge")
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
        self.domains_count_lbl.setObjectName("fieldLabel")
        count_row.addWidget(self.domains_count_lbl)

        count_row.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtrar sitios...")
        self.search_input.setFixedWidth(140)
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

    def setup_selective_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        # 1. Header Banner
        header_frame = QFrame()
        header_frame.setObjectName("settingsCard")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(12)

        hdr_info = QVBoxLayout()
        hdr_info.setSpacing(2)
        hdr_title = QLabel("Bloqueo Selectivo")
        hdr_title.setObjectName("sectionHeader")
        hdr_sub = QLabel("Aislamiento temporal de distracciones bajo demanda.")
        hdr_sub.setObjectName("cardDesc")
        hdr_info.addWidget(hdr_title)
        hdr_info.addWidget(hdr_sub)
        header_layout.addLayout(hdr_info)
        header_layout.addStretch()

        self.sel_status_badge = QLabel("EN ESPERA")
        self.sel_status_badge.setObjectName("statusBadge")
        header_layout.addWidget(self.sel_status_badge)
        main_layout.addWidget(header_frame)

        # 2. Active Session Hero Card (Visible only when selective lock is running)
        self.sel_active_card = QFrame()
        self.sel_active_card.setObjectName("heroCard")
        active_layout = QVBoxLayout(self.sel_active_card)
        active_layout.setSpacing(10)

        act_top_row = QHBoxLayout()
        act_pill = QLabel("SESIÓN ACTIVA")
        act_pill.setStyleSheet("background-color: rgba(56, 139, 253, 0.15); color: #58A6FF; font-weight: 700; font-size: 10px; padding: 3px 8px; border-radius: 12px; border: 1px solid rgba(56, 139, 253, 0.3);")
        act_top_row.addWidget(act_pill)
        act_top_row.addStretch()

        self.sel_active_countdown_lbl = QLabel("Calculando...")
        self.sel_active_countdown_lbl.setStyleSheet("font-family: ui-monospace, SFMono-Regular, monospace; font-size: 18px; font-weight: 700; color: #58A6FF;")
        act_top_row.addWidget(self.sel_active_countdown_lbl)
        active_layout.addLayout(act_top_row)

        self.sel_active_domains_lbl = QLabel("")
        self.sel_active_domains_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #F0F6FC;" if self.is_dark_mode() else "font-size: 12px; font-weight: 600; color: #1F2328;")
        self.sel_active_domains_lbl.setWordWrap(True)
        active_layout.addWidget(self.sel_active_domains_lbl)

        act_bottom_row = QHBoxLayout()
        self.sel_active_end_lbl = QLabel("")
        self.sel_active_end_lbl.setStyleSheet("font-size: 11px; color: #8B949E;")
        act_bottom_row.addWidget(self.sel_active_end_lbl)
        act_bottom_row.addStretch()

        self.sel_cancel_btn = QPushButton("Finalizar Bloqueo")
        self.sel_cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sel_cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262D;
                color: #F85149;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 600;
                font-size: 11.5px;
            }
            QPushButton:hover {
                background-color: #DA3633;
                color: #FFFFFF;
                border-color: #F85149;
            }
        """)
        self.sel_cancel_btn.clicked.connect(self.on_cancel_selective_clicked)
        act_bottom_row.addWidget(self.sel_cancel_btn)
        active_layout.addLayout(act_bottom_row)

        self.sel_active_card.setVisible(False)
        main_layout.addWidget(self.sel_active_card)

        # 3. Two-Column Split Layout
        split_layout = QHBoxLayout()
        split_layout.setSpacing(12)

        # LEFT COLUMN (55%): Minimalist Domain Picker & On-the-fly Adder
        sites_card = QFrame()
        sites_card.setObjectName("settingsCard")
        sites_layout = QVBoxLayout(sites_card)
        sites_layout.setContentsMargins(16, 14, 16, 14)
        sites_layout.setSpacing(10)

        col_top = QHBoxLayout()
        col_title = QLabel("1. Selección de Sitios")
        col_title.setObjectName("sectionHeader")
        col_top.addWidget(col_title)
        col_top.addStretch()

        self.sel_count_lbl = QLabel("0 seleccionados")
        self.sel_count_lbl.setObjectName("statusBadge")
        col_top.addWidget(self.sel_count_lbl)
        sites_layout.addLayout(col_top)

        # Quick Add Site Row directly in this tab
        add_row = QHBoxLayout()
        add_row.setSpacing(6)

        self.sel_add_input = QLineEdit()
        self.sel_add_input.setPlaceholderText("Añadir sitio y seleccionar (ej: instagram.com)...")
        self.sel_add_input.returnPressed.connect(self.on_sel_add_domain_clicked)
        add_row.addWidget(self.sel_add_input)

        sel_add_btn = QPushButton("Añadir")
        sel_add_btn.setObjectName("primaryBtn")
        sel_add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sel_add_btn.clicked.connect(self.on_sel_add_domain_clicked)
        add_row.addWidget(sel_add_btn)
        sites_layout.addLayout(add_row)

        self.sel_add_feedback_lbl = QLabel("")
        self.sel_add_feedback_lbl.setStyleSheet("font-size: 11px; font-weight: 600;")
        sites_layout.addWidget(self.sel_add_feedback_lbl)

        # Search filter, bulk actions, and refresh button
        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(6)

        self.sel_search_input = QLineEdit()
        self.sel_search_input.setPlaceholderText("Filtrar sitios...")
        self.sel_search_input.setFixedWidth(140)
        self.sel_search_input.textChanged.connect(lambda: self.render_selective_domains_list())
        toolbar_row.addWidget(self.sel_search_input)

        sel_all_btn = QPushButton("Todos")
        sel_all_btn.setObjectName("presetChipSmall")
        sel_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sel_all_btn.clicked.connect(self.on_select_all_selective)
        toolbar_row.addWidget(sel_all_btn)

        desel_all_btn = QPushButton("Ninguno")
        desel_all_btn.setObjectName("presetChipSmall")
        desel_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        desel_all_btn.clicked.connect(self.on_deselect_all_selective)
        toolbar_row.addWidget(desel_all_btn)

        refresh_btn = QPushButton("Actualizar")
        refresh_btn.setObjectName("presetChipSmall")
        refresh_btn.setToolTip("Recargar lista desde la configuración activa")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.on_refresh_selective_list)
        toolbar_row.addWidget(refresh_btn)
        sites_layout.addLayout(toolbar_row)

        self.sel_domains_list = QListWidget()
        self.sel_domains_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.sel_domains_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.sel_domains_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sel_domains_list.setMinimumHeight(280)
        sites_layout.addWidget(self.sel_domains_list)

        split_layout.addWidget(sites_card, stretch=55)

        # RIGHT COLUMN (45%): Duration & Launch Action
        ctrl_card = QFrame()
        ctrl_card.setObjectName("settingsCard")
        ctrl_layout = QVBoxLayout(ctrl_card)
        ctrl_layout.setContentsMargins(16, 14, 16, 14)
        ctrl_layout.setSpacing(12)

        ctrl_title = QLabel("2. Duración del Bloqueo")
        ctrl_title.setObjectName("sectionHeader")
        ctrl_layout.addWidget(ctrl_title)

        ctrl_desc = QLabel("Define el tiempo durante el cual permanecerán bloqueados los sitios marcados.")
        ctrl_desc.setObjectName("cardDesc")
        ctrl_desc.setWordWrap(True)
        ctrl_layout.addWidget(ctrl_desc)

        # Duration Selector Box
        dur_box = QFrame()
        dur_box.setObjectName("innerCard")
        dur_box_layout = QVBoxLayout(dur_box)
        dur_box_layout.setSpacing(8)

        dur_box_title = QLabel("Tiempo a bloquear:")
        dur_box_title.setObjectName("fieldLabel")
        dur_box_layout.addWidget(dur_box_title)

        stepper_row = QHBoxLayout()
        stepper_row.setSpacing(6)

        step_minus = QPushButton("−")
        step_minus.setObjectName("stepBtn")
        step_minus.setToolTip("Disminuir 5 minutos")
        step_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        step_minus.clicked.connect(lambda: self.step_selective_duration(-5))
        stepper_row.addWidget(step_minus)

        self.sel_duration_spin = QSpinBox()
        self.sel_duration_spin.setRange(1, 1440)
        self.sel_duration_spin.setSingleStep(5)
        self.sel_duration_spin.setValue(25)
        self.sel_duration_spin.setSuffix(" min")
        self.sel_duration_spin.setFixedWidth(80)
        self.sel_duration_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sel_duration_spin.valueChanged.connect(self.update_selective_summary)
        stepper_row.addWidget(self.sel_duration_spin)

        step_plus = QPushButton("+")
        step_plus.setObjectName("stepBtn")
        step_plus.setToolTip("Aumentar 5 minutos")
        step_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        step_plus.clicked.connect(lambda: self.step_selective_duration(5))
        stepper_row.addWidget(step_plus)

        stepper_row.addSpacing(10)

        for m in [15, 25, 45, 60]:
            pill = QPushButton(f"{m}m")
            pill.setObjectName("presetChipSmall")
            pill.setToolTip(f"Fijar duración a {m} minutos")
            pill.setCursor(Qt.CursorShape.PointingHandCursor)
            pill.clicked.connect(lambda _, mins=m: self.sel_duration_spin.setValue(mins))
            stepper_row.addWidget(pill)

        stepper_row.addStretch()
        dur_box_layout.addLayout(stepper_row)
        ctrl_layout.addWidget(dur_box)

        # Session Forecast Card
        self.sel_summary_card = QFrame()
        self.sel_summary_card.setObjectName("previewCard")
        sum_layout = QVBoxLayout(self.sel_summary_card)
        sum_layout.setContentsMargins(10, 8, 10, 8)
        sum_layout.setSpacing(4)

        self.sel_summary_title = QLabel("Parámetros de Sesión")
        self.sel_summary_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #58A6FF;")
        sum_layout.addWidget(self.sel_summary_title)

        self.sel_summary_lbl = QLabel("")
        self.sel_summary_lbl.setObjectName("cardDesc")
        self.sel_summary_lbl.setWordWrap(True)
        sum_layout.addWidget(self.sel_summary_lbl)

        ctrl_layout.addWidget(self.sel_summary_card)
        ctrl_layout.addStretch()

        # Action Button
        self.sel_start_btn = QPushButton("Iniciar Bloqueo (25 min)")
        self.sel_start_btn.setObjectName("primaryBtn")
        self.sel_start_btn.setMinimumHeight(40)
        self.sel_start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sel_start_btn.clicked.connect(self.on_start_selective_lock)
        ctrl_layout.addWidget(self.sel_start_btn)

        self.sel_feedback_lbl = QLabel("")
        self.sel_feedback_lbl.setStyleSheet("font-size: 11px; font-weight: 600;")
        self.sel_feedback_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl_layout.addWidget(self.sel_feedback_lbl)

        split_layout.addWidget(ctrl_card, stretch=45)

        main_layout.addLayout(split_layout)
        scroll.setWidget(container)

        tab_widget = QWidget()
        tab_layout = QVBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        self.tabs.addTab(tab_widget, "Bloqueo Selectivo")


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
        self.dash_state_title.setObjectName("sectionHeader")
        top_row.addWidget(self.dash_state_title)
        top_row.addStretch()

        self.dash_state_pill = QLabel("ESTADO")
        self.dash_state_pill.setObjectName("statusBadge")
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
        self.dash_desc_lbl.setObjectName("cardDesc")
        self.dash_desc_lbl.setWordWrap(True)
        hero_layout.addWidget(self.dash_desc_lbl)

        layout.addWidget(self.hero_card)

        # 2. Quick Focus Sessions Grid (Pomodoro)
        act_box = QVBoxLayout()
        act_box.setSpacing(8)
        
        act_title = QLabel("Sesiones de Enfoque y Control")
        act_title.setObjectName("sectionHeader")
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
        telem_title.setObjectName("sectionHeader")
        telemetry_layout.addWidget(telem_title)

        self.telem_domains_lbl = QLabel("• Sitios protegidos: Calculando...")
        self.telem_domains_lbl.setObjectName("fieldLabel")
        telemetry_layout.addWidget(self.telem_domains_lbl)

        self.telem_curfew_lbl = QLabel("• Toque de Queda: 23:15 a 07:00")
        self.telem_curfew_lbl.setObjectName("fieldLabel")
        telemetry_layout.addWidget(self.telem_curfew_lbl)

        self.telem_boot_lbl = QLabel("• Cooldown de Inicio: 30 minutos")
        self.telem_boot_lbl.setObjectName("fieldLabel")
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
        res_status = self.ipc.get_status()
        if res_status.get("is_selective"):
            res = self.ipc.cancel_selective_lock()
        else:
            res = self.ipc.unlock_now()
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
        hover_bg = "#161B22" if is_dark else "#F6F8FA"
        sep_color = "#21262D" if is_dark else "#E1E4E8"

        if total_cnt == 0:
            item = QListWidgetItem()
            empty_box = QFrame()
            empty_layout = QVBoxLayout(empty_box)
            empty_layout.setContentsMargins(20, 36, 20, 36)
            empty_layout.setSpacing(6)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            title = QLabel("Sin sitios en la lista")
            title.setStyleSheet("font-size: 12px; font-weight: 700; color: #F0F6FC; background: transparent; border: none;" if is_dark else "font-size: 12px; font-weight: 700; color: #1F2328; background: transparent; border: none;")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(title)

            sub = QLabel("Ingresa dominios arriba (ej: youtube.com) para activar la protección.")
            sub.setStyleSheet("font-size: 11.5px; color: #8B949E; background: transparent; border: none;")
            sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(sub)

            item.setSizeHint(empty_box.sizeHint())
            self.domains_list.addItem(item)
            self.domains_list.setItemWidget(item, empty_box)
            if hasattr(self, "sel_domains_list"):
                self.render_selective_domains_list()
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
            name_lbl.setStyleSheet(f"font-weight: 600; font-size: 13px; border: none; background: transparent; color: {'#F0F6FC' if is_dark else '#1F2328'};")
            row_layout.addWidget(name_lbl)

            row_layout.addStretch()

            # Elegant minimalist remove button
            del_btn = QPushButton("×")
            del_btn.setToolTip(f"Eliminar {domain}")
            del_btn.setObjectName("removeBtn")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda _, d=domain: self.on_remove_domain(d))
            row_layout.addWidget(del_btn)

            item.setSizeHint(QSize(0, 42))
            self.domains_list.addItem(item)
            self.domains_list.setItemWidget(item, row)

        if hasattr(self, "sel_domains_list"):
            self.render_selective_domains_list()

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
            if hasattr(self, "domain_auto_feedback_lbl"):
                self.domain_auto_feedback_lbl.setStyleSheet("font-size: 11px; color: #2EA043; font-weight: 600;")
                self.domain_auto_feedback_lbl.setText(feedback_text)
                QTimer.singleShot(2500, lambda: self.domain_auto_feedback_lbl.setText(""))
            self.render_selective_domains_list()

    def render_selective_domains_list(self):
        """Populates the selective blocking domains list with minimalist tiles."""
        if not hasattr(self, "sel_domains_list"):
            return

        self.sel_domains_list.clear()
        self.domain_tile_widgets = {}

        # Clean up any selected domains that might have been deleted from blocked_domains
        current_set = set(self.blocked_domains)
        self.selected_selective_domains = self.selected_selective_domains.intersection(current_set)

        search_query = self.sel_search_input.text().strip().lower() if hasattr(self, "sel_search_input") else ""
        filtered = [d for d in self.blocked_domains if (not search_query or search_query in d.lower())]

        is_dark = self.is_dark_mode()
        text_color = "#F0F6FC" if is_dark else "#1F2328"

        if not self.blocked_domains:
            empty_item = QListWidgetItem()
            empty_box = QWidget()
            empty_layout = QVBoxLayout(empty_box)
            empty_layout.setContentsMargins(20, 30, 20, 30)
            empty_layout.setSpacing(6)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            title = QLabel("Sin sitios configurados")
            title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {text_color}; background: transparent; border: none;")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(title)

            sub = QLabel("Añade dominios en 'Sitios Bloqueados' para gestionarlos aquí.")
            sub.setStyleSheet("font-size: 11.5px; color: #8B949E; background: transparent; border: none;")
            sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(sub)

            empty_item.setSizeHint(empty_box.sizeHint())
            self.sel_domains_list.addItem(empty_item)
            self.sel_domains_list.setItemWidget(empty_item, empty_box)
            self.update_selective_summary()
            return

        if not filtered and search_query:
            empty_item = QListWidgetItem()
            empty_lbl = QLabel("Sin coincidencias")
            empty_lbl.setStyleSheet("font-size: 11.5px; color: #8B949E; padding: 16px; background: transparent;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_item.setSizeHint(QSize(0, 42))
            self.sel_domains_list.addItem(empty_item)
            self.sel_domains_list.setItemWidget(empty_item, empty_lbl)
            self.update_selective_summary()
            return

        for domain in sorted(filtered):
            item = QListWidgetItem()
            is_checked = domain in self.selected_selective_domains

            row = QFrame()
            row.setCursor(Qt.CursorShape.PointingHandCursor)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 6, 12, 6)
            row_layout.setSpacing(10)

            # Left: bullet indicator
            dot_lbl = QLabel("•")
            dot_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #58A6FF; border: none; background: transparent;")
            row_layout.addWidget(dot_lbl)

            # Center: Domain info
            info_layout = QVBoxLayout()
            info_layout.setSpacing(1)
            name_lbl = QLabel(domain)
            name_lbl.setStyleSheet(f"font-weight: 600; font-size: 12.5px; color: {text_color}; background: transparent; border: none;")
            info_layout.addWidget(name_lbl)

            sub_lbl = QLabel("Regla individual")
            sub_lbl.setStyleSheet("font-size: 10px; color: #8B949E; background: transparent; border: none;")
            info_layout.addWidget(sub_lbl)
            row_layout.addLayout(info_layout)

            row_layout.addStretch()

            # Right: Checkbox indicator (mouse transparent so click lands on the card)
            cb = QCheckBox()
            cb.setChecked(is_checked)
            cb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            row_layout.addWidget(cb)

            # Apply initial tile styling
            self.apply_domain_tile_style(row, is_checked)

            # Click handler on the tile
            def make_click_handler(d=domain):
                def handler(event):
                    self.toggle_domain_selection(d)
                return handler

            row.mousePressEvent = make_click_handler(domain)
            self.domain_tile_widgets[domain] = (row, cb)

            item.setSizeHint(QSize(0, 44))
            self.sel_domains_list.addItem(item)
            self.sel_domains_list.setItemWidget(item, row)

        self.update_selective_summary()

    def apply_domain_tile_style(self, frame: QFrame, is_checked: bool):
        is_dark = self.is_dark_mode()
        if is_checked:
            bg = "rgba(56, 139, 253, 0.12)" if is_dark else "rgba(9, 105, 218, 0.10)"
            border = "#388BFD" if is_dark else "#0969DA"
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg};
                    border: 1px solid {border};
                    border-left: 3px solid {border};
                    border-radius: 6px;
                }}
            """)
        else:
            bg = "#1C2128" if is_dark else "#FFFFFF"
            border = "#30363D" if is_dark else "#D0D7DE"
            hover_bg = "#21262D" if is_dark else "#F6F8FA"
            hover_border = "#58A6FF" if is_dark else "#0969DA"
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg};
                    border: 1px solid {border};
                    border-radius: 6px;
                }}
                QFrame:hover {{
                    background-color: {hover_bg};
                    border-color: {hover_border};
                }}
            """)

    def toggle_domain_selection(self, domain: str):
        if domain in self.selected_selective_domains:
            self.selected_selective_domains.remove(domain)
            is_checked = False
        else:
            self.selected_selective_domains.add(domain)
            is_checked = True

        if hasattr(self, "domain_tile_widgets") and domain in self.domain_tile_widgets:
            frame, cb = self.domain_tile_widgets[domain]
            cb.setChecked(is_checked)
            self.apply_domain_tile_style(frame, is_checked)

        self.update_selective_summary()

    def step_selective_duration(self, delta: int):
        val = self.sel_duration_spin.value() + delta
        val = max(self.sel_duration_spin.minimum(), min(self.sel_duration_spin.maximum(), val))
        self.sel_duration_spin.setValue(val)

    def on_select_all_selective(self):
        search_query = self.sel_search_input.text().strip().lower() if hasattr(self, "sel_search_input") else ""
        for d in self.blocked_domains:
            if not search_query or search_query in d.lower():
                self.selected_selective_domains.add(d)
                if hasattr(self, "domain_tile_widgets") and d in self.domain_tile_widgets:
                    frame, cb = self.domain_tile_widgets[d]
                    cb.setChecked(True)
                    self.apply_domain_tile_style(frame, True)
        self.update_selective_summary()

    def on_deselect_all_selective(self):
        search_query = self.sel_search_input.text().strip().lower() if hasattr(self, "sel_search_input") else ""
        if search_query:
            for d in self.blocked_domains:
                if search_query in d.lower():
                    self.selected_selective_domains.discard(d)
                    if hasattr(self, "domain_tile_widgets") and d in self.domain_tile_widgets:
                        frame, cb = self.domain_tile_widgets[d]
                        cb.setChecked(False)
                        self.apply_domain_tile_style(frame, False)
        else:
            self.selected_selective_domains.clear()
            if hasattr(self, "domain_tile_widgets"):
                for d, (frame, cb) in self.domain_tile_widgets.items():
                    cb.setChecked(False)
                    self.apply_domain_tile_style(frame, False)
        self.update_selective_summary()

    def on_sel_add_domain_clicked(self):
        raw = self.sel_add_input.text().strip()
        if not raw:
            return
        domain = sanitize_domain(raw)
        if not domain:
            self.sel_add_feedback_lbl.setStyleSheet("font-size: 11px; color: #F85149; font-weight: 600;")
            self.sel_add_feedback_lbl.setText("Formato no válido (ej: twitter.com)")
            QTimer.singleShot(3000, lambda: self.sel_add_feedback_lbl.setText(""))
            return

        if domain not in self.blocked_domains:
            self.blocked_domains.append(domain)
            self.auto_save_domains()
            self.render_domains_list()

        self.selected_selective_domains.add(domain)
        self.sel_add_input.clear()
        self.render_selective_domains_list()
        self.sel_add_feedback_lbl.setStyleSheet("font-size: 11px; color: #2EA043; font-weight: 600;")
        self.sel_add_feedback_lbl.setText(f"Añadido y seleccionado: {domain}")
        QTimer.singleShot(3000, lambda: self.sel_add_feedback_lbl.setText(""))

    def on_refresh_selective_list(self):
        res = self.ipc.get_config()
        if res.get("status") == "ok":
            self.config_data = res.get("config", {})
            self.blocked_domains = list(self.config_data.get("blocked_domains", []))
        self.render_selective_domains_list()
        self.render_domains_list()
        self.sel_add_feedback_lbl.setStyleSheet("font-size: 11px; color: #58A6FF; font-weight: 600;")
        self.sel_add_feedback_lbl.setText("Lista sincronizada")
        QTimer.singleShot(2500, lambda: self.sel_add_feedback_lbl.setText(""))

    def on_tab_changed(self, index: int):
        if index == 0:
            self.render_domains_list()
        elif index == 1:
            self.render_selective_domains_list()

    def update_selective_summary(self):
        if not hasattr(self, "sel_count_lbl"):
            return

        count = len(self.selected_selective_domains)
        total = len(self.blocked_domains)
        self.sel_count_lbl.setText(f"{count} de {total} seleccionados")

        dur = self.sel_duration_spin.value()
        target_dt = datetime.now() + timedelta(minutes=dur)
        target_str = target_dt.strftime("%H:%M")

        if count == 0:
            self.sel_summary_title.setText("Parámetros de Sesión")
            self.sel_summary_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #8B949E;")
            self.sel_summary_lbl.setText("Marca al menos un sitio de la lista izquierda para iniciar el bloqueo.")
            self.sel_start_btn.setEnabled(False)
            self.sel_start_btn.setText("Selecciona sitios para iniciar")
            self.sel_start_btn.setToolTip("Selecciona al menos un sitio para activar el bloqueo.")
        else:
            plural = "sitio" if count == 1 else "sitios"
            self.sel_summary_title.setText("Parámetros de Sesión")
            self.sel_summary_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #58A6FF;")
            self.sel_summary_lbl.setText(
                f"• Sitios seleccionados: <b>{count} {plural}</b><br>"
                f"• Tiempo de bloqueo: <b>{dur} min</b><br>"
                f"• Finalizará a las: <b>{target_str}</b>"
            )
            # Check if active lock is running
            res = self.ipc.get_status()
            is_selective = res.get("is_selective", False) if res.get("status") == "ok" else False
            if not is_selective:
                self.sel_start_btn.setEnabled(True)
                self.sel_start_btn.setText(f"Iniciar Bloqueo ({dur} min)")
                self.sel_start_btn.setToolTip(f"Iniciar bloqueo selectivo de {count} {plural} por {dur} minutos.")

    def on_start_selective_lock(self):
        if not self.selected_selective_domains:
            self.sel_feedback_lbl.setStyleSheet("font-size: 11px; color: #F85149; font-weight: 600;")
            self.sel_feedback_lbl.setText("Selecciona al menos un sitio")
            QTimer.singleShot(3000, lambda: self.sel_feedback_lbl.setText(""))
            return

        dur = self.sel_duration_spin.value()
        domains = sorted(list(self.selected_selective_domains))
        res = self.ipc.request_selective_lock(domains, dur)

        if res.get("status") == "ok":
            self.sel_feedback_lbl.setStyleSheet("font-size: 11px; color: #2EA043; font-weight: 600;")
            self.sel_feedback_lbl.setText(f"Bloqueo activado ({len(domains)} sitios)")
            QTimer.singleShot(3500, lambda: self.sel_feedback_lbl.setText(""))
            self.refresh_live_status()
            self.config_saved.emit()
        else:
            err = res.get("message") or res.get("error") or "Error al activar el bloqueo"
            self.sel_feedback_lbl.setStyleSheet("font-size: 11px; color: #F85149; font-weight: 600;")
            self.sel_feedback_lbl.setText(f"Error: {err}")
            QTimer.singleShot(4000, lambda: self.sel_feedback_lbl.setText(""))

    def on_cancel_selective_clicked(self):
        res = self.ipc.cancel_selective_lock()
        if res.get("status") == "ok":
            self.sel_feedback_lbl.setStyleSheet("font-size: 11px; color: #2EA043; font-weight: 600;")
            self.sel_feedback_lbl.setText("Bloqueo selectivo finalizado")
            QTimer.singleShot(3000, lambda: self.sel_feedback_lbl.setText(""))
            self.refresh_live_status()
            self.config_saved.emit()


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

    def refresh_live_status(self):
        res = self.ipc.get_status()
        if res.get("status") != "ok":
            self.status_badge.setText("FUERA DE LÍNEA")
            self.status_badge.setStyleSheet("background-color: rgba(110, 118, 129, 0.2); color: #8F98A0; font-weight: 700; padding: 4px 10px; border-radius: 12px; border: 1px solid #30363D;")
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

            elif reason == "SELECTIVE_LOCK":
                sel_count = len(res.get("selective_domains", []))
                self.status_badge.setText("BLOQUEO SELECTIVO")
                self.status_badge.setStyleSheet("background-color: rgba(56, 139, 253, 0.15); color: #58A6FF; font-weight: 700; padding: 4px 10px; border-radius: 12px; border: 1px solid rgba(56, 139, 253, 0.3);")
                icon_act = os.path.join(self.resource_dir, "icon-active.svg")
                if os.path.exists(icon_act):
                    self.header_icon_lbl.setPixmap(QIcon(icon_act).pixmap(28, 28))
                self.dash_state_pill.setText("BLOQUEO SELECTIVO")
                self.dash_state_pill.setStyleSheet("border: 1px solid #388BFD; color: #58A6FF; font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px; background-color: rgba(56, 139, 253, 0.12);")
                self.dash_state_title.setText(f"Bloqueo Selectivo ({sel_count} sitios)")
                self.dash_desc_lbl.setText(f"Bloqueo específico activo para {sel_count} dominios seleccionados.")
                self.dash_countdown_lbl.setStyleSheet("font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; font-size: 22px; font-weight: 700; color: #58A6FF;")
                self.dash_progress_bar.setValue(100)
                self.dash_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #388BFD; }")
                self.btn_stop_focus.setVisible(True)
                self.btn_stop_focus.setText("Finalizar Bloqueo")
                self.btn_stop_focus.setToolTip("Finalizar el bloqueo selectivo y restaurar el acceso a todos los sitios.")

                self.btn_primary_action.setText("Bloqueo en Curso")
                self.btn_primary_action.setEnabled(False)
                self.btn_pomodoro_25.setEnabled(False)
                self.btn_pomodoro_50.setEnabled(False)

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

        # Update Selective Lock Tab UI State
        is_selective = res.get("is_selective", False)
        selective_domains = res.get("selective_domains", [])

        if hasattr(self, "sel_active_card"):
            if is_selective and selective_domains:
                self.sel_active_card.setVisible(True)
                if hasattr(self, "sel_status_badge"):
                    self.sel_status_badge.setText("EN CURSO")
                    self.sel_status_badge.setStyleSheet("font-size: 10px; font-weight: 700; padding: 4px 10px; border-radius: 12px; border: 1px solid #388BFD; color: #58A6FF; background-color: rgba(56, 139, 253, 0.15);")
                self.sel_active_countdown_lbl.setText(f"{human_time.upper()} RESTANTES")
                badges_text = "  /  ".join(selective_domains)
                self.sel_active_domains_lbl.setText(f"Sitios bloqueados: <b>{badges_text}</b>")
                self.sel_active_end_lbl.setText(f"Término programado: {target}")
                self.sel_start_btn.setEnabled(False)
                self.sel_start_btn.setText("Bloqueo selectivo en curso")
                self.sel_start_btn.setToolTip("Ya hay una sesión de bloqueo selectivo activa.")
            else:
                self.sel_active_card.setVisible(False)
                if hasattr(self, "sel_status_badge"):
                    self.sel_status_badge.setText("EN ESPERA")
                    self.sel_status_badge.setStyleSheet("font-size: 10px; font-weight: 700; padding: 4px 10px; border-radius: 12px; border: 1px solid #30363D; color: #8B949E; background-color: rgba(110, 118, 129, 0.15);")
                self.update_selective_summary()


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
