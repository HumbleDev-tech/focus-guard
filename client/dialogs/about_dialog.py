"""
Focus-Guard About Dialog
Sleek modern About dialog matching the clean dark aesthetic.
"""

import os
from typing import Dict, Any

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt

from client.theme import apply_dialog_theme


class AboutDialog(QDialog):
    """Sleek modern About dialog matching KDE Plasma 6 dark aesthetic."""
    def __init__(self, resource_dir: str, config: Dict[str, Any] | None = None, parent=None):
        super().__init__(parent)
        self.resource_dir = resource_dir
        self.config = config or {}
        self.setWindowTitle("Acerca de Focus-Guard")
        self.setFixedSize(480, 420)
        apply_dialog_theme(self, resource_dir=resource_dir)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(14)

        # Header with Logo
        header = QHBoxLayout()
        header.setSpacing(14)

        icon_lbl = QLabel()
        icon_path = os.path.join(resource_dir, "icon-active.svg")
        if os.path.exists(icon_path):
            icon_lbl.setPixmap(QIcon(icon_path).pixmap(48, 48))
        header.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        app_name = QLabel("Focus-Guard")
        app_name.setStyleSheet("font-size: 18px; font-weight: 800;")
        app_ver = QLabel("Versión 1.0.0 (Linux Edition) • KDE Plasma 6 / Wayland")
        app_ver.setObjectName("cardDesc")
        title_box.addWidget(app_name)
        title_box.addWidget(app_ver)
        header.addLayout(title_box)
        header.addStretch()
        layout.addLayout(header)

        desc = QLabel("Anti-procrastinación y regulador de dopamina a nivel de sistema. Bloquea distracciones en /etc/hosts con separación estricta de privilegios.")
        desc.setObjectName("cardDesc")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Architecture and Rules Card
        card = QFrame()
        card.setObjectName("infoCard")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)

        curfew = self.config.get("curfew", {})
        boot = self.config.get("boot_cooldown", {})
        domains = self.config.get("blocked_domains", [])

        curfew_txt = f"{curfew.get('start_time', '23:15')} a {curfew.get('end_time', '07:00')}" if curfew.get('enabled') else "Desactivado"
        boot_txt = f"{boot.get('duration_minutes', 30)} minutos" if boot.get('enabled') else "Desactivado"

        def make_row(lbl_txt, val_txt):
            r = QHBoxLayout()
            l = QLabel(lbl_txt)
            l.setObjectName("fieldLabel")
            v = QLabel(val_txt)
            v.setObjectName("sectionHeader")
            r.addWidget(l)
            r.addStretch()
            r.addWidget(v)
            return r

        card_layout.addLayout(make_row("Toque de Queda Nocturno:", curfew_txt))
        card_layout.addLayout(make_row("Foco de Inicio de sesión:", boot_txt))
        card_layout.addLayout(make_row("Sitios Bloqueados:", f"{len(domains)} dominios"))
        card_layout.addLayout(make_row("Nivel de Redirección:", "0.0.0.0 (Directo)"))

        layout.addWidget(card)

        layout.addStretch()

        # Bottom OK button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        ok_btn = QPushButton("Entendido")
        ok_btn.setObjectName("primaryBtn")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

