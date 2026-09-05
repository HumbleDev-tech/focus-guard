"""
Focus-Guard Theme & Design System
Clean minimalist black aesthetic tokens and QSS stylesheet generators.
"""

import os

DARK_THEME = {
    "bg_window": "#0D1117",
    "bg_card": "#161B22",
    "bg_card_inner": "#1C2128",
    "bg_input": "#161B22",
    "border_color": "#30363D",
    "border_subtle": "#21262D",
    "text_primary": "#F0F6FC",
    "text_secondary": "#8B949E",
    "accent_blue": "#388BFD",
    "accent_blue_hover": "#1F6FEB",
    "tab_bg": "#111419",
    "danger": "#DA3633",
    "danger_hover": "#F85149",
    "success": "#2EA043",
    "warning": "#D29922",
}

LIGHT_THEME = {
    "bg_window": "#F6F8FA",
    "bg_card": "#FFFFFF",
    "bg_card_inner": "#F3F4F6",
    "bg_input": "#FFFFFF",
    "border_color": "#D0D7DE",
    "border_subtle": "#E1E4E8",
    "text_primary": "#1F2328",
    "text_secondary": "#656D76",
    "accent_blue": "#0969DA",
    "accent_blue_hover": "#0550AE",
    "tab_bg": "#EAECEF",
    "danger": "#CF222E",
    "danger_hover": "#A40E26",
    "success": "#1A7F37",
    "warning": "#9A6700",
}


def get_theme_colors(is_dark: bool = True) -> dict:
    return DARK_THEME if is_dark else LIGHT_THEME


