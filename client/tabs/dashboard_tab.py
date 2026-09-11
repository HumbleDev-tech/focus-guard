"""Focus-Guard Dashboard Tab Component.

Encapsulates the hero status card, Pomodoro/focus controls, and telemetry summary.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from client.utils import format_human_time


class DashboardTab(QWidget):
    """Tab widget for active protection status, Pomodoro controls, and telemetry."""

    focus_session_requested = pyqtSignal(int)
    primary_action_clicked = pyqtSignal()
    secondary_action_clicked = pyqtSignal()
    stop_focus_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._setup_ui()

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
        self.btn_pomodoro_25.setMinimumHeight(38)
        self.btn_pomodoro_25.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pomodoro_25.clicked.connect(lambda: self.focus_session_requested.emit(25))
        grid.addWidget(self.btn_pomodoro_25, 0, 0)

        self.btn_pomodoro_50 = QPushButton("Trabajo Profundo (50 min)")
        self.btn_pomodoro_50.setObjectName("secondaryBtn")
        self.btn_pomodoro_50.setMinimumHeight(38)
        self.btn_pomodoro_50.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_pomodoro_50.clicked.connect(lambda: self.focus_session_requested.emit(50))
        grid.addWidget(self.btn_pomodoro_50, 0, 1)

        self.btn_primary_action = QPushButton("Bloquear Ahora")
        self.btn_primary_action.setObjectName("primaryBtn")
        self.btn_primary_action.setMinimumHeight(38)
        self.btn_primary_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_primary_action.clicked.connect(self.primary_action_clicked.emit)
        grid.addWidget(self.btn_primary_action, 1, 0)

        self.btn_secondary_action = QPushButton("Pausa Temporal (15 min)")
        self.btn_secondary_action.setObjectName("secondaryBtn")
        self.btn_secondary_action.setMinimumHeight(38)
        self.btn_secondary_action.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_secondary_action.clicked.connect(self.secondary_action_clicked.emit)
        grid.addWidget(self.btn_secondary_action, 1, 1)

        act_box.addLayout(grid)

        # Stop manual focus button
        self.btn_stop_focus = QPushButton("Finalizar Sesión de Enfoque")
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

        telem_title = QLabel("Resumen de Configuración")
        telem_title.setObjectName("sectionHeader")
        self.telemetry_box.addWidget(telem_title)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)

        # KPI 1: Dominios Protegidos
        kpi_dom = QFrame()
        kpi_dom.setObjectName("kpiCard")
        kpi_dom_layout = QVBoxLayout(kpi_dom)
        kpi_dom_layout.setContentsMargins(10, 8, 10, 8)
        kpi_dom_layout.setSpacing(2)
        lbl_dom_title = QLabel("SITIOS PROTEGIDOS")
        lbl_dom_title.setObjectName("kpiTitle")
        self.kpi_domains_val = QLabel("0 dominios")
        self.kpi_domains_val.setObjectName("kpiValue")
        kpi_dom_layout.addWidget(lbl_dom_title)
        kpi_dom_layout.addWidget(self.kpi_domains_val)
        kpi_row.addWidget(kpi_dom)

        # KPI 2: Toque de Queda
        kpi_curf = QFrame()
        kpi_curf.setObjectName("kpiCard")
        kpi_curf_layout = QVBoxLayout(kpi_curf)
        kpi_curf_layout.setContentsMargins(10, 8, 10, 8)
        kpi_curf_layout.setSpacing(2)
        lbl_curf_title = QLabel("TOQUE DE QUEDA")
        lbl_curf_title.setObjectName("kpiTitle")
        self.kpi_curfew_val = QLabel("23:15 a 07:00")
        self.kpi_curfew_val.setObjectName("kpiValue")
        kpi_curf_layout.addWidget(lbl_curf_title)
        kpi_curf_layout.addWidget(self.kpi_curfew_val)
        kpi_row.addWidget(kpi_curf)

        # KPI 3: Cooldown Inicio
        kpi_boot = QFrame()
        kpi_boot.setObjectName("kpiCard")
        kpi_boot_layout = QVBoxLayout(kpi_boot)
        kpi_boot_layout.setContentsMargins(10, 8, 10, 8)
        kpi_boot_layout.setSpacing(2)
        lbl_boot_title = QLabel("COOLDOWN INICIO")
        lbl_boot_title.setObjectName("kpiTitle")
        self.kpi_boot_val = QLabel("30 minutos")
        self.kpi_boot_val.setObjectName("kpiValue")
        kpi_boot_layout.addWidget(lbl_boot_title)
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
        if res.get("status") != "ok":
            self.dash_state_pill.setText("DESCONECTADO")
            self.dash_state_pill.setStyleSheet(
                "border: 1px solid #30363D; color: #8B949E; font-size: 10px; font-weight: 700; "
                "padding: 3px 10px; border-radius: 12px; background-color: rgba(110, 118, 129, 0.12);"
            )
            self.dash_state_title.setText("Servicio Fuera de Línea")
            self.dash_countdown_lbl.setText("Inactivo")
            self.dash_countdown_lbl.setStyleSheet(
                "font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; "
                "font-size: 20px; font-weight: 700; color: #8B949E;"
            )
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
        self.kpi_domains_val.setText(f"{domains_cnt} dominios")
        curfew = config_data.get("curfew", {})
        curfew_str = (
            f"{curfew.get('start_time', '23:15')} a {curfew.get('end_time', '07:00')}"
            if curfew.get("enabled")
            else "Desactivado"
        )
        self.kpi_curfew_val.setText(curfew_str)
        boot = config_data.get("boot_cooldown", {})
        boot_str = (
            f"{boot.get('duration_minutes', 30)}m (Activo)"
            if (reason == "BOOT_COOLDOWN")
            else (f"{boot.get('duration_minutes', 30)}m" if boot.get("enabled") else "Desactivado")
        )
        self.kpi_boot_val.setText(boot_str)

        # 1. State: UNLOCKED / FREE TIME
        if state == "UNLOCKED":
            self.dash_state_pill.setText("MODO LIBRE")
            self.dash_state_pill.setStyleSheet(
                "border: 1px solid #2EA043; color: #3FB950; font-size: 10px; font-weight: 700; "
                "padding: 3px 10px; border-radius: 12px; background-color: rgba(46, 160, 67, 0.12);"
            )
            self.dash_state_title.setText("Modo Libre (Navegación Abierta)")
            self.dash_countdown_lbl.setText("Sitios Desbloqueados")
            self.dash_countdown_lbl.setStyleSheet(
                "font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; "
                "font-size: 20px; font-weight: 700; color: #3FB950;"
            )
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

        # 2. State: BYPASS / BREAK
        elif state == "BYPASS":
            self.dash_state_pill.setText("PAUSA TEMPORAL")
            self.dash_state_pill.setStyleSheet(
                "border: 1px solid #D29922; color: #E3B341; font-size: 10px; font-weight: 700; "
                "padding: 3px 10px; border-radius: 12px; background-color: rgba(210, 153, 34, 0.12);"
            )
            self.dash_state_title.setText("Pausa Temporal Activa")
            self.dash_countdown_lbl.setText(f"{human_time}")
            self.dash_countdown_lbl.setStyleSheet(
                "font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; "
                "font-size: 22px; font-weight: 700; color: #E3B341;"
            )
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
                self.dash_state_pill.setText("NOCHE PROTEGIDA")
                self.dash_state_pill.setStyleSheet(
                    "border: 1px solid #8957E5; color: #D2A8FF; font-size: 10px; font-weight: 700; "
                    "padding: 3px 10px; border-radius: 12px; background-color: rgba(137, 87, 229, 0.12);"
                )
                self.dash_state_title.setText("Toque de Queda Nocturno")
                self.dash_desc_lbl.setText(f"Protección nocturna activa hasta las {target}.")
                self.dash_countdown_lbl.setStyleSheet(
                    "font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; "
                    "font-size: 22px; font-weight: 700; color: #D2A8FF;"
                )
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

                if curfew_emerg_enabled:
                    self.btn_secondary_action.setText("Desbloqueo de Emergencia")
                    self.btn_secondary_action.setEnabled(True)
                    self.btn_secondary_action.setToolTip("Solicitar 15 minutos de emergencia mediante frase de seguridad.")
                else:
                    self.btn_secondary_action.setText("Descanso Desactivado")
                    self.btn_secondary_action.setEnabled(False)
                    self.btn_secondary_action.setToolTip("Los descansos nocturnos están deshabilitados. Puedes habilitar la opción de emergencia en Horarios y Reglas.")

            elif reason == "BOOT_COOLDOWN":
                self.dash_state_pill.setText("BOOT FOCUS")
                self.dash_state_pill.setStyleSheet(
                    "border: 1px solid #388BFD; color: #58A6FF; font-size: 10px; font-weight: 700; "
                    "padding: 3px 10px; border-radius: 12px; background-color: rgba(56, 139, 253, 0.12);"
                )
                self.dash_state_title.setText("Cooldown de Arranque")
                self.dash_desc_lbl.setText(f"Protección de inicio activa hasta las {target}.")
                self.dash_countdown_lbl.setStyleSheet(
                    "font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; "
                    "font-size: 22px; font-weight: 700; color: #58A6FF;"
                )
                total_boot = max(1, config_data.get("boot_cooldown", {}).get("duration_minutes", 30) * 60)
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
                self.dash_state_pill.setText("ENFOQUE MANUAL")
                self.dash_state_pill.setStyleSheet(
                    "border: 1px solid #388BFD; color: #58A6FF; font-size: 10px; font-weight: 700; "
                    "padding: 3px 10px; border-radius: 12px; background-color: rgba(56, 139, 253, 0.12);"
                )
                self.dash_state_title.setText("Modo Focus / Pomodoro")
                self.dash_desc_lbl.setText("Sesión de concentración manual en curso.")
                self.dash_countdown_lbl.setStyleSheet(
                    "font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; "
                    "font-size: 22px; font-weight: 700; color: #58A6FF;"
                )
                self.dash_progress_bar.setValue(100)
                self.dash_progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #388BFD; }")
                self.btn_stop_focus.setVisible(True)
                self.btn_stop_focus.setText("Finalizar Sesión de Enfoque")
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
                is_indef = res.get("is_indefinite", False)
                self.dash_state_pill.setText("INDEFINIDO" if is_indef else "TEMPORAL")
                self.dash_state_pill.setStyleSheet(
                    "border: 1px solid #388BFD; color: #58A6FF; font-size: 10px; font-weight: 700; "
                    "padding: 3px 10px; border-radius: 12px; background-color: rgba(56, 139, 253, 0.12);"
                )
                self.dash_state_title.setText(f"Bloqueo Selectivo ({sel_count} sitios)")
                self.dash_desc_lbl.setText(f"Bloqueo específico activo para {sel_count} dominios seleccionados.")
                self.dash_countdown_lbl.setStyleSheet(
                    "font-family: ui-monospace, SFMono-Regular, 'JetBrains Mono', monospace; "
                    "font-size: 22px; font-weight: 700; color: #58A6FF;"
                )
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
                self.dash_progress_bar.setVisible(True)
            else:
                self.dash_countdown_lbl.setText("Protección Activa")
                self.dash_progress_bar.setVisible(False)
