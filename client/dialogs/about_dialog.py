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


class AboutDialog(QDialog):
    """Sleek modern About dialog matching KDE Plasma 6 dark aesthetic."""
    def __init__(self, resource_dir: str, config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Acerca de Focus-Guard")
        self.setFixedSize(480, 420)
        self.setStyleSheet("""
            QDialog {
                background-color: #0D1117;
                color: #F0F6FC;
            }
            QPushButton#primaryBtn {
                background-color: #388BFD;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton#primaryBtn:hover {
                background-color: #1F6FEB;
            }
            QFrame#infoCard {
                background-color: #161B22;
                border: 1px solid #30363D;
                border-radius: 8px;
                padding: 14px;
            }
        """)

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
        app_name.setStyleSheet("font-size: 18px; font-weight: 800; color: #F0F6FC;")
        app_ver = QLabel("Versión 1.0.0 (Linux Edition) • KDE Plasma 6 / Wayland")
        app_ver.setStyleSheet("font-size: 11px; color: #8B949E; font-weight: 500;")
        title_box.addWidget(app_name)
        title_box.addWidget(app_ver)
        header.addLayout(title_box)
        header.addStretch()
        layout.addLayout(header)

        desc = QLabel("Anti-procrastinación y regulador de dopamina a nivel de sistema. Bloquea distracciones en /etc/hosts con separación estricta de privilegios.")
        desc.setStyleSheet("font-size: 12px; color: #8B949E; line-height: 1.4;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Architecture and Rules Card
        card = QFrame()
        card.setObjectName("infoCard")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)

        curfew = config.get("curfew", {})
        boot = config.get("boot_cooldown", {})
        domains = config.get("blocked_domains", [])

        curfew_txt = f"{curfew.get('start_time', '23:15')} a {curfew.get('end_time', '07:00')}" if curfew.get('enabled') else "Desactivado"
        boot_txt = f"{boot.get('duration_minutes', 30)} minutos" if boot.get('enabled') else "Desactivado"

        def make_row(lbl_txt, val_txt):
            r = QHBoxLayout()
            l = QLabel(lbl_txt)
            l.setStyleSheet("font-size: 12px; color: #8B949E; font-weight: 500;")
            v = QLabel(val_txt)
            v.setStyleSheet("font-size: 12px; color: #F0F6FC; font-weight: 600;")
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
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)
