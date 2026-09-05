"""
Focus-Guard Confirm Domain Removal Dialog
Friction modal to prevent impulsive deletion of blocked sites during active protection.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFrame, QApplication
)
from PyQt6.QtCore import Qt, QTimer


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
            QLineEdit:focus {
                border-color: #388BFD;
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
            QPushButton#secondaryBtn:hover {
                background-color: #21262D;
                border-color: #58A6FF;
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
