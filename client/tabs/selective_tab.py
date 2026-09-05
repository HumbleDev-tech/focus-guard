"""
Focus-Guard Selective Blocking Tab Component
Handles selective domain locking, duration pickers, and active session management.
"""
from datetime import datetime, timedelta
from typing import List, Set, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QScrollArea, QAbstractItemView, QFrame, QSpinBox,
    QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QPalette

from client.utils import sanitize_domain


class SelectiveTab(QWidget):
    """Component managing the Selective Blocking tab."""
    start_lock_requested = pyqtSignal(list, int)  # (domains, minutes)
    cancel_lock_requested = pyqtSignal()
    domain_added = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.blocked_domains: List[str] = []
        self.selected_selective_domains: Set[str] = set()
        self.domain_tile_widgets: Dict[str, Any] = {}
        self.is_active_selective: bool = False

        self.setup_ui()

    def is_dark_mode(self) -> bool:
        bg = self.palette().color(QPalette.ColorRole.Window)
        return bg.lightness() < 128

    def setup_ui(self):
        scroll = QScrollArea(self)
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

        # 2. Active Session Hero Card
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
        self.sel_active_domains_lbl.setObjectName("sectionHeader")
        self.sel_active_domains_lbl.setWordWrap(True)
        active_layout.addWidget(self.sel_active_domains_lbl)

        act_bottom_row = QHBoxLayout()
        self.sel_active_end_lbl = QLabel("")
        self.sel_active_end_lbl.setObjectName("cardDesc")
        act_bottom_row.addWidget(self.sel_active_end_lbl)
        act_bottom_row.addStretch()

        self.sel_cancel_btn = QPushButton("Finalizar Bloqueo")
        self.sel_cancel_btn.setObjectName("dangerBtn")
        self.sel_cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sel_cancel_btn.clicked.connect(self.cancel_lock_requested.emit)
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
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self.render_selective_domains_list)
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
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroll)

    def set_domains(self, domains: List[str]):
        self.blocked_domains = list(domains)
        self.selected_selective_domains = self.selected_selective_domains.intersection(set(self.blocked_domains))
        self.render_selective_domains_list()

    def get_selected_domains(self) -> List[str]:
        return sorted(list(self.selected_selective_domains))

    def step_selective_duration(self, delta: int):
        val = self.sel_duration_spin.value() + delta
        val = max(self.sel_duration_spin.minimum(), min(self.sel_duration_spin.maximum(), val))
        self.sel_duration_spin.setValue(val)

    def render_selective_domains_list(self):
        self.sel_domains_list.clear()
        self.domain_tile_widgets = {}

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

            dot_lbl = QLabel("•")
            dot_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #58A6FF; border: none; background: transparent;")
            row_layout.addWidget(dot_lbl)

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

            cb = QCheckBox()
            cb.setChecked(is_checked)
            cb.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            row_layout.addWidget(cb)

            self.apply_domain_tile_style(row, is_checked)

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
            frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg};
                    border: 1px solid {border};
                    border-radius: 6px;
                }}
                QFrame:hover {{
                    background-color: {hover_bg};
                    border-color: #58A6FF;
                }}
            """)

    def toggle_domain_selection(self, domain: str):
        if domain in self.selected_selective_domains:
            self.selected_selective_domains.remove(domain)
            is_checked = False
        else:
            self.selected_selective_domains.add(domain)
            is_checked = True

        if domain in self.domain_tile_widgets:
            frame, cb = self.domain_tile_widgets[domain]
            cb.setChecked(is_checked)
            self.apply_domain_tile_style(frame, is_checked)

        self.update_selective_summary()

    def on_select_all_selective(self):
        query = self.sel_search_input.text().strip().lower()
        targets = [d for d in self.blocked_domains if (not query or query in d.lower())]
        for d in targets:
            self.selected_selective_domains.add(d)
        self.render_selective_domains_list()

    def on_deselect_all_selective(self):
        query = self.sel_search_input.text().strip().lower()
        if query:
            targets = [d for d in self.blocked_domains if query in d.lower()]
            for d in targets:
                self.selected_selective_domains.discard(d)
        else:
            self.selected_selective_domains.clear()
        self.render_selective_domains_list()

    def on_sel_add_domain_clicked(self):
        raw = self.sel_add_input.text()
        clean = sanitize_domain(raw)
        if not clean:
            self.sel_add_feedback_lbl.setStyleSheet("font-size: 11px; color: #F85149; font-weight: 600;")
            self.sel_add_feedback_lbl.setText("Formato de dominio no reconocido")
            QTimer.singleShot(2500, lambda: self.sel_add_feedback_lbl.setText(""))
            return

        self.sel_add_input.clear()
        self.selected_selective_domains.add(clean)

        if clean not in self.blocked_domains:
            self.blocked_domains.append(clean)
            self.domain_added.emit(clean)

        self.render_selective_domains_list()
        self.sel_add_feedback_lbl.setStyleSheet("font-size: 11px; color: #2EA043; font-weight: 600;")
        self.sel_add_feedback_lbl.setText(f"'{clean}' seleccionado para la sesión")
        QTimer.singleShot(2500, lambda: self.sel_add_feedback_lbl.setText(""))

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
            if not self.is_active_selective:
                self.sel_start_btn.setEnabled(True)
                self.sel_start_btn.setText(f"Iniciar Bloqueo ({dur} min)")
                self.sel_start_btn.setToolTip(f"Iniciar bloqueo selectivo de {count} {plural} por {dur} minutos.")

    def on_start_selective_lock(self):
        if not self.selected_selective_domains:
            self.set_feedback("Selecciona al menos un sitio", is_success=False)
            return

        dur = self.sel_duration_spin.value()
        domains = sorted(list(self.selected_selective_domains))
        self.start_lock_requested.emit(domains, dur)

    def set_feedback(self, text: str, is_success: bool = True):
        color = "#2EA043" if is_success else "#F85149"
        self.sel_feedback_lbl.setStyleSheet(f"font-size: 11px; color: {color}; font-weight: 600;")
        self.sel_feedback_lbl.setText(text)
        QTimer.singleShot(3500, lambda: self.sel_feedback_lbl.setText(""))

    def update_active_status(
        self,
        is_selective: bool,
        remaining_sec: int,
        selective_domains: List[str] | None = None,
        target_time: str = "",
        human_time: str = ""
    ):
        self.is_active_selective = is_selective
        domains_list = selective_domains or []

        if is_selective and domains_list:
            self.sel_status_badge.setText("EN CURSO")
            self.sel_status_badge.setStyleSheet("font-size: 10px; font-weight: 700; padding: 4px 10px; border-radius: 12px; border: 1px solid #388BFD; color: #58A6FF; background-color: rgba(56, 139, 253, 0.15);")
            self.sel_active_card.setVisible(True)

            if human_time:
                self.sel_active_countdown_lbl.setText(f"{human_time.upper()} RESTANTES")
            else:
                mins = remaining_sec // 60
                secs = remaining_sec % 60
                self.sel_active_countdown_lbl.setText(f"{mins:02d}:{secs:02d} RESTANTES")

            num_domains = len(domains_list)
            domains_preview = ", ".join(domains_list[:3])
            if num_domains > 3:
                domains_preview += f" (+{num_domains - 3} más)"
            self.sel_active_domains_lbl.setText(f"Bloqueando {num_domains} sitios: {domains_preview}")
            self.sel_active_end_lbl.setText(f"Finaliza a las {target_time}" if target_time else "")

            self.sel_start_btn.setEnabled(False)
            self.sel_start_btn.setText("Bloqueo Selectivo en curso")
            self.sel_start_btn.setToolTip("Ya hay un bloqueo selectivo activo.")
        else:
            self.sel_status_badge.setText("EN ESPERA")
            self.sel_status_badge.setStyleSheet("font-size: 10px; font-weight: 700; padding: 4px 10px; border-radius: 12px; border: 1px solid #30363D; color: #8B949E; background-color: rgba(110, 118, 129, 0.15);")
            self.sel_active_card.setVisible(False)
            self.update_selective_summary()
