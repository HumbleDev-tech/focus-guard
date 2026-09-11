"""
Focus-Guard Domains Tab Component
Handles adding, filtering, displaying, and removing blocked domains with friction protection.
"""
from typing import List, Callable, Optional, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QAbstractItemView, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QPalette

from client.utils import sanitize_domain
from client.dialogs import ConfirmDomainRemovalDialog


class DomainsTab(QWidget):
    """Component managing the Blocked Domains tab."""
    domains_changed = pyqtSignal(list)
    auto_save_requested = pyqtSignal(list, str)  # (domains, feedback_text)

    def __init__(self, get_protection_status_fn: Callable[[], Dict[str, Any]],
                 get_config_fn: Callable[[], Dict[str, Any]],
                 parent=None):
        super().__init__(parent)
        self.get_protection_status = get_protection_status_fn
        self.get_config = get_config_fn
        self.blocked_domains: List[str] = []

        self.setup_ui()

    def is_dark_mode(self) -> bool:
        bg = self.palette().color(QPalette.ColorRole.Window)
        return bg.lightness() < 128

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # 1. Direct Input Row
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText("Ingresa un dominio a bloquear (ej: twitter.com o enlace)...")
        self.domain_input.returnPressed.connect(self.on_add_domain_clicked)
        self.domain_input.textChanged.connect(self.on_domain_input_changed)
        top_row.addWidget(self.domain_input)

        add_btn = QPushButton("Añadir")
        add_btn.setObjectName("primaryBtn")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.on_add_domain_clicked)
        top_row.addWidget(add_btn)
        layout.addLayout(top_row)

        # Live preview chip
        self.domain_preview_lbl = QLabel("")
        self.domain_preview_lbl.setStyleSheet("font-size: 11px; font-weight: 600; padding-left: 2px;")
        layout.addWidget(self.domain_preview_lbl)

        # 2. Header with counter, search filter and inline auto-save feedback
        count_row = QHBoxLayout()
        count_row.setSpacing(10)
        self.domains_count_lbl = QLabel("Sitios Bloqueados")
        self.domains_count_lbl.setObjectName("fieldLabel")
        count_row.addWidget(self.domains_count_lbl)

        count_row.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtrar sitios...")
        self.search_input.setFixedWidth(170)
        self.search_input.textChanged.connect(lambda: self.render_domains_list())
        count_row.addWidget(self.search_input)

        self.domain_auto_feedback_lbl = QLabel("")
        self.domain_auto_feedback_lbl.setStyleSheet("font-size: 11px; color: #2EA043; font-weight: 600;")
        count_row.addWidget(self.domain_auto_feedback_lbl)
        layout.addLayout(count_row)

        # 3. Clean List with Fluid Rows
        self.domains_list = QListWidget()
        self.domains_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.domains_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.domains_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.domains_list)

    def set_domains(self, domains: List[str]):
        self.blocked_domains = list(domains)
        self.render_domains_list()

    def get_domains(self) -> List[str]:
        return list(self.blocked_domains)

    def focus_domain_input(self):
        self.domain_input.setFocus()
        self.domain_input.selectAll()

    def focus_search_or_domain_input(self):
        if len(self.blocked_domains) > 5:
            self.search_input.setFocus()
            self.search_input.selectAll()
        else:
            self.focus_domain_input()

    def on_domain_input_changed(self, text: str):
        raw = text.strip()
        if not raw:
            self.domain_preview_lbl.setText("")
            return
        clean = sanitize_domain(raw)
        if clean:
            if clean in self.blocked_domains:
                self.domain_preview_lbl.setStyleSheet("font-size: 11px; color: #D29922; font-weight: 600;")
                self.domain_preview_lbl.setText(f"Dominio ya presente en la lista: {clean}")
            else:
                self.domain_preview_lbl.setStyleSheet("font-size: 11px; color: #58A6FF; font-weight: 600;")
                self.domain_preview_lbl.setText(f"Se bloqueará: {clean}")
        else:
            self.domain_preview_lbl.setStyleSheet("font-size: 11px; color: #F85149; font-weight: 600;")
            self.domain_preview_lbl.setText("Formato de dominio no reconocido (ej: twitter.com)")

    def render_domains_list(self):
        self.domains_list.clear()
        total_cnt = len(self.blocked_domains)
        filter_text = self.search_input.text().strip().lower() if hasattr(self, "search_input") else ""
        filtered_domains = [d for d in self.blocked_domains if (not filter_text or filter_text in d.lower())]

        if filter_text:
            self.domains_count_lbl.setText(f"Sitios ({len(filtered_domains)} de {total_cnt})")
        else:
            self.domains_count_lbl.setText(f"Sitios Bloqueados ({total_cnt})")

        if hasattr(self, "search_input"):
            self.search_input.setEnabled(total_cnt > 0)
            self.search_input.setPlaceholderText("Sin sitios" if total_cnt == 0 else "Filtrar sitios...")
        is_dark = self.is_dark_mode()
        hover_bg = "#161B22" if is_dark else "#F6F8FA"
        sep_color = "#21262D" if is_dark else "#E1E4E8"

        if total_cnt == 0:
            item = QListWidgetItem()
            empty_box = QFrame()
            empty_layout = QVBoxLayout(empty_box)
            empty_layout.setContentsMargins(20, 36, 20, 36)
            empty_layout.setSpacing(6)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            title = QLabel("Sin sitios en la lista")
            title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {'#F0F6FC' if is_dark else '#1F2328'}; background: transparent; border: none;")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(title)

            sub = QLabel("Ingresa dominios arriba (ej: youtube.com) para activar la protección.")
            sub.setStyleSheet("font-size: 11.5px; color: #8B949E; background: transparent; border: none;")
            sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(sub)

            item.setSizeHint(empty_box.sizeHint())
            self.domains_list.addItem(item)
            self.domains_list.setItemWidget(item, empty_box)
            return

        if not filtered_domains and filter_text:
            item = QListWidgetItem()
            lbl = QLabel("Sin coincidencias para la búsqueda")
            lbl.setStyleSheet("font-size: 11.5px; color: #8B949E; padding: 20px; background: transparent;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setSizeHint(QSize(0, 44))
            self.domains_list.addItem(item)
            self.domains_list.setItemWidget(item, lbl)
            return

        for domain in sorted(filtered_domains):
            item = QListWidgetItem()
            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{
                    background-color: transparent;
                    border-bottom: 1px solid {sep_color};
                    border-radius: 6px;
                    border-left: 3px solid transparent;
                }}
                QFrame:hover {{
                    background-color: {hover_bg};
                    border-left: 3px solid #388BFD;
                }}
            """)

            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 5, 12, 5)
            row_layout.setSpacing(10)

            dot_lbl = QLabel("•")
            dot_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #58A6FF; border: none; background: transparent;")
            row_layout.addWidget(dot_lbl)

            name_lbl = QLabel(domain)
            name_lbl.setStyleSheet(f"font-weight: 600; font-size: 13px; border: none; background: transparent; color: {'#F0F6FC' if is_dark else '#1F2328'};")
            row_layout.addWidget(name_lbl)

            row_layout.addStretch()

            # Subtle routing pill to bridge the horizontal gap
            status_pill = QLabel("127.0.0.1")
            status_pill.setStyleSheet(f"""
                font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", monospace;
                font-size: 10px;
                font-weight: 600;
                color: {'#8B949E' if is_dark else '#656D76'};
                background-color: {'rgba(110, 118, 129, 0.12)' if is_dark else 'rgba(175, 184, 193, 0.15)'};
                border: 1px solid {'#30363D' if is_dark else '#D0D7DE'};
                border-radius: 4px;
                padding: 2px 8px;
            """)
            status_pill.setToolTip("Redirigido a localhost para bloqueo local")
            row_layout.addWidget(status_pill)

            # Elegant minimalist remove button
            del_btn = QPushButton("×")
            del_btn.setToolTip(f"Eliminar {domain}")
            del_btn.setObjectName("removeBtn")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda _, d=domain: self.on_remove_domain(d))
            row_layout.addWidget(del_btn)

            item.setSizeHint(QSize(0, 46))
            self.domains_list.addItem(item)
            self.domains_list.setItemWidget(item, row)

    def on_add_domain_clicked(self):
        raw = self.domain_input.text()
        domain = sanitize_domain(raw)
        if not domain:
            self.domain_auto_feedback_lbl.setStyleSheet("font-size: 11px; color: #F85149; font-weight: 600;")
            self.domain_auto_feedback_lbl.setText("Dominio inválido")
            QTimer.singleShot(2500, lambda: self.domain_auto_feedback_lbl.setText(""))
            return

        if domain in self.blocked_domains:
            self.domain_auto_feedback_lbl.setStyleSheet("font-size: 11px; color: #D29922; font-weight: 600;")
            self.domain_auto_feedback_lbl.setText("Ya está en la lista")
            QTimer.singleShot(2500, lambda: self.domain_auto_feedback_lbl.setText(""))
            return

        self.blocked_domains.append(domain)
        self.domain_input.clear()
        self.render_domains_list()

        # Emit auto save request
        self.auto_save_requested.emit(self.blocked_domains, f"'{domain}' añadido y guardado")
        self.domains_changed.emit(self.blocked_domains)

    def on_remove_domain(self, domain: str):
        if domain not in self.blocked_domains:
            return

        # Check if active protection is running
        status_res = self.get_protection_status()
        is_blocking = status_res.get("is_blocking", False) if status_res.get("status") == "ok" else False
        reason_msg = status_res.get("message", "Bloqueo activo")

        if is_blocking:
            raw_cfg = self.get_config()
            cfg = raw_cfg.get("config", raw_cfg) if isinstance(raw_cfg, dict) else {}
            phrase = cfg.get("bypasses", {}).get("emergency_phrase", "necesito desbloqueo de emergencia")
            dlg = ConfirmDomainRemovalDialog(domain=domain, reason_str=reason_msg, phrase=phrase, parent=self)
            dlg.exec()
            if not dlg.confirmed:
                return

        self.blocked_domains.remove(domain)
        self.render_domains_list()
        self.auto_save_requested.emit(self.blocked_domains, f"'{domain}' eliminado")
        self.domains_changed.emit(self.blocked_domains)

    def set_feedback_message(self, text: str, is_success: bool = True):
        color = "#2EA043" if is_success else "#F85149"
        self.domain_auto_feedback_lbl.setStyleSheet(f"font-size: 11px; color: {color}; font-weight: 600;")
        self.domain_auto_feedback_lbl.setText(text)
        QTimer.singleShot(3000, lambda: self.domain_auto_feedback_lbl.setText(""))
