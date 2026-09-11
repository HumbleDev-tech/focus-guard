"""
Focus-Guard Rules Tab Component
Manages Boot Focus cooldown, Night Curfew, Bypasses & Emergency phrases, and Autostart.
"""
from typing import Dict, Any, Tuple

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QScrollArea, QFrame, QCheckBox, QTimeEdit, QSpinBox, QApplication
)
from PyQt6.QtCore import Qt, QTime, QTimer, pyqtSignal

from client.autostart import is_autostart_enabled, set_autostart_enabled


class RulesTab(QWidget):
    """Component managing the Horarios y Reglas (Schedules & Rules) tab."""
    rules_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initial_config: Dict[str, Any] = {}

        self.setup_ui()

    def setup_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

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

        self.boot_dur_label = QLabel("Duración inicial:")
        self.boot_dur_label.setObjectName("fieldLabel")
        dur_row.addWidget(self.boot_dur_label)

        self.boot_step_minus = QPushButton("−")
        self.boot_step_minus.setObjectName("stepBtn")
        self.boot_step_minus.setToolTip("Disminuir 5 minutos")
        self.boot_step_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boot_step_minus.clicked.connect(lambda: self.step_boot_duration(-5))
        dur_row.addWidget(self.boot_step_minus)

        self.boot_duration_spin = QSpinBox()
        self.boot_duration_spin.setRange(5, 180)
        self.boot_duration_spin.setSingleStep(5)
        self.boot_duration_spin.setSuffix(" min")
        self.boot_duration_spin.setFixedWidth(80)
        self.boot_duration_spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dur_row.addWidget(self.boot_duration_spin)

        self.boot_step_plus = QPushButton("+")
        self.boot_step_plus.setObjectName("stepBtn")
        self.boot_step_plus.setToolTip("Aumentar 5 minutos")
        self.boot_step_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.boot_step_plus.clicked.connect(lambda: self.step_boot_duration(5))
        dur_row.addWidget(self.boot_step_plus)

        dur_row.addSpacing(10)

        self.boot_presets = []
        for m in [15, 30, 45, 60]:
            pill = QPushButton(f"{m}m")
            pill.setObjectName("presetChipSmall")
            pill.setCursor(Qt.CursorShape.PointingHandCursor)
            pill.clicked.connect(lambda _, mins=m: self.boot_duration_spin.setValue(mins))
            dur_row.addWidget(pill)
            self.boot_presets.append(pill)

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

        self.curfew_start_lbl = QLabel("Bloquear desde:")
        self.curfew_start_lbl.setObjectName("fieldLabel")
        time_row.addWidget(self.curfew_start_lbl)

        self.curfew_start_minus = QPushButton("−")
        self.curfew_start_minus.setObjectName("stepBtn")
        self.curfew_start_minus.setToolTip("Restar 15 minutos")
        self.curfew_start_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.curfew_start_minus.clicked.connect(lambda: self.step_curfew_start(-15))
        time_row.addWidget(self.curfew_start_minus)

        self.curfew_start_time = QTimeEdit()
        self.curfew_start_time.setDisplayFormat("HH:mm")
        self.curfew_start_time.setFixedWidth(75)
        self.curfew_start_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.curfew_start_time.timeChanged.connect(self.update_curfew_summary)
        time_row.addWidget(self.curfew_start_time)

        self.curfew_start_plus = QPushButton("+")
        self.curfew_start_plus.setObjectName("stepBtn")
        self.curfew_start_plus.setToolTip("Sumar 15 minutos")
        self.curfew_start_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.curfew_start_plus.clicked.connect(lambda: self.step_curfew_start(15))
        time_row.addWidget(self.curfew_start_plus)

        time_row.addSpacing(14)

        self.curfew_end_lbl = QLabel("Hasta las:")
        self.curfew_end_lbl.setObjectName("fieldLabel")
        time_row.addWidget(self.curfew_end_lbl)

        self.curfew_end_minus = QPushButton("−")
        self.curfew_end_minus.setObjectName("stepBtn")
        self.curfew_end_minus.setToolTip("Restar 15 minutos")
        self.curfew_end_minus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.curfew_end_minus.clicked.connect(lambda: self.step_curfew_end(-15))
        time_row.addWidget(self.curfew_end_minus)

        self.curfew_end_time = QTimeEdit()
        self.curfew_end_time.setDisplayFormat("HH:mm")
        self.curfew_end_time.setFixedWidth(75)
        self.curfew_end_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.curfew_end_time.timeChanged.connect(self.update_curfew_summary)
        time_row.addWidget(self.curfew_end_time)

        self.curfew_end_plus = QPushButton("+")
        self.curfew_end_plus.setObjectName("stepBtn")
        self.curfew_end_plus.setToolTip("Sumar 15 minutos")
        self.curfew_end_plus.setCursor(Qt.CursorShape.PointingHandCursor)
        self.curfew_end_plus.clicked.connect(lambda: self.step_curfew_end(15))
        time_row.addWidget(self.curfew_end_plus)

        time_row.addStretch()
        curfew_layout.addLayout(time_row)

        # Dynamic human summary pill
        self.curfew_summary_lbl = QLabel("")
        self.curfew_summary_lbl.setObjectName("summaryPill")
        curfew_layout.addWidget(self.curfew_summary_lbl)

        # Quick schedule preset pills
        sched_row = QHBoxLayout()
        sched_row.setSpacing(6)
        self.curfew_sched_lbl = QLabel("Horarios habituales:")
        self.curfew_sched_lbl.setStyleSheet("font-size: 11px; color: #8B949E; font-weight: 500;")
        sched_row.addWidget(self.curfew_sched_lbl)

        curfew_presets = [
            ("23:00 a 07:00", (23, 0), (7, 0)),
            ("23:30 a 07:30", (23, 30), (7, 30)),
            ("00:00 a 08:00", (0, 0), (8, 0)),
            ("01:00 a 07:00", (1, 0), (7, 0))
        ]
        self.curfew_presets_btns = []
        for p_title, p_start, p_end in curfew_presets:
            p_btn = QPushButton(p_title)
            p_btn.setObjectName("presetChipSmall")
            p_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            p_btn.clicked.connect(lambda _, s=p_start, e=p_end: self.set_curfew_times(s, e))
            sched_row.addWidget(p_btn)
            self.curfew_presets_btns.append(p_btn)

        sched_row.addStretch()
        curfew_layout.addLayout(sched_row)

        self.curfew_notice_banner = QFrame()
        self.curfew_notice_banner.setObjectName("infoBanner")
        notice_layout = QHBoxLayout(self.curfew_notice_banner)
        notice_layout.setContentsMargins(10, 8, 10, 8)

        self.curfew_notice = QLabel("Aviso: Recibirás una notificación en tu escritorio 10 minutos antes del Toque de Queda para cerrar tus pestañas con calma.")
        self.curfew_notice.setObjectName("infoBannerText")
        self.curfew_notice.setWordWrap(True)
        notice_layout.addWidget(self.curfew_notice)
        curfew_layout.addWidget(self.curfew_notice_banner)

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

        emerg_container = QWidget()
        emerg_layout = QVBoxLayout(emerg_container)
        emerg_layout.setContentsMargins(20, 0, 0, 0)
        emerg_layout.setSpacing(8)

        self.curfew_emerg_cb = QCheckBox("Permitir desbloqueo de emergencia durante el Toque de Queda")
        self.curfew_emerg_cb.setStyleSheet("font-size: 12px; font-weight: 600;")
        emerg_layout.addWidget(self.curfew_emerg_cb)

        phrase_row = QHBoxLayout()
        phrase_row.setSpacing(8)

        self.emergency_phrase_lbl = QLabel("Frase de confirmación:")
        self.emergency_phrase_lbl.setObjectName("fieldLabel")
        phrase_row.addWidget(self.emergency_phrase_lbl)

        self.emergency_phrase_input = QLineEdit()
        self.emergency_phrase_input.setPlaceholderText("ej: necesito desbloqueo de emergencia")
        phrase_row.addWidget(self.emergency_phrase_input)

        self.copy_phrase_btn = QPushButton("Copiar Frase")
        self.copy_phrase_btn.setObjectName("secondaryBtn")
        self.copy_phrase_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.boot_enabled_cb.toggled.connect(self._update_boot_controls_enabled)
        self.curfew_enabled_cb.toggled.connect(self._update_curfew_controls_enabled)
        self.curfew_emerg_cb.toggled.connect(lambda: self._update_emergency_controls_enabled())

        # Notify parent on change
        self.boot_enabled_cb.toggled.connect(self.rules_changed.emit)
        self.boot_duration_spin.valueChanged.connect(self.rules_changed.emit)
        self.curfew_enabled_cb.toggled.connect(self.rules_changed.emit)
        self.curfew_start_time.timeChanged.connect(self.rules_changed.emit)
        self.curfew_end_time.timeChanged.connect(self.rules_changed.emit)
        self.bypasses_enabled_cb.toggled.connect(self.rules_changed.emit)
        self.curfew_emerg_cb.toggled.connect(self.rules_changed.emit)
        self.emergency_phrase_input.textChanged.connect(self.rules_changed.emit)

        layout.addStretch()
        scroll.setWidget(container)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroll)

    def _update_boot_controls_enabled(self, enabled: bool):
        self.boot_dur_label.setEnabled(enabled)
        self.boot_duration_spin.setEnabled(enabled)
        self.boot_step_minus.setEnabled(enabled)
        self.boot_step_plus.setEnabled(enabled)
        for p in self.boot_presets:
            p.setEnabled(enabled)

    def _update_curfew_controls_enabled(self, enabled: bool):
        self.curfew_start_lbl.setEnabled(enabled)
        self.curfew_end_lbl.setEnabled(enabled)
        self.curfew_start_minus.setEnabled(enabled)
        self.curfew_start_plus.setEnabled(enabled)
        self.curfew_end_minus.setEnabled(enabled)
        self.curfew_end_plus.setEnabled(enabled)
        self.curfew_start_time.setEnabled(enabled)
        self.curfew_end_time.setEnabled(enabled)
        self.curfew_summary_lbl.setEnabled(enabled)
        self.curfew_sched_lbl.setEnabled(enabled)
        for b in self.curfew_presets_btns:
            b.setEnabled(enabled)
        if hasattr(self, "curfew_notice_banner"):
            self.curfew_notice_banner.setEnabled(enabled)
        self.curfew_notice.setEnabled(enabled)
        self._update_emergency_controls_enabled()

    def _update_emergency_controls_enabled(self):
        curfew_on = self.curfew_enabled_cb.isChecked()
        self.curfew_emerg_cb.setEnabled(curfew_on)
        emerg_active = curfew_on and self.curfew_emerg_cb.isChecked()
        self.emergency_phrase_lbl.setEnabled(emerg_active)
        self.emergency_phrase_input.setEnabled(emerg_active)
        self.copy_phrase_btn.setEnabled(emerg_active)

    def load_rules(self, config: Dict[str, Any]):
        self.initial_config = dict(config)

        # Block signals temporarily to prevent false dirty tracking
        self.blockSignals(True)

        boot = config.get("boot_cooldown", {})
        self.boot_enabled_cb.setChecked(boot.get("enabled", True))
        self.boot_duration_spin.setValue(boot.get("duration_minutes", 30))
        self._update_boot_controls_enabled(self.boot_enabled_cb.isChecked())

        curfew = config.get("curfew", {})
        self.curfew_enabled_cb.setChecked(curfew.get("enabled", True))
        start_parts = [int(x) for x in curfew.get("start_time", "23:15").split(":")]
        end_parts = [int(x) for x in curfew.get("end_time", "07:00").split(":")]
        self.curfew_start_time.setTime(QTime(start_parts[0], start_parts[1]))
        self.curfew_end_time.setTime(QTime(end_parts[0], end_parts[1]))
        self._update_curfew_controls_enabled(self.curfew_enabled_cb.isChecked())

        bypasses = config.get("bypasses", {})
        self.bypasses_enabled_cb.setChecked(bypasses.get("enabled", True))
        self.curfew_emerg_cb.setChecked(bypasses.get("allow_during_curfew", False))
        self.emergency_phrase_input.setText(bypasses.get("emergency_phrase", "necesito desbloqueo de emergencia"))
        self._update_emergency_controls_enabled()

        self.blockSignals(False)
        self.update_curfew_summary()

    def get_rules_dict(self) -> Dict[str, Any]:
        return {
            "boot_cooldown": {
                "enabled": self.boot_enabled_cb.isChecked(),
                "duration_minutes": self.boot_duration_spin.value()
            },
            "curfew": {
                "enabled": self.curfew_enabled_cb.isChecked(),
                "start_time": self.curfew_start_time.time().toString("HH:mm"),
                "end_time": self.curfew_end_time.time().toString("HH:mm")
            },
            "bypasses": {
                "enabled": self.bypasses_enabled_cb.isChecked(),
                "allow_during_curfew": self.curfew_emerg_cb.isChecked(),
                "emergency_phrase": self.emergency_phrase_input.text().strip() or "necesito desbloqueo de emergencia"
            }
        }

    def has_unsaved_changes(self) -> bool:
        if not self.initial_config:
            return False

        current = self.get_rules_dict()
        init_boot = self.initial_config.get("boot_cooldown", {})
        if (current["boot_cooldown"]["enabled"] != init_boot.get("enabled", True) or
                current["boot_cooldown"]["duration_minutes"] != init_boot.get("duration_minutes", 30)):
            return True

        init_curfew = self.initial_config.get("curfew", {})
        if (current["curfew"]["enabled"] != init_curfew.get("enabled", True) or
                current["curfew"]["start_time"] != init_curfew.get("start_time", "23:15") or
                current["curfew"]["end_time"] != init_curfew.get("end_time", "07:00")):
            return True

        init_bypasses = self.initial_config.get("bypasses", {})
        if (current["bypasses"]["enabled"] != init_bypasses.get("enabled", True) or
                current["bypasses"]["allow_during_curfew"] != init_bypasses.get("allow_during_curfew", False) or
                current["bypasses"]["emergency_phrase"] != init_bypasses.get("emergency_phrase", "necesito desbloqueo de emergencia")):
            return True

        return False

    def step_boot_duration(self, delta: int):
        val = self.boot_duration_spin.value() + delta
        val = max(self.boot_duration_spin.minimum(), min(self.boot_duration_spin.maximum(), val))
        self.boot_duration_spin.setValue(val)

    def step_curfew_start(self, delta_minutes: int):
        cur = self.curfew_start_time.time()
        self.curfew_start_time.setTime(cur.addSecs(delta_minutes * 60))

    def step_curfew_end(self, delta_minutes: int):
        cur = self.curfew_end_time.time()
        self.curfew_end_time.setTime(cur.addSecs(delta_minutes * 60))

    def set_curfew_times(self, start_tuple: Tuple[int, int], end_tuple: Tuple[int, int]):
        self.curfew_start_time.setTime(QTime(start_tuple[0], start_tuple[1]))
        self.curfew_end_time.setTime(QTime(end_tuple[0], end_tuple[1]))

    def update_curfew_summary(self):
        s_time = self.curfew_start_time.time()
        e_time = self.curfew_end_time.time()

        # Compute span in minutes
        s_mins = s_time.hour() * 60 + s_time.minute()
        e_mins = e_time.hour() * 60 + e_time.minute()

        if e_mins >= s_mins:
            total_mins = e_mins - s_mins
        else:
            total_mins = (1440 - s_mins) + e_mins

        hours = total_mins // 60
        mins = total_mins % 60
        dur_txt = f"{hours}h {mins}m" if mins > 0 else f"{hours}h"

        s_str = s_time.toString("HH:mm")
        e_str = e_time.toString("HH:mm")

        self.curfew_summary_lbl.setText(
            f"El toque de queda bloqueará distracciones todos los días de <b>{s_str} a {e_str}</b> ({dur_txt} de descanso protegido)."
        )

    def on_autostart_toggled(self, checked: bool):
        set_autostart_enabled(checked)

    def on_copy_phrase_clicked(self):
        phrase = self.emergency_phrase_input.text().strip()
        if phrase:
            QApplication.clipboard().setText(phrase)
            self.copy_phrase_btn.setText("Copiado")
            QTimer.singleShot(2000, lambda: self.copy_phrase_btn.setText("Copiar Frase"))
