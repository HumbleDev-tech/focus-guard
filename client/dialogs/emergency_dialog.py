"""
Focus-Guard Emergency Prompt Dialog
Custom dialog for emergency unlock verification during active curfew.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFrame, QApplication
)
from PyQt6.QtCore import Qt, QTimer

from client.theme import apply_dialog_theme


class EmergencyPromptDialog(QDialog):
    """Custom dialog for emergency unlock verification without broken HTML."""
    def __init__(self, phrase: str, parent=None):
        super().__init__(parent)
        self.phrase = phrase.strip()
        self.confirmed = False

        self.setWindowTitle("Desbloqueo de Emergencia")
        self.setMinimumWidth(440)
        apply_dialog_theme(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Toque de Queda Nocturno Activo")
        title.setObjectName("sectionHeader")
        layout.addWidget(title)

        desc = QLabel("Para confirmar una excepción de trabajo real, escribe la frase de confirmación:")
        desc.setObjectName("cardDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        phrase_container = QFrame()
        phrase_container.setObjectName("innerCard")
        phrase_box_layout = QHBoxLayout(phrase_container)
        phrase_box_layout.setContentsMargins(10, 6, 8, 6)
        phrase_box_layout.setSpacing(10)

        phrase_box = QLabel(self.phrase)
        phrase_box.setObjectName("codePhrase")
        phrase_box.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard)
        phrase_box_layout.addWidget(phrase_box)

        phrase_box_layout.addStretch()

        self.copy_btn = QPushButton("Copiar Frase")
        self.copy_btn.setObjectName("secondaryBtn")
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        confirm_btn = QPushButton("Confirmar Desbloqueo (15 min)")
        confirm_btn.setObjectName("primaryBtn")
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
            self.input_field.setStyleSheet("border: 1px solid #DA3633;")

