"""
Focus-Guard Dialogs Package
Provides modular modal dialogs for confirmation, about, and prompt screens.
"""

from client.dialogs.emergency_dialog import EmergencyPromptDialog
from client.dialogs.confirm_dialog import ConfirmDomainRemovalDialog
from client.dialogs.about_dialog import AboutDialog
from client.dialogs.unsaved_dialog import UnsavedChangesDialog

__all__ = [
    "EmergencyPromptDialog",
    "ConfirmDomainRemovalDialog",
    "AboutDialog",
    "UnsavedChangesDialog",
]
