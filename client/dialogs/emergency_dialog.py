"""
Focus-Guard Emergency Prompt Dialog
Custom dialog for emergency unlock verification during active curfew.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFrame, QApplication
)
from PyQt6.QtCore import Qt, QTimer


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
            QLineEdit:focus {
                border-color: #388BFD;
            }
            QPushButton#primaryBtn {
                background-color: #388BFD;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton#primaryBtn:hover {
                background-color: #1F6FEB;
            }
            QPushButton#secondaryBtn {
                background-color: #161B22;
                color: #F0F6FC;
                border: 1px solid #30363D;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #21262D;
                border-color: #58A6FF;
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
