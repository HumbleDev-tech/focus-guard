"""
Focus-Guard Selective Blocking Tab Component
Handles selective domain locking, duration pickers, and active session management.
"""
from datetime import datetime, timedelta
from typing import List, Set, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QScrollArea, QAbstractItemView, QFrame, QSpinBox,
    QCheckBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QPalette

from client.utils import sanitize_domain
from client.icons import get_themed_icon, get_pixmap
from client.i18n import t


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
        self.is_indefinite_selective: bool = False

        self.setup_ui()

    def is_dark_mode(self) -> bool:
        win = self.window()
        if win and hasattr(win, "is_dark_mode"):
            return win.is_dark_mode()
        if self.parent() and hasattr(self.parent(), "is_dark_mode"):
            return self.parent().is_dark_mode()
        from PyQt6.QtCore import QSettings
        mode = QSettings("FocusGuard", "FocusGuardTray").value("theme_mode", "auto")
        if mode == "dark":
            return True
        elif mode == "light":
            return False
        bg = self.palette().color(QPalette.ColorRole.Window)
        return bg.lightness() < 128

    def update_icons(self, is_dark: bool | None = None):
        if is_dark is None:
            is_dark = self.is_dark_mode()
        if hasattr(self, "sel_add_btn"):
            self.sel_add_btn.setIcon(get_themed_icon("plus", is_dark, role="white", size=14))
        if hasattr(self, "sel_step_minus"):
            self.sel_step_minus.setIcon(get_themed_icon("minus", is_dark, size=13, active_role="white"))
        if hasattr(self, "sel_step_plus"):
            self.sel_step_plus.setIcon(get_themed_icon("plus", is_dark, size=13, active_role="white"))
        if hasattr(self, "sel_start_btn"):
            self.sel_start_btn.setIcon(get_themed_icon("lock", is_dark, role="white", size=15))
        if hasattr(self, "sel_indefinite_btn"):
            self.sel_indefinite_btn.setIcon(get_themed_icon("lock", is_dark, role="secondary", size=15))

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
        self.header_frame = QFrame()
        self.header_frame.setObjectName("settingsCard")
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(12)

        hdr_info = QVBoxLayout()
        hdr_info.setSpacing(2)
        self.hdr_title = QLabel(t("selective.header_title"))
        self.hdr_title.setObjectName("sectionHeader")
        self.hdr_sub = QLabel(t("selective.header_desc"))
        self.hdr_sub.setObjectName("cardDesc")
        hdr_info.addWidget(self.hdr_title)
        hdr_info.addWidget(self.hdr_sub)
        header_layout.addLayout(hdr_info)
        header_layout.addStretch()

        self.sel_status_badge = QLabel(t("selective.badge_idle"))
        self.sel_status_badge.setObjectName("statusBadge")
        header_layout.addWidget(self.sel_status_badge)
        main_layout.addWidget(self.header_frame)

        # 2. Active Session Hero Card
        self.sel_active_card = QFrame()
        self.sel_active_card.setObjectName("heroCard")
        active_layout = QVBoxLayout(self.sel_active_card)
        active_layout.setSpacing(10)

        act_top_row = QHBoxLayout()
        self.act_pill = QLabel(t("selective.hero_pill"))
        self.act_pill.setStyleSheet("background-color: rgba(56, 139, 253, 0.15); color: #58A6FF; font-weight: 700; font-size: 10px; padding: 3px 8px; border-radius: 12px; border: 1px solid rgba(56, 139, 253, 0.3);")
        act_top_row.addWidget(self.act_pill)
        act_top_row.addStretch()

        self.sel_active_countdown_lbl = QLabel(t("selective.hero_calculating"))
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

        self.sel_cancel_btn = QPushButton(t("selective.btn_cancel"))
        self.sel_cancel_btn.setObjectName("dangerBtn")
        self.sel_cancel_btn.setMinimumHeight(34)
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
        self.col_title = QLabel(t("selective.step1_title"))
        self.col_title.setObjectName("sectionHeader")
        col_top.addWidget(self.col_title)
        col_top.addStretch()

        self.sel_count_lbl = QLabel(t("selective.count_selected", count=0))
        self.sel_count_lbl.setObjectName("statusBadge")
        col_top.addWidget(self.sel_count_lbl)
        sites_layout.addLayout(col_top)

        # Quick Add Site Row directly in this tab
        add_row = QHBoxLayout()
        add_row.setSpacing(6)

        self.sel_add_input = QLineEdit()
        self.sel_add_input.setPlaceholderText(t("selective.add_placeholder"))
        self.sel_add_input.returnPressed.connect(self.on_sel_add_domain_clicked)
        add_row.addWidget(self.sel_add_input)

        self.sel_add_btn = QPushButton(t("selective.btn_add"))
        self.sel_add_btn.setObjectName("primaryBtn")
        self.sel_add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sel_add_btn.clicked.connect(self.on_sel_add_domain_clicked)
        add_row.addWidget(self.sel_add_btn)
        sites_layout.addLayout(add_row)

        self.sel_add_feedback_lbl = QLabel("")
        self.sel_add_feedback_lbl.setStyleSheet("font-size: 11px; font-weight: 600;")
        sites_layout.addWidget(self.sel_add_feedback_lbl)

        # Search filter, bulk actions, and refresh button
        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(6)

        self.sel_search_input = QLineEdit()
        self.sel_search_input.setPlaceholderText(t("selective.search_placeholder"))
        self.sel_search_input.setFixedWidth(170)
        self.sel_search_input.textChanged.connect(lambda: self.render_selective_domains_list())
        toolbar_row.addWidget(self.sel_search_input)

        self.sel_all_btn = QPushButton(t("selective.btn_select_all"))
        self.sel_all_btn.setObjectName("presetChipSmall")
        self.sel_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sel_all_btn.clicked.connect(self.on_select_all_selective)
        toolbar_row.addWidget(self.sel_all_btn)

        self.sel_desel_btn = QPushButton(t("selective.btn_deselect_all"))
        self.sel_desel_btn.setObjectName("presetChipSmall")
        self.sel_desel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sel_desel_btn.clicked.connect(self.on_deselect_all_selective)
        toolbar_row.addWidget(self.sel_desel_btn)

        self.refresh_btn = QPushButton(t("selective.btn_refresh"))
        self.refresh_btn.setObjectName("presetChipSmall")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.render_selective_domains_list)
        toolbar_row.addWidget(self.refresh_btn)

        sites_layout.addLayout(toolbar_row)

        self.sel_domains_list = QListWidget()
        self.sel_domains_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.sel_domains_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.sel_domains_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sel_domains_list.setMinimumHeight(300)
        self.sel_domains_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sites_layout.addWidget(self.sel_domains_list, stretch=1)

        split_layout.addWidget(sites_card, stretch=55)

        # RIGHT COLUMN (45%): Duration & Launch Action
        ctrl_card = QFrame()
        ctrl_card.setObjectName("settingsCard")
        ctrl_layout = QVBoxLayout(ctrl_card)
        ctrl_layout.setContentsMargins(16, 14, 16, 14)
        ctrl_layout.setSpacing(12)

        self.ctrl_title = QLabel(t("selective.step2_title"))
        self.ctrl_title.setObjectName("sectionHeader")
        ctrl_layout.addWidget(self.ctrl_title)

        self.ctrl_desc = QLabel(t("selective.step2_desc"))
        self.ctrl_desc.setObjectName("cardDesc")
        self.ctrl_desc.setWordWrap(True)
        ctrl_layout.addWidget(self.ctrl_desc)

        # 1) Timed Blocking Card
        timed_box = QFrame()
        timed_box.setObjectName("innerCard")
        timed_layout = QVBoxLayout(timed_box)
        timed_layout.setSpacing(8)

        self.timed_hdr = QLabel(t("selective.timed_hdr"))
        self.timed_hdr.setObjectName("fieldLabel")
        timed_layout.addWidget(self.timed_hdr)

        stepper_row = QHBoxLayout()
        stepper_row.setSpacing(6)

        self.sel_step_minus = QPushButton()
        self.sel_step_minus.setObjectName("stepBtn")
        self.sel_step_minus.setToolTip(t("selective.step_minus_tooltip"))
        self.sel_step_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sel_step_minus.clicked.connect(lambda: self.step_selective_duration(-5))
        stepper_row.addWidget(self.sel_step_minus)

        self.sel_duration_spin = QSpinBox()
        self.sel_duration_spin.setRange(1, 1440)
        self.sel_duration_spin.setSingleStep(5)
        self.sel_duration_spin.setValue(25)
        self.sel_duration_spin.setSuffix(t("selective.spin_suffix"))
        self.sel_duration_spin.setFixedWidth(84)
        self.sel_duration_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sel_duration_spin.valueChanged.connect(self.update_selective_summary)
        stepper_row.addWidget(self.sel_duration_spin)

        self.sel_step_plus = QPushButton()
        self.sel_step_plus.setObjectName("stepBtn")
        self.sel_step_plus.setToolTip(t("selective.step_plus_tooltip"))
        self.sel_step_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sel_step_plus.clicked.connect(lambda: self.step_selective_duration(5))
        stepper_row.addWidget(self.sel_step_plus)
        stepper_row.addStretch()

        timed_layout.addLayout(stepper_row)

        self.sel_start_btn = QPushButton(t("selective.btn_start_timed", minutes=25))
        self.sel_start_btn.setObjectName("primaryBtn")
        self.sel_start_btn.setMinimumHeight(38)
        self.sel_start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sel_start_btn.clicked.connect(self.on_start_selective_lock)
        timed_layout.addWidget(self.sel_start_btn)

        ctrl_layout.addWidget(timed_box)

        # 2) Indefinite Blocking Card
        indef_box = QFrame()
        indef_box.setObjectName("innerCard")
        indef_layout = QVBoxLayout(indef_box)
        indef_layout.setSpacing(8)

        self.indef_hdr = QLabel(t("selective.indef_hdr"))
        self.indef_hdr.setObjectName("fieldLabel")
        indef_layout.addWidget(self.indef_hdr)

        self.indef_desc = QLabel(t("selective.indef_desc"))
        self.indef_desc.setObjectName("cardDesc")
        self.indef_desc.setWordWrap(True)
        indef_layout.addWidget(self.indef_desc)

        self.sel_indefinite_btn = QPushButton(t("selective.btn_start_indefinite"))
        self.sel_indefinite_btn.setObjectName("secondaryBtn")
        self.sel_indefinite_btn.setMinimumHeight(38)
        self.sel_indefinite_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sel_indefinite_btn.clicked.connect(self.on_indefinite_button_clicked)
        indef_layout.addWidget(self.sel_indefinite_btn)

        ctrl_layout.addWidget(indef_box)

        # Session Forecast Card
        self.sel_summary_card = QFrame()
        self.sel_summary_card.setObjectName("previewCard")
        sum_layout = QVBoxLayout(self.sel_summary_card)
        sum_layout.setContentsMargins(10, 8, 10, 8)
        sum_layout.setSpacing(4)

        self.sel_summary_title = QLabel(t("selective.summary_title"))
        self.sel_summary_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #58A6FF;")
        sum_layout.addWidget(self.sel_summary_title)

        self.sel_summary_lbl = QLabel("")
        self.sel_summary_lbl.setObjectName("cardDesc")
        self.sel_summary_lbl.setWordWrap(True)
        sum_layout.addWidget(self.sel_summary_lbl)

        ctrl_layout.addWidget(self.sel_summary_card)
        ctrl_layout.addStretch()

        self.sel_feedback_lbl = QLabel("")
        self.sel_feedback_lbl.setStyleSheet("font-size: 11px; font-weight: 600;")
        self.sel_feedback_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ctrl_layout.addWidget(self.sel_feedback_lbl)

        split_layout.addWidget(ctrl_card, stretch=45)
        main_layout.addLayout(split_layout, stretch=1)

        self.update_icons()

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

        total_cnt = len(self.blocked_domains)
        if hasattr(self, "sel_search_input"):
            self.sel_search_input.setEnabled(total_cnt > 0 and not getattr(self, "session_running", False))
            self.sel_search_input.setPlaceholderText(t("selective.search_empty") if total_cnt == 0 else t("selective.search_placeholder"))

        is_dark = self.is_dark_mode()
        text_color = "#F0F6FC" if is_dark else "#1F2328"

        if not self.blocked_domains:
            empty_item = QListWidgetItem()
            empty_box = QWidget()
            empty_layout = QVBoxLayout(empty_box)
            empty_layout.setContentsMargins(20, 30, 20, 30)
            empty_layout.setSpacing(6)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            title = QLabel(t("selective.empty_title"))
            title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {text_color}; background: transparent; border: none;")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(title)

            sub = QLabel(t("selective.empty_desc"))
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
            empty_lbl = QLabel(t("selective.search_no_matches"))
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

            icon_lbl = QLabel()
            icon_lbl.setPixmap(get_pixmap("globe", color="#388BFD" if is_dark else "#0969DA", size=14))
            icon_lbl.setStyleSheet("border: none; background: transparent;")
            row_layout.addWidget(icon_lbl)

            info_layout = QVBoxLayout()
            info_layout.setSpacing(1)
            name_lbl = QLabel(domain)
            name_lbl.setStyleSheet(f"font-weight: 600; font-size: 12.5px; color: {text_color}; background: transparent; border: none;")
            info_layout.addWidget(name_lbl)

            is_active_lock = getattr(self, "session_running", False) and is_checked
            sub_lbl = QLabel(t("selective.tile_active_lock") if is_active_lock else t("selective.tile_individual_rule"))
            sub_lbl.setStyleSheet(
                "font-size: 10px; color: #58A6FF; font-weight: 600; background: transparent; border: none;"
                if is_active_lock
                else "font-size: 10px; color: #8B949E; background: transparent; border: none;"
            )
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
                    if not getattr(self, "session_running", False):
                        self.toggle_domain_selection(d)
                return handler

            row.mousePressEvent = make_click_handler(domain)
            self.domain_tile_widgets[domain] = (row, cb)

            item.setSizeHint(QSize(0, 48))
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
            self.sel_add_feedback_lbl.setText(t("selective.feedback_invalid_domain"))
            QTimer.singleShot(2500, lambda: self.sel_add_feedback_lbl.setText(""))
            return

        self.sel_add_input.clear()
        self.selected_selective_domains.add(clean)

        if clean not in self.blocked_domains:
            self.blocked_domains.append(clean)
            self.domain_added.emit(clean)

        self.render_selective_domains_list()
        self.sel_add_feedback_lbl.setStyleSheet("font-size: 11px; color: #2EA043; font-weight: 600;")
        self.sel_add_feedback_lbl.setText(t("selective.feedback_domain_selected", domain=clean))
        QTimer.singleShot(2500, lambda: self.sel_add_feedback_lbl.setText(""))

    def update_selective_summary(self):
        if not hasattr(self, "sel_count_lbl"):
            return

        count = len(self.selected_selective_domains)
        total = len(self.blocked_domains)

        if getattr(self, "session_running", False):
            self.sel_count_lbl.setText(t("selective.count_blocked_of", count=count, total=total))
            self.sel_count_lbl.setStyleSheet(
                "font-size: 10px; font-weight: 700; padding: 3px 10px; border-radius: 12px; "
                "border: 1px solid #388BFD; color: #58A6FF; background-color: rgba(56, 139, 253, 0.12);"
            )
            plural = t("selective.plural_site") if count == 1 else t("selective.plural_sites")
            self.sel_summary_title.setText(t("selective.summary_title_active"))
            self.sel_summary_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #58A6FF;")
            self.sel_summary_lbl.setText(t("selective.summary_active_desc", count=count, plural=plural))
            self.sel_start_btn.setEnabled(False)
            self.sel_start_btn.setText(t("selective.btn_active_running"))
            self.sel_indefinite_btn.setEnabled(False)
            self.sel_indefinite_btn.setText(t("selective.btn_lock_running"))
            self.sel_indefinite_btn.setObjectName("secondaryBtn")
            self.sel_indefinite_btn.setStyleSheet("")
            return

        self.sel_count_lbl.setText(t("selective.count_selected_of", count=count, total=total))
        self.sel_count_lbl.setStyleSheet("")

        dur = self.sel_duration_spin.value()
        target_dt = datetime.now() + timedelta(minutes=dur)
        target_str = target_dt.strftime("%H:%M")

        if count == 0:
            self.sel_summary_title.setText(t("selective.summary_title"))
            self.sel_summary_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #8B949E;")
            self.sel_summary_lbl.setText(t("selective.summary_none_desc"))
            self.sel_start_btn.setEnabled(False)
            self.sel_start_btn.setText(t("selective.btn_select_to_start"))
            self.sel_start_btn.setToolTip(t("selective.btn_select_tooltip"))
            self.sel_indefinite_btn.setEnabled(False)
            self.sel_indefinite_btn.setText(t("selective.btn_start_indefinite"))
            self.sel_indefinite_btn.setObjectName("secondaryBtn")
            self.sel_indefinite_btn.setStyleSheet("")
        else:
            plural = t("selective.plural_site") if count == 1 else t("selective.plural_sites")
            self.sel_summary_title.setText(t("selective.summary_title"))
            self.sel_summary_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #58A6FF;")
            self.sel_summary_lbl.setText(t("selective.summary_configured_desc", count=count, plural=plural, dur=dur, target=target_str))
            self.sel_start_btn.setEnabled(True)
            self.sel_start_btn.setText(t("selective.btn_start_timed", minutes=dur))
            self.sel_start_btn.setToolTip(f"{t('selective.btn_start_timed', minutes=dur)} ({count} {plural})")
            self.sel_indefinite_btn.setEnabled(True)
            self.sel_indefinite_btn.setText(t("selective.btn_indefinite_with_count", count=count, plural=plural))
            self.sel_indefinite_btn.setObjectName("secondaryBtn")
            self.sel_indefinite_btn.setStyleSheet("")

    def on_start_selective_lock(self):
        if not self.selected_selective_domains:
            self.set_feedback(t("selective.feedback_select_at_least_one"), is_success=False)
            return

        dur = self.sel_duration_spin.value()
        domains = sorted(list(self.selected_selective_domains))
        self.start_lock_requested.emit(domains, dur)

    def on_indefinite_button_clicked(self):
        if (self.is_active_selective and self.is_indefinite_selective) or getattr(self, "has_pending_selective", False):
            # Re-clicking while indefinite lock is active or pending cooldown releases the block
            self.cancel_lock_requested.emit()
            return

        if not self.selected_selective_domains:
            self.set_feedback(t("selective.feedback_select_at_least_one"), is_success=False)
            return

        domains = sorted(list(self.selected_selective_domains))
        # 0 minutes indicates indefinite lock
        self.start_lock_requested.emit(domains, 0)

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
        human_time: str = "",
        is_indefinite: bool = False,
        has_pending_selective: bool = False
    ):
        self.is_active_selective = is_selective
        self.is_indefinite_selective = (is_selective and is_indefinite) or has_pending_selective
        self.has_pending_selective = has_pending_selective
        domains_list = selective_domains or []

        # Prevent modifying checklist and buttons while a selective session is running or pending
        session_running = (is_selective and bool(domains_list)) or (has_pending_selective and bool(domains_list))
        self.session_running = session_running

        # Synchronize active domains with the checklist so the list reflects actual blocked sites
        if session_running and domains_list:
            active_set = set(domains_list)
            if self.selected_selective_domains != active_set:
                self.selected_selective_domains = active_set
                self.render_selective_domains_list()

        if hasattr(self, "header_frame"):
            self.header_frame.setVisible(not session_running)

        if hasattr(self, "sel_domains_list"):
            self.sel_domains_list.setEnabled(not session_running)
        if hasattr(self, "sel_all_btn"):
            self.sel_all_btn.setEnabled(not session_running)
        if hasattr(self, "sel_desel_btn"):
            self.sel_desel_btn.setEnabled(not session_running)
        if hasattr(self, "sel_add_input"):
            self.sel_add_input.setEnabled(not session_running)
        if hasattr(self, "sel_add_btn"):
            self.sel_add_btn.setEnabled(not session_running)
        if hasattr(self, "sel_search_input"):
            has_domains = len(self.blocked_domains) > 0
            self.sel_search_input.setEnabled(has_domains and not session_running)
            self.sel_search_input.setPlaceholderText(t("selective.search_empty") if not has_domains else t("selective.search_placeholder"))
        if hasattr(self, "sel_duration_spin"):
            self.sel_duration_spin.setEnabled(not session_running)
        if hasattr(self, "sel_step_minus"):
            self.sel_step_minus.setEnabled(not session_running)
        if hasattr(self, "sel_step_plus"):
            self.sel_step_plus.setEnabled(not session_running)

        if is_selective and domains_list:
            num_domains = len(domains_list)
            domains_preview = ", ".join(domains_list[:3])
            if num_domains > 3:
                domains_preview += f" {t('selective.plus_more', count=num_domains - 3)}"

            self.sel_active_card.setVisible(True)
            self.sel_active_domains_lbl.setText(t("selective.active_blocking_domains", count=num_domains, preview=domains_preview))

            if is_indefinite:
                self.sel_status_badge.setText(t("selective.badge_indefinite"))
                self.sel_status_badge.setStyleSheet(
                    "font-size: 10px; font-weight: 700; padding: 4px 10px; border-radius: 12px; "
                    "border: 1px solid #A371F7; color: #BC8CFF; background-color: rgba(163, 113, 247, 0.15);"
                )
                self.sel_active_countdown_lbl.setText(t("selective.hero_no_limit"))
                self.sel_active_countdown_lbl.setStyleSheet(
                    "font-family: ui-monospace, SFMono-Regular, monospace; font-size: 16px; font-weight: 700; color: #BC8CFF;"
                )
                self.sel_active_end_lbl.setText(t("selective.hero_indefinite_end"))

                self.sel_start_btn.setEnabled(False)
                self.sel_start_btn.setText(t("selective.btn_indefinite_running"))

                self.sel_indefinite_btn.setEnabled(False)
                self.sel_indefinite_btn.setText(t("selective.btn_lock_running"))
                self.sel_indefinite_btn.setObjectName("secondaryBtn")
                self.sel_indefinite_btn.setStyleSheet("")
            else:
                self.sel_status_badge.setText(t("selective.badge_in_progress"))
                self.sel_status_badge.setStyleSheet(
                    "font-size: 10px; font-weight: 700; padding: 4px 10px; border-radius: 12px; "
                    "border: 1px solid #388BFD; color: #58A6FF; background-color: rgba(56, 139, 253, 0.15);"
                )
                if human_time:
                    self.sel_active_countdown_lbl.setText(t("selective.hero_remaining", time=human_time.upper()))
                else:
                    mins = remaining_sec // 60
                    secs = remaining_sec % 60
                    self.sel_active_countdown_lbl.setText(t("selective.hero_remaining", time=f"{mins:02d}:{secs:02d}"))
                self.sel_active_countdown_lbl.setStyleSheet(
                    "font-family: ui-monospace, SFMono-Regular, monospace; font-size: 18px; font-weight: 700; color: #58A6FF;"
                )
                self.sel_active_end_lbl.setText(t("selective.hero_ends_at", time=target_time) if target_time else "")

                self.sel_start_btn.setEnabled(False)
                self.sel_start_btn.setText(t("selective.btn_timed_running"))

                self.sel_indefinite_btn.setEnabled(False)
                self.sel_indefinite_btn.setText(t("selective.btn_timed_running"))
                self.sel_indefinite_btn.setObjectName("secondaryBtn")
                self.sel_indefinite_btn.setStyleSheet("")
            self.update_selective_summary()
        elif has_pending_selective and domains_list:
            num_domains = len(domains_list)
            domains_preview = ", ".join(domains_list[:3])
            if num_domains > 3:
                domains_preview += f" {t('selective.plus_more', count=num_domains - 3)}"

            self.sel_active_card.setVisible(True)
            self.sel_active_domains_lbl.setText(t("selective.active_blocking_domains", count=num_domains, preview=domains_preview))
            self.sel_status_badge.setText(t("selective.badge_pending"))
            self.sel_status_badge.setStyleSheet(
                "font-size: 10px; font-weight: 700; padding: 4px 10px; border-radius: 12px; "
                "border: 1px solid #388BFD; color: #58A6FF; background-color: rgba(56, 139, 253, 0.15);"
            )
            self.sel_active_countdown_lbl.setText(t("selective.hero_cooldown"))
            self.sel_active_countdown_lbl.setStyleSheet(
                "font-family: ui-monospace, SFMono-Regular, monospace; font-size: 16px; font-weight: 700; color: #58A6FF;"
            )
            self.sel_active_end_lbl.setText(t("selective.hero_pending_end"))

            self.sel_start_btn.setEnabled(False)
            self.sel_start_btn.setText(t("selective.btn_indefinite_scheduled"))

            self.sel_indefinite_btn.setEnabled(False)
            self.sel_indefinite_btn.setText(t("selective.btn_lock_running"))
            self.sel_indefinite_btn.setObjectName("secondaryBtn")
            self.sel_indefinite_btn.setStyleSheet("")
            self.update_selective_summary()
        else:
            self.sel_status_badge.setText(t("selective.badge_idle"))
            self.sel_status_badge.setStyleSheet(
                "font-size: 10px; font-weight: 700; padding: 4px 10px; border-radius: 12px; "
                "border: 1px solid #30363D; color: #8B949E; background-color: rgba(110, 118, 129, 0.15);"
            )
            self.sel_active_card.setVisible(False)
            self.update_selective_summary()

    def retranslate_ui(self):
        """Retranslates all text elements on the Selective tab dynamically."""
        if hasattr(self, "hdr_title"):
            self.hdr_title.setText(t("selective.header_title"))
        if hasattr(self, "hdr_sub"):
            self.hdr_sub.setText(t("selective.header_desc"))
        if hasattr(self, "act_pill"):
            self.act_pill.setText(t("selective.hero_pill"))
        if hasattr(self, "sel_cancel_btn"):
            self.sel_cancel_btn.setText(t("selective.btn_cancel"))
        if hasattr(self, "col_title"):
            self.col_title.setText(t("selective.step1_title"))
        if hasattr(self, "sel_add_input"):
            self.sel_add_input.setPlaceholderText(t("selective.add_placeholder"))
        if hasattr(self, "sel_add_btn"):
            self.sel_add_btn.setText(t("selective.btn_add"))
        if hasattr(self, "sel_search_input"):
            has_domains = len(self.blocked_domains) > 0
            self.sel_search_input.setPlaceholderText(t("selective.search_empty") if not has_domains else t("selective.search_placeholder"))
        if hasattr(self, "sel_all_btn"):
            self.sel_all_btn.setText(t("selective.btn_select_all"))
        if hasattr(self, "sel_desel_btn"):
            self.sel_desel_btn.setText(t("selective.btn_deselect_all"))
        if hasattr(self, "refresh_btn"):
            self.refresh_btn.setText(t("selective.btn_refresh"))
        if hasattr(self, "ctrl_title"):
            self.ctrl_title.setText(t("selective.step2_title"))
        if hasattr(self, "ctrl_desc"):
            self.ctrl_desc.setText(t("selective.step2_desc"))
        if hasattr(self, "timed_hdr"):
            self.timed_hdr.setText(t("selective.timed_hdr"))
        if hasattr(self, "sel_step_minus"):
            self.sel_step_minus.setToolTip(t("selective.step_minus_tooltip"))
        if hasattr(self, "sel_duration_spin"):
            self.sel_duration_spin.setSuffix(t("selective.spin_suffix"))
        if hasattr(self, "sel_step_plus"):
            self.sel_step_plus.setToolTip(t("selective.step_plus_tooltip"))
        if hasattr(self, "indef_hdr"):
            self.indef_hdr.setText(t("selective.indef_hdr"))
        if hasattr(self, "indef_desc"):
            self.indef_desc.setText(t("selective.indef_desc"))

        self.update_selective_summary()
        self.render_selective_domains_list()

