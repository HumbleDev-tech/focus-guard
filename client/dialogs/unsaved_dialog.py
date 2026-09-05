"""
Focus-Guard Unsaved Changes Dialog
Modern modal asking to save unsaved rule changes before closing.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
)
from PyQt6.QtCore import Qt

from client.theme import apply_dialog_theme


class UnsavedChangesDialog(QDialog):
    """Modern modal asking to save unsaved rule changes before closing."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.action = "cancel"  # 'save', 'discard', 'cancel'
        self.setWindowTitle("Cambios sin guardar")
        self.setFixedWidth(420)
        apply_dialog_theme(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("¿Guardar cambios antes de salir?")
        title.setObjectName("sectionHeader")
        layout.addWidget(title)

        desc = QLabel("Has modificado horarios o reglas del sistema. Si sales sin guardar, los cambios se descartarán.")
        desc.setObjectName("cardDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.on_cancel)
        btn_row.addWidget(cancel_btn)

        btn_row.addStretch()

        discard_btn = QPushButton("Descartar")
        discard_btn.setObjectName("dangerBtn")
        discard_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        discard_btn.clicked.connect(self.on_discard)
        btn_row.addWidget(discard_btn)

        save_btn = QPushButton("Guardar y Salir")
        save_btn.setObjectName("primaryBtn")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
