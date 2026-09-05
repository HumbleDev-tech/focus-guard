"""
Focus-Guard Unsaved Changes Dialog
Modern modal asking to save unsaved rule changes before closing.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)


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