def get_theme_stylesheet(is_dark: bool, resource_dir: str) -> str:
    c = get_theme_colors(is_dark)
    check_icon = os.path.join(resource_dir, 'checkbox-check.svg')

    return f"""
        QDialog {{
            background-color: {c['bg_window']};
            color: {c['text_primary']};
        }}
        QToolTip {{
            background-color: {c['bg_card']};
            color: {c['text_primary']};
            border: 1px solid {c['border_color']};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 11.5px;
            font-weight: 500;
        }}
        QTabWidget::pane {{
            border: 1px solid {c['border_color']};
            border-radius: 8px;
            background-color: {c['bg_card']};
            top: -1px;
        }}
        QTabBar::tab {{
            background: {c['tab_bg']};
            color: {c['text_secondary']};
            padding: 10px 18px;
            margin-right: 4px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            font-weight: 600;
            font-size: 12px;
        }}
        QTabBar::tab:selected {{
            background: {c['bg_card']};
            color: {c['text_primary']};
            border-top: 2px solid {c['accent_blue']};
        }}
        QLineEdit {{
            background-color: {c['bg_input']};
            color: {c['text_primary']};
            border: 1px solid {c['border_color']};
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 13px;
        }}
        QLineEdit:focus {{
            border: 1px solid {c['accent_blue']};
        }}
        QTimeEdit, QSpinBox {{
            background-color: {c['bg_input']};
            color: {c['text_primary']};
            border: 1px solid {c['border_color']};
            border-radius: 6px;
            padding: 4px 8px;
            font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", monospace;
            font-size: 13px;
            font-weight: 700;
            min-height: 24px;
        }}
        QTimeEdit:focus, QSpinBox:focus {{
            border: 1px solid {c['accent_blue']};
        }}
        QTimeEdit::up-button, QTimeEdit::down-button,
        QSpinBox::up-button, QSpinBox::down-button {{
            width: 0px;
            height: 0px;
            border: none;
            background: transparent;
        }}
        QPushButton {{
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 600;
            font-size: 12px;
        }}
        QPushButton#primaryBtn {{
            background-color: {c['accent_blue']};
            color: #FFFFFF;
            border: none;
        }}
        QPushButton#primaryBtn:hover {{
            background-color: {c['accent_blue_hover']};
        }}
        QPushButton#primaryBtn:disabled {{
            background-color: #161B22;
            color: #484F58;
            border: 1px solid #21262D;
        }}
        QPushButton#secondaryBtn {{
            background-color: {c['bg_card_inner']};
            color: {c['text_primary']};
            border: 1px solid {c['border_color']};
        }}
        QPushButton#secondaryBtn:hover {{
            border-color: {c['accent_blue']};
            background-color: {c['bg_card']};
        }}
        QPushButton#secondaryBtn:disabled {{
            background-color: #0D1117;
            color: #484F58;
            border: 1px solid #21262D;
        }}
        QPushButton#stepBtn {{
            background-color: {c['bg_card_inner']};
            color: {c['text_primary']};
            border: 1px solid {c['border_color']};
            border-radius: 6px;
            font-size: 14px;
            font-weight: 700;
            padding: 0px;
            min-width: 28px;
            max-width: 28px;
            min-height: 26px;
            max-height: 26px;
        }}
        QPushButton#stepBtn:hover {{
            background-color: {c['accent_blue']};
            color: #FFFFFF;
            border-color: {c['accent_blue']};
        }}
        QPushButton#presetChipSmall {{
            background-color: {c['bg_input']};
            color: {c['text_secondary']};
            border: 1px solid {c['border_subtle']};
            border-radius: 12px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 600;
        }}
        QPushButton#presetChipSmall:hover {{
            border-color: {c['accent_blue']};
            color: {c['accent_blue']};
            background-color: {c['bg_card_inner']};
        }}
        QPushButton#presetCardBtn {{
            background-color: {c['bg_card_inner']};
            color: {c['text_primary']};
            border: 1px solid {c['border_color']};
            border-radius: 6px;
            font-size: 11.5px;
            font-weight: 600;
            padding: 8px 6px;
        }}
        QPushButton#presetCardBtn:hover {{
            background-color: {c['bg_card']};
            border-color: {c['accent_blue']};
        }}
        QPushButton#presetCardBtnSelected {{
            background-color: rgba(56, 139, 253, 0.15);
            border: 1.5px solid {c['accent_blue']};
            border-radius: 6px;
            color: {c['accent_blue']};
            font-size: 11.5px;
            font-weight: 700;
            padding: 8px 6px;
        }}
        QFrame#previewCard {{
            background-color: {c['bg_card_inner']};
            border: 1px solid {c['border_subtle']};
            border-radius: 6px;
            padding: 10px 12px;
        }}
        QLabel#summaryPill {{
            font-size: 11.5px;
            color: #58A6FF;
            background-color: rgba(56, 139, 253, 0.08);
            border: 1px solid rgba(56, 139, 253, 0.25);
            border-radius: 6px;
            padding: 6px 12px;
            font-weight: 600;
        }}
        QPushButton:disabled {{
            opacity: 0.45;
            color: #6E7681;
            background-color: {c['bg_card_inner']};
            border: 1px solid {c['border_color']};
        }}
        QListWidget {{
            background-color: {c['bg_card_inner']};
            border: 1px solid {c['border_color']};
            border-radius: 6px;
            padding: 2px;
            outline: none;
        }}
        QListWidget::item {{
            background-color: transparent;
            border: none;
            padding: 0px;
            margin-bottom: 1px;
        }}
        QListWidget::item:focus, QListWidget::item:selected {{
            background-color: transparent;
            border: none;
            outline: none;
        }}
        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 6px;
            margin: 4px 2px 4px 0px;
        }}
        QScrollBar::handle:vertical {{
            background: #30363D;
            min-height: 24px;
            border-radius: 3px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: #58A6FF;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QCheckBox {{
            color: {c['text_primary']};
            font-size: 13px;
            font-weight: 600;
            spacing: 10px;
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1px solid {c['border_color']};
            background-color: {c['bg_input']};
        }}
        QCheckBox::indicator:hover {{
            border-color: {c['accent_blue']};
        }}
        QCheckBox::indicator:checked {{
            background-color: {c['accent_blue']};
            border-color: {c['accent_blue']};
            image: url({check_icon});
        }}
        QCheckBox::indicator:disabled {{
            background-color: {c['bg_card_inner']};
            border-color: {c['border_subtle']};
        }}
        QFrame#settingsCard {{
            background-color: {c['bg_card_inner']};
            border: 1px solid {c['border_subtle']};
            border-radius: 8px;
        }}
        QFrame#heroCard {{
            background-color: {c['bg_card_inner']};
            border: 1px solid {c['border_color']};
            border-radius: 8px;
            padding: 16px;
        }}
        QFrame#telemetryCard {{
            background-color: {c['bg_card_inner']};
            border: 1px solid {c['border_subtle']};
            border-radius: 8px;
            padding: 12px;
        }}
        QLabel#cardDesc {{
            font-size: 12px;
            color: {c['text_secondary']};
            background: transparent;
            border: none;
            padding: 2px 0px;
        }}
        QLabel#fieldLabel {{
            font-size: 12px;
            font-weight: 500;
            color: {c['text_primary']};
            background: transparent;
            border: none;
            padding: 0px;
        }}
        QProgressBar {{
            background-color: {c['bg_input']};
            border: 1px solid {c['border_subtle']};
            border-radius: 4px;
            height: 8px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background-color: #2EA043;
            border-radius: 3px;
        }}
        QPushButton#dangerBtn {{
            background-color: {c['danger']};
            color: #FFFFFF;
            border: none;
        }}
        QPushButton#dangerBtn:hover {{
            background-color: {c['danger_hover']};
        }}
        QPushButton#dangerBtn:disabled {{
            background-color: {c['bg_card_inner']};
            color: #484F58;
            border: 1px solid {c['border_color']};
        }}
        QPushButton#removeBtn {{
            background-color: {c['bg_card_inner']};
            color: {c['text_secondary']};
            border: 1px solid {c['border_color']};
            border-radius: 4px;
            font-size: 15px;
            font-weight: 600;
            padding: 0px;
            min-width: 26px;
            max-width: 26px;
            min-height: 26px;
            max-height: 26px;
        }}
        QPushButton#removeBtn:hover {{
            background-color: {c['danger']};
            border-color: {c['danger']};
            color: #FFFFFF;
        }}
        QFrame#innerCard {{
            background-color: {c['bg_card_inner']};
            border: 1px solid {c['border_color']};
            border-radius: 8px;
            padding: 10px;
        }}
        QFrame#infoCard {{
            background-color: {c['bg_card_inner']};
            border: 1px solid {c['border_color']};
            border-radius: 8px;
            padding: 14px;
        }}
        QLabel#sectionHeader {{
            font-size: 13px;
            font-weight: 700;
            color: {c['text_primary']};
            background: transparent;
            border: none;
            padding: 0px;
        }}
        QLabel#statusBadge {{
            background-color: rgba(110, 118, 129, 0.15);
            color: {c['text_secondary']};
            border: 1px solid {c['border_color']};
            font-size: 10px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 12px;
        }}
        QLabel#codePhrase {{
            font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", monospace;
            font-size: 12.5px;
            font-weight: 600;
            color: {c['accent_blue']};
            background: transparent;
            border: none;
        }}
    """


def apply_dialog_theme(dialog, is_dark: bool = True, resource_dir: str = "") -> None:
    """Applies unified theme stylesheet to any modal QDialog."""
    if not resource_dir and hasattr(dialog, "resource_dir") and dialog.resource_dir:
        resource_dir = dialog.resource_dir
    elif not resource_dir and dialog.parent() and hasattr(dialog.parent(), "resource_dir"):
        resource_dir = dialog.parent().resource_dir
    if not resource_dir:
        candidates = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../resources")),
            "/usr/share/focus-guard/resources",
            "/usr/local/share/focus-guard/resources",
            os.path.expanduser("~/.local/share/focus-guard/resources")
        ]
        for candidate in candidates:
            if os.path.exists(candidate) and os.path.exists(os.path.join(candidate, "icon-active.svg")):
                resource_dir = candidate
                break
        if not resource_dir:
            resource_dir = candidates[0]
    dialog.setStyleSheet(get_theme_stylesheet(is_dark, resource_dir))
