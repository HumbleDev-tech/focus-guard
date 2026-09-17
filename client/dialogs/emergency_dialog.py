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
from client.icons import get_themed_icon
from client.i18n import t


class EmergencyPromptDialog(QDialog):
    """Custom dialog for emergency unlock verification without broken HTML."""
    def __init__(self, phrase: str, parent=None):
        super().__init__(parent)
        self.phrase = phrase.strip()
        self.confirmed = False

        self.setWindowTitle(t("dialog.emergency_title"))
        self.setMinimumWidth(440)
        apply_dialog_theme(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(t("dialog.emergency_header"))
        title.setObjectName("sectionHeader")
        layout.addWidget(title)

        desc = QLabel(t("dialog.emergency_desc"))
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

        self.copy_btn = QPushButton(t("dialog.confirm_removal_btn_copy"))
        self.copy_btn.setObjectName("secondaryBtn")
        self.copy_btn.setIcon(get_themed_icon("copy", role="secondary", size=14))
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.setToolTip(t("dialog.confirm_removal_btn_copy"))
        self.copy_btn.clicked.connect(self.on_copy_phrase)
        phrase_box_layout.addWidget(self.copy_btn)

        layout.addWidget(phrase_container)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(t("dialog.emergency_input_placeholder"))
        self.input_field.returnPressed.connect(self.on_confirm)
        layout.addWidget(self.input_field)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton(t("dialog.confirm_removal_btn_cancel"))
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        confirm_btn = QPushButton(t("dialog.emergency_btn_confirm"))
        confirm_btn.setObjectName("primaryBtn")
        confirm_btn.setIcon(get_themed_icon("unlock", role="white", size=15))
        confirm_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        confirm_btn.clicked.connect(self.on_confirm)
        btn_row.addWidget(confirm_btn)

        layout.addLayout(btn_row)

    def on_copy_phrase(self):
        QApplication.clipboard().setText(self.phrase)
        if hasattr(self, "copy_btn"):
            self.copy_btn.setText(t("dialog.confirm_removal_copied"))
            QTimer.singleShot(2000, lambda: self.copy_btn.setText(t("dialog.confirm_removal_btn_copy")))
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

