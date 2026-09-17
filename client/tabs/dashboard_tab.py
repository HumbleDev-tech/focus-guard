"""Focus-Guard Dashboard Tab Component.

Encapsulates the hero status card, Pomodoro/focus controls, and telemetry summary.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPalette
from client.utils import format_human_time
from client.icons import get_themed_icon
from client.i18n import t


class DashboardTab(QWidget):
    """Tab widget for active protection status, Pomodoro controls, and telemetry."""

    focus_session_requested = pyqtSignal(int)
    primary_action_clicked = pyqtSignal()
    secondary_action_clicked = pyqtSignal()
    stop_focus_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.last_status_args = None
        self._setup_ui()

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
        self.btn_pomodoro_25.setIcon(get_themed_icon("timer", is_dark, size=16))
        self.btn_pomodoro_50.setIcon(get_themed_icon("zap", is_dark, size=16))
        self.btn_primary_action.setIcon(get_themed_icon("lock", is_dark, role="white", size=16))
        self.btn_secondary_action.setIcon(get_themed_icon("coffee", is_dark, size=16))
        self.btn_stop_focus.setIcon(get_themed_icon("unlock", is_dark, role="white", size=16))

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 1. Hero Status Card with Progress Bar
        self.hero_card = QFrame()
        self.hero_card.setObjectName("heroCard")
        hero_layout = QVBoxLayout(self.hero_card)
        hero_layout.setSpacing(8)

        top_row = QHBoxLayout()
        self.dash_state_title = QLabel(t("dash.state_title"))
        self.dash_state_title.setObjectName("sectionHeader")
        top_row.addWidget(self.dash_state_title)
        top_row.addStretch()

        self.dash_state_pill = QLabel(t("dash.status_free"))
        self.dash_state_pill.setObjectName("statusBadge")
        top_row.addWidget(self.dash_state_pill)
        hero_layout.addLayout(top_row)

        self.dash_countdown_lbl = QLabel(t("dash.calculating"))
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

        self.act_title = QLabel(t("dash.sessions_title"))
        self.act_title.setObjectName("sectionHeader")
        act_box.addWidget(self.act_title)

        grid = QGridLayout()
        grid.setSpacing(8)

        self.btn_pomodoro_25 = QPushButton(t("dash.btn_pomodoro_25"))
        self.btn_pomodoro_25.setObjectName("secondaryBtn")
        self.btn_pomodoro_25.setMinimumHeight(38)
        self.btn_pomodoro_25.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pomodoro_25.clicked.connect(lambda: self.focus_session_requested.emit(25))
        grid.addWidget(self.btn_pomodoro_25, 0, 0)

        self.btn_pomodoro_50 = QPushButton(t("dash.btn_pomodoro_50"))
        self.btn_pomodoro_50.setObjectName("secondaryBtn")
        self.btn_pomodoro_50.setMinimumHeight(38)
        self.btn_pomodoro_50.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pomodoro_50.clicked.connect(lambda: self.focus_session_requested.emit(50))
        grid.addWidget(self.btn_pomodoro_50, 0, 1)

        self.btn_primary_action = QPushButton(t("dash.btn_lock_now"))
        self.btn_primary_action.setObjectName("primaryBtn")
        self.btn_primary_action.setMinimumHeight(38)
        self.btn_primary_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_primary_action.clicked.connect(self.primary_action_clicked.emit)
        grid.addWidget(self.btn_primary_action, 1, 0)

        self.btn_secondary_action = QPushButton(t("dash.btn_pause_15"))
        self.btn_secondary_action.setObjectName("secondaryBtn")
        self.btn_secondary_action.setMinimumHeight(38)
        self.btn_secondary_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_secondary_action.clicked.connect(self.secondary_action_clicked.emit)
        grid.addWidget(self.btn_secondary_action, 1, 1)

        act_box.addLayout(grid)

        # Stop manual focus button
        self.btn_stop_focus = QPushButton(t("dash.btn_stop_focus"))
        self.btn_stop_focus.setObjectName("dangerBtn")
        self.btn_stop_focus.setMinimumHeight(38)
        self.btn_stop_focus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop_focus.setVisible(False)
        self.btn_stop_focus.clicked.connect(self.stop_focus_clicked.emit)
        act_box.addWidget(self.btn_stop_focus)

        layout.addLayout(act_box)

        # 3. Telemetry / Active Rules Summary KPI Cards
        self.telemetry_box = QVBoxLayout()
        self.telemetry_box.setSpacing(8)

        self.telem_title = QLabel(t("dash.kpi_section_title"))
        self.telem_title.setObjectName("sectionHeader")
        self.telemetry_box.addWidget(self.telem_title)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)

        # KPI 1: Dominios Protegidos
        kpi_dom = QFrame()
        kpi_dom.setObjectName("kpiCard")
        kpi_dom_layout = QVBoxLayout(kpi_dom)
        kpi_dom_layout.setContentsMargins(10, 8, 10, 8)
        kpi_dom_layout.setSpacing(2)
        self.lbl_dom_title = QLabel(t("dash.kpi_protected_sites"))
        self.lbl_dom_title.setObjectName("kpiTitle")
        self.kpi_domains_val = QLabel(t("dash.kpi_domains_val", count=0))
        self.kpi_domains_val.setObjectName("kpiValue")
        kpi_dom_layout.addWidget(self.lbl_dom_title)
        kpi_dom_layout.addWidget(self.kpi_domains_val)
        kpi_row.addWidget(kpi_dom)

        # KPI 2: Toque de Queda
        kpi_curf = QFrame()
        kpi_curf.setObjectName("kpiCard")
        kpi_curf_layout = QVBoxLayout(kpi_curf)
        kpi_curf_layout.setContentsMargins(10, 8, 10, 8)
        kpi_curf_layout.setSpacing(2)
        self.lbl_curf_title = QLabel(t("dash.kpi_curfew"))
        self.lbl_curf_title.setObjectName("kpiTitle")
        self.kpi_curfew_val = QLabel("23:15 a 07:00")
        self.kpi_curfew_val.setObjectName("kpiValue")
        kpi_curf_layout.addWidget(self.lbl_curf_title)
        kpi_curf_layout.addWidget(self.kpi_curfew_val)
        kpi_row.addWidget(kpi_curf)

        # KPI 3: Cooldown Inicio
        kpi_boot = QFrame()
        kpi_boot.setObjectName("kpiCard")
        kpi_boot_layout = QVBoxLayout(kpi_boot)
        kpi_boot_layout.setContentsMargins(10, 8, 10, 8)
        kpi_boot_layout.setSpacing(2)
        self.lbl_boot_title = QLabel(t("dash.kpi_boot_cooldown"))
        self.lbl_boot_title.setObjectName("kpiTitle")
        self.kpi_boot_val = QLabel(t("dash.kpi_boot_val", mins=30))
        self.kpi_boot_val.setObjectName("kpiValue")
        kpi_boot_layout.addWidget(self.lbl_boot_title)
        kpi_boot_layout.addWidget(self.kpi_boot_val)
        kpi_row.addWidget(kpi_boot)

        self.telemetry_box.addLayout(kpi_row)
        layout.addLayout(self.telemetry_box)

        # Legacy label references for backward compatibility
        self.telem_domains_lbl = self.kpi_domains_val
        self.telem_curfew_lbl = self.kpi_curfew_val
        self.telem_boot_lbl = self.kpi_boot_val

        # Action feedback label
        self.dash_feedback_lbl = QLabel("")
        self.dash_feedback_lbl.setStyleSheet("font-size: 11px; color: #2EA043; font-weight: 600;")
        layout.addWidget(self.dash_feedback_lbl)

        layout.addStretch()
        self.update_icons()

    def show_feedback(self, message: str, timeout_ms: int = 3000):
        """Displays temporary feedback text."""
        self.dash_feedback_lbl.setText(message)
        QTimer.singleShot(timeout_ms, lambda: self.dash_feedback_lbl.setText(""))

    def update_status(
        self,
        res: dict,
        config_data: dict,
        blocked_domains_count: int = 0,
        curfew_emerg_enabled: bool = False
    ):
        """Updates all dashboard elements based on the daemon status."""
        self.last_status_args = (res, config_data, blocked_domains_count, curfew_emerg_enabled)

        if res.get("status") != "ok":
            self.dash_state_pill.setText(t("dash.pill_offline"))
            self.dash_state_pill.setStyleSheet(
                "border: 1px solid #30363D; color: #8B949E; font-size: 10px; font-weight: 700; "
                "padding: 3px 10px; border-radius: 12px; background-color: rgba(110, 118, 129, 0.12);"
            )
            self.dash_state_title.setText(t("dash.offline_title"))
            self.dash_countdown_lbl.setText(t("dash.offline_countdown"))
            self.dash_countdown_lbl.setStyleSheet(
                "font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; "
                "font-size: 20px; font-weight: 700; color: #8B949E;"
            )
            self.dash_desc_lbl.setText(t("dash.offline_desc"))
            self.dash_progress_bar.setValue(0)
            self.btn_primary_action.setEnabled(False)
            self.btn_primary_action.setToolTip(t("dash.offline_tooltip"))
            self.btn_pomodoro_25.setEnabled(False)
            self.btn_pomodoro_25.setToolTip(t("dash.offline_tooltip"))
            self.btn_pomodoro_50.setEnabled(False)
            self.btn_pomodoro_50.setToolTip(t("dash.offline_tooltip"))
            self.btn_secondary_action.setEnabled(False)
            self.btn_secondary_action.setToolTip(t("dash.offline_tooltip"))
            self.btn_stop_focus.setVisible(False)
            return

        state = res.get("state", "UNLOCKED")
        reason = res.get("reason", "FREE_TIME")
        rem = res.get("remaining_seconds", 0)
        target = res.get("target_time_str", "")
        is_blocking = res.get("is_blocking", False)
        bypasses_enabled = res.get("bypasses_enabled", True)
        domains_cnt = res.get("domains_count", blocked_domains_count)

        human_time = format_human_time(rem)

        # Update Telemetry Widget
        self.kpi_domains_val.setText(t("dash.kpi_domains_val", count=domains_cnt))
        curfew = config_data.get("curfew", {})
        curfew_str = (
            t("dash.kpi_curfew_val", start=curfew.get('start_time', '23:15'), end=curfew.get('end_time', '07:00'))
            if curfew.get("enabled")
            else t("dash.disabled")
        )
        self.kpi_curfew_val.setText(curfew_str)
        boot = config_data.get("boot_cooldown", {})
        boot_str = (
            t("dash.kpi_boot_active", mins=boot.get('duration_minutes', 30))
            if (reason == "BOOT_COOLDOWN")
            else (t("dash.kpi_boot_val", mins=boot.get('duration_minutes', 30)) if boot.get("enabled") else t("dash.disabled"))
        )
        self.kpi_boot_val.setText(boot_str)

        # 1. State: UNLOCKED / FREE TIME
        if state == "UNLOCKED":
            self.dash_state_pill.setText(t("dash.pill_free"))
            self.dash_state_pill.setStyleSheet(
                "border: 1px solid #2EA043; color: #3FB950; font-size: 10px; font-weight: 700; "
                "padding: 3px 10px; border-radius: 12px; background-color: rgba(46, 160, 67, 0.12);"
            )
            self.dash_state_title.setText(t("dash.state_unlocked_title"))
            self.dash_countdown_lbl.setText(t("dash.state_unlocked_countdown"))
            self.dash_countdown_lbl.setStyleSheet(
                "font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; "
                "font-size: 20px; font-weight: 700; color: #3FB950;"
            )
            self.dash_desc_lbl.setText(t("dash.state_unlocked_desc"))
            self.dash_progress_bar.setValue(0)
            self.dash_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #2EA043; }")
            self.btn_stop_focus.setVisible(False)

            self.btn_primary_action.setText(t("dash.btn_lock_now"))
            self.btn_primary_action.setEnabled(True)
            self.btn_primary_action.setToolTip(t("dash.btn_lock_now"))
            self.btn_pomodoro_25.setEnabled(True)
            self.btn_pomodoro_25.setToolTip(t("dash.btn_pomodoro_25"))
            self.btn_pomodoro_50.setEnabled(True)
            self.btn_pomodoro_50.setToolTip(t("dash.btn_pomodoro_50"))
            self.btn_secondary_action.setText(t("dash.btn_pause_15"))
            self.btn_secondary_action.setEnabled(False)
            self.btn_secondary_action.setToolTip(t("dash.btn_break_disabled"))

        # 2. State: BYPASS / BREAK
        elif state == "BYPASS":
            self.dash_state_pill.setText(t("dash.pill_pause"))
            self.dash_state_pill.setStyleSheet(
                "border: 1px solid #D29922; color: #E3B341; font-size: 10px; font-weight: 700; "
                "padding: 3px 10px; border-radius: 12px; background-color: rgba(210, 153, 34, 0.12);"
            )
            self.dash_state_title.setText(t("dash.state_bypass_title"))
            self.dash_countdown_lbl.setText(f"{human_time}")
            self.dash_countdown_lbl.setStyleSheet(
                "font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; "
                "font-size: 22px; font-weight: 700; color: #E3B341;"
            )
            self.dash_desc_lbl.setText(t("dash.state_bypass_desc"))
            self.dash_progress_bar.setValue(max(5, min(100, int((rem / 900) * 100))))
            self.dash_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #D29922; }")
            self.btn_stop_focus.setVisible(False)

            self.btn_primary_action.setText(t("dash.btn_end_pause"))
            self.btn_primary_action.setEnabled(True)
            self.btn_primary_action.setToolTip(t("dash.btn_end_pause"))
            self.btn_pomodoro_25.setEnabled(False)
            self.btn_pomodoro_25.setToolTip(t("dash.btn_pause_running"))
            self.btn_pomodoro_50.setEnabled(False)
            self.btn_pomodoro_50.setToolTip(t("dash.btn_pause_running"))
            self.btn_secondary_action.setText(t("dash.btn_pause_running"))
            self.btn_secondary_action.setEnabled(False)
            self.btn_secondary_action.setToolTip(t("dash.btn_pause_running"))

        # 3. State: LOCKED / ACTIVE PROTECTION
        elif is_blocking:
            if reason == "CURFEW":
                self.dash_state_pill.setText(t("dash.pill_curfew"))
                self.dash_state_pill.setStyleSheet(
                    "border: 1px solid #8957E5; color: #D2A8FF; font-size: 10px; font-weight: 700; "
                    "padding: 3px 10px; border-radius: 12px; background-color: rgba(137, 87, 229, 0.12);"
                )
                self.dash_state_title.setText(t("dash.state_curfew_title"))
                self.dash_desc_lbl.setText(t("dash.state_curfew_desc", target=target))
                self.dash_countdown_lbl.setStyleSheet(
                    "font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; "
                    "font-size: 22px; font-weight: 700; color: #D2A8FF;"
                )
                self.dash_progress_bar.setValue(100)
                self.dash_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #8957E5; }")
                self.btn_stop_focus.setVisible(False)

                self.btn_primary_action.setText(t("dash.btn_night_lock"))
                self.btn_primary_action.setEnabled(False)
                self.btn_primary_action.setToolTip(t("dash.btn_night_lock"))
                self.btn_pomodoro_25.setEnabled(False)
                self.btn_pomodoro_25.setToolTip(t("dash.btn_night_lock"))
                self.btn_pomodoro_50.setEnabled(False)
                self.btn_pomodoro_50.setToolTip(t("dash.btn_night_lock"))

                if curfew_emerg_enabled:
                    self.btn_secondary_action.setText(t("dash.btn_emergency_unlock"))
                    self.btn_secondary_action.setEnabled(True)
                    self.btn_secondary_action.setToolTip(t("dash.btn_emergency_unlock"))
                else:
                    self.btn_secondary_action.setText(t("dash.btn_break_disabled"))
                    self.btn_secondary_action.setEnabled(False)
                    self.btn_secondary_action.setToolTip(t("dash.btn_break_disabled"))

            elif reason == "BOOT_COOLDOWN":
                self.dash_state_pill.setText(t("dash.pill_boot"))
                self.dash_state_pill.setStyleSheet(
                    "border: 1px solid #388BFD; color: #58A6FF; font-size: 10px; font-weight: 700; "
                    "padding: 3px 10px; border-radius: 12px; background-color: rgba(56, 139, 253, 0.12);"
                )
                self.dash_state_title.setText(t("dash.state_boot_title"))
                self.dash_desc_lbl.setText(t("dash.state_boot_desc", target=target))
                self.dash_countdown_lbl.setStyleSheet(
                    "font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; "
                    "font-size: 22px; font-weight: 700; color: #58A6FF;"
                )
                total_boot = max(1, config_data.get("boot_cooldown", {}).get("duration_minutes", 30) * 60)
                self.dash_progress_bar.setValue(max(5, min(100, int((rem / total_boot) * 100))))
                self.dash_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #388BFD; }")
                self.btn_stop_focus.setVisible(False)

                self.btn_primary_action.setText(t("dash.btn_boot_active"))
                self.btn_primary_action.setEnabled(False)
                self.btn_primary_action.setToolTip(t("dash.btn_boot_active"))
                self.btn_pomodoro_25.setEnabled(False)
                self.btn_pomodoro_25.setToolTip(t("dash.btn_boot_active"))
                self.btn_pomodoro_50.setEnabled(False)
                self.btn_pomodoro_50.setToolTip(t("dash.btn_boot_active"))

                if bypasses_enabled:
                    self.btn_secondary_action.setText(t("dash.btn_pause_15"))
                    self.btn_secondary_action.setEnabled(True)
                    self.btn_secondary_action.setToolTip(t("dash.btn_pause_15"))
                else:
                    self.btn_secondary_action.setText(t("dash.btn_break_disabled"))
                    self.btn_secondary_action.setEnabled(False)
                    self.btn_secondary_action.setToolTip(t("dash.btn_break_disabled"))

            elif reason == "MANUAL_LOCK":
                self.dash_state_pill.setText(t("dash.pill_focus"))
                self.dash_state_pill.setStyleSheet(
                    "border: 1px solid #388BFD; color: #58A6FF; font-size: 10px; font-weight: 700; "
                    "padding: 3px 10px; border-radius: 12px; background-color: rgba(56, 139, 253, 0.12);"
                )
                self.dash_state_title.setText(t("dash.state_manual_title"))
                self.dash_desc_lbl.setText(t("dash.state_manual_desc"))
                self.dash_countdown_lbl.setStyleSheet(
                    "font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; "
                    "font-size: 22px; font-weight: 700; color: #58A6FF;"
                )
                self.dash_progress_bar.setValue(100)
                self.dash_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #388BFD; }")
                self.btn_stop_focus.setVisible(True)
                self.btn_stop_focus.setText(t("dash.btn_stop_focus"))
                self.btn_stop_focus.setToolTip(t("dash.btn_stop_focus"))

                self.btn_primary_action.setText(t("dash.btn_focus_running"))
                self.btn_primary_action.setEnabled(False)
                self.btn_primary_action.setToolTip(t("dash.btn_focus_running"))
                self.btn_pomodoro_25.setEnabled(False)
                self.btn_pomodoro_25.setToolTip(t("dash.btn_focus_running"))
                self.btn_pomodoro_50.setEnabled(False)
                self.btn_pomodoro_50.setToolTip(t("dash.btn_focus_running"))

                if bypasses_enabled:
                    self.btn_secondary_action.setText(t("dash.btn_pause_15"))
                    self.btn_secondary_action.setEnabled(True)
                    self.btn_secondary_action.setToolTip(t("dash.btn_pause_15"))
                else:
                    self.btn_secondary_action.setText(t("dash.btn_break_disabled"))
                    self.btn_secondary_action.setEnabled(False)
                    self.btn_secondary_action.setToolTip(t("dash.btn_break_disabled"))

            elif reason == "SELECTIVE_LOCK":
                sel_count = len(res.get("selective_domains", []))
                is_indef = res.get("is_indefinite", False)
                self.dash_state_pill.setText(t("dash.pill_indefinite") if is_indef else t("dash.pill_timed"))
                self.dash_state_pill.setStyleSheet(
                    "border: 1px solid #388BFD; color: #58A6FF; font-size: 10px; font-weight: 700; "
                    "padding: 3px 10px; border-radius: 12px; background-color: rgba(56, 139, 253, 0.12);"
                )
                self.dash_state_title.setText(t("dash.state_selective_title", count=sel_count))
                self.dash_desc_lbl.setText(t("dash.state_selective_desc", count=sel_count))
                self.dash_countdown_lbl.setStyleSheet(
                    "font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; "
                    "font-size: 22px; font-weight: 700; color: #58A6FF;"
                )
                self.dash_progress_bar.setValue(100)
                self.dash_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #388BFD; }")
                self.btn_stop_focus.setVisible(True)
                self.btn_stop_focus.setText(t("dash.btn_end_selective"))
                self.btn_stop_focus.setToolTip(t("dash.btn_end_selective"))

                self.btn_primary_action.setText(t("dash.btn_lock_running"))
                self.btn_primary_action.setEnabled(False)
                self.btn_pomodoro_25.setEnabled(False)
                self.btn_pomodoro_50.setEnabled(False)

                if bypasses_enabled:
                    self.btn_secondary_action.setText(t("dash.btn_pause_15"))
                    self.btn_secondary_action.setEnabled(True)
                    self.btn_secondary_action.setToolTip(t("dash.btn_pause_15"))
                else:
                    self.btn_secondary_action.setText(t("dash.btn_break_disabled"))
                    self.btn_secondary_action.setEnabled(False)
                    self.btn_secondary_action.setToolTip(t("dash.btn_break_disabled"))

            if rem > 0:
                self.dash_countdown_lbl.setText(f"{human_time}")
                self.dash_progress_bar.setVisible(True)
            else:
                self.dash_countdown_lbl.setText(t("dash.active_protection"))
                self.dash_progress_bar.setVisible(False)

    def retranslate_ui(self):
        """Retranslates all static text in Dashboard tab."""
        if hasattr(self, "act_title"):
            self.act_title.setText(t("dash.sessions_title"))
        if hasattr(self, "btn_pomodoro_25"):
            self.btn_pomodoro_25.setText(t("dash.btn_pomodoro_25"))
        if hasattr(self, "btn_pomodoro_50"):
            self.btn_pomodoro_50.setText(t("dash.btn_pomodoro_50"))
        if hasattr(self, "telem_title"):
            self.telem_title.setText(t("dash.kpi_section_title"))
        if hasattr(self, "lbl_dom_title"):
            self.lbl_dom_title.setText(t("dash.kpi_protected_sites"))
        if hasattr(self, "lbl_curf_title"):
            self.lbl_curf_title.setText(t("dash.kpi_curfew"))
        if hasattr(self, "lbl_boot_title"):
            self.lbl_boot_title.setText(t("dash.kpi_boot_cooldown"))

        if self.last_status_args is not None:
            self.update_status(*self.last_status_args)

