"""
Focus-Guard Domains Tab Component
Handles adding, filtering, displaying, and removing blocked domains with friction protection.
"""
import re
from typing import List, Callable, Optional, Dict, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QAbstractItemView, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QPalette

from client.utils import sanitize_domain
from client.dialogs import ConfirmDomainRemovalDialog
from client.icons import get_themed_icon, get_pixmap
from client.i18n import t


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
        win = self.window()
        if win and win is not self and hasattr(win, "is_dark_mode"):
            return win.is_dark_mode()
        if self.parent() and self.parent() is not self and hasattr(self.parent(), "is_dark_mode"):
            return self.parent().is_dark_mode()
        from PyQt6.QtCore import QSettings
        mode = QSettings("FocusGuard", "FocusGuardTray").value("theme_mode", "auto")
        if mode == "dark":
            return True
        elif mode == "light":
            return False
        bg = self.palette().color(QPalette.ColorRole.Window)
        return bg.lightness() < 128

    def update_icons(self, is_dark: bool | None = None):
        if is_dark is None:
            is_dark = self.is_dark_mode()
        if hasattr(self, "add_btn"):
            self.add_btn.setIcon(get_themed_icon("plus", is_dark, role="white", size=14))

    def retranslate_ui(self):
        """Refreshes all texts when language changes dynamically."""
        if hasattr(self, "domain_input"):
            self.domain_input.setPlaceholderText(t("domains.input_placeholder"))
        if hasattr(self, "add_btn"):
            self.add_btn.setText(t("domains.btn_add"))
        if hasattr(self, "search_input"):
            self.search_input.setPlaceholderText(t("domains.search_placeholder"))
        self.render_domains_list()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # 1. Direct Input Row
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText(t("domains.input_placeholder"))
        self.domain_input.returnPressed.connect(self.on_add_domain_clicked)
        self.domain_input.textChanged.connect(self.on_domain_input_changed)
        top_row.addWidget(self.domain_input)

        self.add_btn = QPushButton(t("domains.btn_add"))
        self.add_btn.setObjectName("primaryBtn")
        self.add_btn.setIcon(get_themed_icon("plus", self.is_dark_mode(), role="white", size=14))
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self.on_add_domain_clicked)
        top_row.addWidget(self.add_btn)
        layout.addLayout(top_row)

        # Live preview chip
        self.domain_preview_lbl = QLabel("")
        self.domain_preview_lbl.setStyleSheet("font-size: 11px; font-weight: 600; padding-left: 2px;")
        layout.addWidget(self.domain_preview_lbl)

        # 2. Header with counter, search filter and inline auto-save feedback
        count_row = QHBoxLayout()
        count_row.setSpacing(10)
        self.domains_count_lbl = QLabel(t("domains.header_title"))
        self.domains_count_lbl.setObjectName("fieldLabel")
        count_row.addWidget(self.domains_count_lbl)

        count_row.addStretch()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t("domains.search_placeholder"))
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

        tokens = [t_item for t_item in re.split(r"[,;\s]+", raw) if t_item]
        if len(tokens) > 1:
            valid_tokens = [sanitize_domain(t_item) for t_item in tokens if sanitize_domain(t_item)]
            if valid_tokens:
                self.domain_preview_lbl.setStyleSheet("font-size: 11px; color: #58A6FF; font-weight: 600;")
                self.domain_preview_lbl.setText(t("domains.preview_batch", count=len(valid_tokens)))
            else:
                self.domain_preview_lbl.setStyleSheet("font-size: 11px; color: #F85149; font-weight: 600;")
                self.domain_preview_lbl.setText(t("domains.preview_invalid"))
            return

        clean = sanitize_domain(raw)
        if clean:
            if clean in self.blocked_domains:
                self.domain_preview_lbl.setStyleSheet("font-size: 11px; color: #D29922; font-weight: 600;")
                self.domain_preview_lbl.setText(t("domains.preview_already_exists", domain=clean))
            else:
                self.domain_preview_lbl.setStyleSheet("font-size: 11px; color: #58A6FF; font-weight: 600;")
                self.domain_preview_lbl.setText(t("domains.preview_will_block", domain=clean))
        else:
            self.domain_preview_lbl.setStyleSheet("font-size: 11px; color: #F85149; font-weight: 600;")
            self.domain_preview_lbl.setText(t("domains.preview_invalid"))

    def render_domains_list(self):
        self.domains_list.clear()
        total_cnt = len(self.blocked_domains)
        filter_text = self.search_input.text().strip().lower() if hasattr(self, "search_input") else ""
        filtered_domains = [d for d in self.blocked_domains if (not filter_text or filter_text in d.lower())]

        if filter_text:
            self.domains_count_lbl.setText(t("domains.header_filtered", filtered=len(filtered_domains), total=total_cnt))
        else:
            self.domains_count_lbl.setText(t("domains.header_count", count=total_cnt))

        if hasattr(self, "search_input"):
            self.search_input.setEnabled(total_cnt > 0)
            self.search_input.setPlaceholderText(t("domains.search_empty") if total_cnt == 0 else t("domains.search_placeholder"))
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

            title = QLabel(t("domains.empty_title"))
            title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {'#F0F6FC' if is_dark else '#1F2328'}; background: transparent; border: none;")
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(title)

            sub = QLabel(t("domains.empty_desc"))
            sub.setStyleSheet("font-size: 11.5px; color: #8B949E; background: transparent; border: none;")
            sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(sub)

            item.setSizeHint(empty_box.sizeHint())
            self.domains_list.addItem(item)
            self.domains_list.setItemWidget(item, empty_box)
            return

        if not filtered_domains and filter_text:
            item = QListWidgetItem()
            lbl = QLabel(t("domains.search_no_matches"))
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

            icon_lbl = QLabel()
            icon_lbl.setPixmap(get_pixmap("globe", color="#388BFD" if is_dark else "#0969DA", size=14))
            icon_lbl.setStyleSheet("border: none; background: transparent;")
            row_layout.addWidget(icon_lbl)

            name_lbl = QLabel(domain)
            name_lbl.setStyleSheet(f"font-weight: 600; font-size: 13px; border: none; background: transparent; color: {'#F0F6FC' if is_dark else '#1F2328'};")
            row_layout.addWidget(name_lbl)

            row_layout.addStretch()

            # Subtle routing pill to bridge the horizontal gap
            status_pill = QLabel(t("domains.pill_routing"))
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
            status_pill.setToolTip(t("domains.pill_routing_tooltip"))
            row_layout.addWidget(status_pill)

            # Elegant minimalist remove button with trash-2 icon
            del_btn = QPushButton()
            del_btn.setIcon(get_themed_icon("trash-2", is_dark, role="secondary", active_role="white", size=14))
            del_btn.setToolTip(t("domains.btn_remove_tooltip", domain=domain))
            del_btn.setObjectName("removeBtn")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda _, d=domain: self.on_remove_domain(d))
            row_layout.addWidget(del_btn)

            item.setSizeHint(QSize(0, 46))
            self.domains_list.addItem(item)
            self.domains_list.setItemWidget(item, row)

    def on_add_domain_clicked(self):
        raw = self.domain_input.text()
        tokens = [t_item for t_item in re.split(r"[,;\s]+", raw) if t_item]
        if not tokens:
            return

        cleaned_list: List[str] = []
        for tok in tokens:
            dom = sanitize_domain(tok)
            if dom and dom not in cleaned_list:
                cleaned_list.append(dom)

        if not cleaned_list:
            self.domain_auto_feedback_lbl.setStyleSheet("font-size: 11px; color: #F85149; font-weight: 600;")
            self.domain_auto_feedback_lbl.setText(t("domains.feedback_invalid"))
            QTimer.singleShot(2500, lambda: self.domain_auto_feedback_lbl.setText(""))
            return

        new_domains = [d for d in cleaned_list if d not in self.blocked_domains]
        if not new_domains:
            self.domain_auto_feedback_lbl.setStyleSheet("font-size: 11px; color: #D29922; font-weight: 600;")
            self.domain_auto_feedback_lbl.setText(t("domains.feedback_exists"))
            QTimer.singleShot(2500, lambda: self.domain_auto_feedback_lbl.setText(""))
            return

        self.blocked_domains.extend(new_domains)
        self.domain_input.clear()
        self.render_domains_list()

        # Emit auto save request
        if len(new_domains) == 1:
            feedback_msg = t("domains.feedback_added", domain=new_domains[0])
        else:
            feedback_msg = t("domains.feedback_batch_added", count=len(new_domains))

        self.auto_save_requested.emit(self.blocked_domains, feedback_msg)
        self.domains_changed.emit(self.blocked_domains)

    def on_remove_domain(self, domain: str):
        if domain not in self.blocked_domains:
            return

        # Check if active protection is running
        status_res = self.get_protection_status()
        is_blocking = status_res.get("is_blocking", False) if status_res.get("status") == "ok" else False
        reason_type = status_res.get("reason", "")
        if reason_type == "CURFEW":
            reason_msg = t("dash.status_curfew")
        elif reason_type == "BOOT_COOLDOWN":
            reason_msg = t("dash.status_boot")
        elif reason_type == "MANUAL_LOCK":
            reason_msg = t("dash.status_focus")
        elif reason_type == "SELECTIVE_LOCK":
            reason_msg = t("dash.status_selective")
        else:
            reason_msg = t("domains.active_block")

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
        self.auto_save_requested.emit(self.blocked_domains, t("domains.feedback_removed", domain=domain))
        self.domains_changed.emit(self.blocked_domains)

    def set_feedback_message(self, text: str, is_success: bool = True):
        color = "#2EA043" if is_success else "#F85149"
        self.domain_auto_feedback_lbl.setStyleSheet(f"font-size: 11px; color: {color}; font-weight: 600;")
        self.domain_auto_feedback_lbl.setText(text)
        QTimer.singleShot(3000, lambda: self.domain_auto_feedback_lbl.setText(""))
