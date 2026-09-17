"""
Focus-Guard Confirm Domain Removal Dialog
Friction modal to prevent impulsive deletion of blocked sites during active protection.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFrame, QApplication
)
from PyQt6.QtCore import Qt, QTimer

from client.theme import apply_dialog_theme
from client.icons import get_themed_icon
from client.i18n import t


class ConfirmDomainRemovalDialog(QDialog):
    """Friction modal to prevent impulsive deletion of blocked sites during active protection."""
    def __init__(self, domain: str, reason_str: str, phrase: str, parent=None):
        super().__init__(parent)
        self.domain = domain
        self.phrase = phrase.strip()
        self.confirmed = False

        self.setWindowTitle(t("dialog.confirm_removal_title"))
        self.setMinimumWidth(440)
        apply_dialog_theme(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(t("dialog.confirm_removal_header"))
        title.setObjectName("sectionHeader")
        layout.addWidget(title)

        desc = QLabel(t("dialog.confirm_removal_desc", reason=reason_str, domain=self.domain))
        desc.setObjectName("cardDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        if self.phrase:
            instruction = QLabel(t("dialog.confirm_removal_instruction"))
            instruction.setObjectName("fieldLabel")
            instruction.setWordWrap(True)
            layout.addWidget(instruction)

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
            self.input_field.setPlaceholderText(t("dialog.confirm_removal_input_placeholder"))
            self.input_field.returnPressed.connect(self.on_confirm)
            layout.addWidget(self.input_field)
        else:
            self.input_field = None

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton(t("dialog.confirm_removal_btn_cancel"))
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        del_btn = QPushButton(t("dialog.confirm_removal_btn_delete", domain=self.domain))
        del_btn.setObjectName("dangerBtn")
        del_btn.setIcon(get_themed_icon("trash-2", role="white", size=14))
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        del_btn.clicked.connect(self.on_confirm)
        btn_row.addWidget(del_btn)

        layout.addLayout(btn_row)

    def on_copy_phrase(self):
        QApplication.clipboard().setText(self.phrase)
        if hasattr(self, "copy_btn"):
            self.copy_btn.setText(t("dialog.confirm_removal_copied"))
            QTimer.singleShot(2000, lambda: self.copy_btn.setText(t("dialog.confirm_removal_btn_copy")))
        if hasattr(self, "input_field") and self.input_field:
            self.input_field.setFocus()

    def on_confirm(self):
        if self.input_field:
            entered = self.input_field.text().strip().lower()
            if entered == self.phrase.lower():
                self.confirmed = True
                self.accept()
            else:
                self.input_field.setStyleSheet("border: 1px solid #DA3633;")
        else:
            self.confirmed = True
            self.accept()

