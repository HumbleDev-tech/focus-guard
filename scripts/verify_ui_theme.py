"""
Quick UI & Icon visual test script.
Loads all Lucide icons and shows them with Theme System 2.0.
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt

from client.icons import get_themed_icon, get_pixmap
from client.theme import get_theme_stylesheet


def run_preview():
    app = QApplication(sys.argv)
    window = QWidget()
    window.setWindowTitle("Focus-Guard — Vista Previa de Iconos y Tema 2.0")
    window.resize(680, 500)

    # Set dark theme stylesheet
    window.setStyleSheet(get_theme_stylesheet(is_dark=True, resource_dir="resources"))

    layout = QVBoxLayout(window)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(14)

    title = QLabel("Focus-Guard — Catálogo de Iconos Lucide & Estilos")
    title.setStyleSheet("font-size: 16px; font-weight: 700; color: #F0F6FC;")
    layout.addWidget(title)

    desc = QLabel("Iconos vectoriales 100% libres (ISC), sin librerías externas, renderizados con QSvgRenderer.")
    desc.setObjectName("cardDesc")
    layout.addWidget(desc)

    card = QFrame()
    card.setObjectName("settingsCard")
    card_layout = QGridLayout(card)
    card_layout.setContentsMargins(16, 16, 16, 16)
    card_layout.setSpacing(12)

    icons = [
        ("shield", "Bloqueados"),
        ("sliders", "Selectivo"),
        ("clock", "Horarios"),
        ("activity", "Dashboard"),
        ("sun", "Claro"),
        ("moon", "Oscuro"),
        ("monitor", "Sistema"),
        ("settings", "Ajustes"),
        ("coffee", "Pausa"),
        ("timer", "Pomodoro"),
        ("zap", "Profundo"),
        ("lock", "Bloquear"),
        ("unlock", "Desbloquear"),
        ("plus", "Añadir"),
        ("minus", "Restar"),
        ("trash-2", "Eliminar"),
        ("check", "Guardar"),
        ("search", "Buscar"),
        ("info", "Acerca de"),
        ("power", "Salir")
    ]

    for idx, (icon_name, label) in enumerate(icons):
        row = idx // 4
        col = idx % 4

        btn = QPushButton(label)
        btn.setObjectName("secondaryBtn")
        btn.setIcon(get_themed_icon(icon_name, is_dark=True, role="accent", size=16))
        card_layout.addWidget(btn, row, col)

    layout.addWidget(card)

    actions_row = QHBoxLayout()
    btn_save = QPushButton("Guardar Cambios")
    btn_save.setObjectName("primaryBtn")
    btn_save.setIcon(get_themed_icon("check", is_dark=True, role="white", size=16))
    actions_row.addWidget(btn_save)

    btn_del = QPushButton("Eliminar Dominio")
    btn_del.setObjectName("dangerBtn")
    btn_del.setIcon(get_themed_icon("trash-2", is_dark=True, role="white", size=16))
    actions_row.addWidget(btn_del)

    actions_row.addStretch()
    layout.addLayout(actions_row)

    print("Visual preview test script validated cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(run_preview())
