"""
Focus-Guard Theme & Design System 2.0
Clean modern desktop aesthetic with refined surface elevation,
crisp contrast, and seamless integration for Lucide vector iconography.
"""

import os

DARK_THEME = {
    "bg_window": "#0B0F14",
    "bg_card": "#131822",
    "bg_card_inner": "#18202C",
    "bg_input": "#141A24",
    "border_color": "#242F3E",
    "border_subtle": "#1B232F",
    "border_highlight": "rgba(255, 255, 255, 0.06)",
    "checkbox_border": "#374354",
    "checkbox_bg": "#18202C",
    "text_primary": "#F0F6FC",
    "text_secondary": "#8B949E",
    "text_disabled": "#484F58",
    "btn_disabled_bg": "#131822",
    "btn_disabled_border": "#1B232F",
    "accent_blue": "#388BFD",
    "accent_blue_hover": "#58A6FF",
    "accent_blue_subtle": "rgba(56, 139, 253, 0.12)",
    "tab_bg": "#0D1117",
    "danger": "#F85149",
    "danger_hover": "#FF6B65",
    "danger_subtle": "rgba(248, 81, 73, 0.12)",
    "success": "#2EA043",
    "success_subtle": "rgba(46, 160, 67, 0.14)",
    "warning": "#D29922",
    "warning_subtle": "rgba(210, 153, 34, 0.14)",
}

LIGHT_THEME = {
    "bg_window": "#F6F8FA",
    "bg_card": "#FFFFFF",
    "bg_card_inner": "#F0F3F6",
    "bg_input": "#FFFFFF",
    "border_color": "#D0D7DE",
    "border_subtle": "#E1E4E8",
    "border_highlight": "rgba(0, 0, 0, 0.04)",
    "checkbox_border": "#D0D7DE",
    "checkbox_bg": "#FFFFFF",
    "text_primary": "#1F2328",
    "text_secondary": "#656D76",
    "text_disabled": "#8C959F",
    "btn_disabled_bg": "#EAECEF",
    "btn_disabled_border": "#D0D7DE",
    "accent_blue": "#0969DA",
    "accent_blue_hover": "#0550AE",
    "accent_blue_subtle": "rgba(9, 105, 218, 0.08)",
    "tab_bg": "#EAECEF",
    "danger": "#CF222E",
    "danger_hover": "#A40E26",
    "danger_subtle": "rgba(207, 34, 46, 0.08)",
    "success": "#1A7F37",
    "success_subtle": "rgba(26, 127, 55, 0.08)",
    "warning": "#9A6700",
    "warning_subtle": "rgba(154, 103, 0, 0.08)",
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
            border-bottom: 2px solid transparent;
        }}
        QTabBar::tab:hover {{
            background: {c['bg_card_inner']};
            color: {c['text_primary']};
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
            border: 1.5px solid {c['accent_blue']};
        }}
        QTimeEdit, QSpinBox {{
            background-color: {c['bg_input']};
            color: {c['text_primary']};
            border: 1px solid {c['border_color']};
            border-radius: 6px;
            padding: 3px 8px;
            font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", monospace;
            font-size: 13px;
            font-weight: 700;
            min-height: 24px;
            max-height: 24px;
        }}
        QTimeEdit:focus, QSpinBox:focus {{
            border: 1.5px solid {c['accent_blue']};
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
            border: 1px solid rgba(255, 255, 255, 0.12);
        }}
        QPushButton#primaryBtn:hover {{
            background-color: {c['accent_blue_hover']};
        }}
        QPushButton#primaryBtn:pressed {{
            background-color: {c['accent_blue']};
        }}
        QPushButton#primaryBtn:disabled {{
            background-color: {c['btn_disabled_bg']};
            color: {c['text_disabled']};
            border: 1px solid {c['btn_disabled_border']};
        }}
        QPushButton#secondaryBtn {{
            background-color: {c['bg_card_inner']};
            color: {c['text_primary']};
            border: 1px solid {c['border_color']};
        }}
        QPushButton#secondaryBtn:hover {{
            border-color: {c['accent_blue']};
            background-color: {c['bg_card']};
            color: {c['text_primary']};
        }}
        QPushButton#secondaryBtn:disabled {{
            background-color: {c['bg_window']};
            color: {c['text_disabled']};
            border: 1px solid {c['btn_disabled_border']};
        }}
        QPushButton#stepBtn {{
            background-color: {c['bg_card_inner']};
            color: {c['text_primary']};
            border: 1px solid {c['border_color']};
            border-radius: 6px;
            font-size: 14px;
            font-weight: 700;
            padding: 0px;
            min-width: 32px;
            max-width: 32px;
            min-height: 32px;
            max-height: 32px;
        }}
        QPushButton#stepBtn:hover {{
            background-color: {c['accent_blue']};
            color: #FFFFFF;
            border-color: {c['accent_blue']};
        }}
        QPushButton#stepBtn:disabled {{
            background-color: {c['bg_window']};
            color: {c['text_disabled']};
            border: 1px solid {c['border_subtle']};
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
            background-color: {c['accent_blue_subtle']};
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
            color: {c['accent_blue_hover']};
            background-color: {c['accent_blue_subtle']};
            border: 1px solid rgba(56, 139, 253, 0.25);
            border-radius: 6px;
            padding: 9px 14px;
            font-weight: 600;
        }}
        QPushButton:disabled {{
            opacity: 0.45;
            color: {c['text_disabled']};
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
            background: {c['border_color']};
            min-height: 24px;
            border-radius: 3px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {c['accent_blue']};
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
            border: 1px solid {c['checkbox_border']};
            background-color: {c['checkbox_bg']};
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
        QCheckBox::indicator:checked:disabled {{
            background-color: {c['accent_blue']};
            border-color: {c['accent_blue']};
            image: url({check_icon});
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
        QFrame#kpiCard {{
            background-color: {c['bg_window']};
            border: 1px solid {c['border_subtle']};
            border-radius: 6px;
            padding: 8px 12px;
        }}
        QLabel#kpiTitle {{
            font-size: 10px;
            font-weight: 700;
            color: {c['text_secondary']};
            letter-spacing: 0.5px;
            background: transparent;
            border: none;
        }}
        QLabel#kpiValue {{
            font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", monospace;
            font-size: 13px;
            font-weight: 700;
            color: {c['text_primary']};
            background: transparent;
            border: none;
        }}
        QFrame#infoBanner {{
            background-color: {c['accent_blue_subtle']};
            border: 1px solid rgba(56, 139, 253, 0.22);
            border-radius: 6px;
            padding: 8px 12px;
        }}
        QLabel#infoBannerText {{
            font-size: 11.5px;
            color: {c['accent_blue_hover']};
            font-weight: 500;
            background: transparent;
            border: none;
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
            background-color: {c['success']};
            border-radius: 3px;
        }}
        QPushButton#dangerBtn {{
            background-color: {c['danger']};
            color: #FFFFFF;
            border: 1px solid rgba(255, 255, 255, 0.12);
        }}
        QPushButton#dangerBtn:hover {{
            background-color: {c['danger_hover']};
        }}
        QPushButton#dangerBtn:disabled {{
            background-color: {c['bg_card_inner']};
            color: {c['text_disabled']};
            border: 1px solid {c['border_color']};
        }}
        QPushButton#removeBtn {{
            background-color: {c['bg_card_inner']};
            color: {c['text_secondary']};
            border: 1px solid {c['border_color']};
            border-radius: 6px;
            font-size: 13px;
            font-weight: 700;
            padding: 0px;
            min-width: 28px;
            max-width: 28px;
            min-height: 28px;
            max-height: 28px;
        }}
        QPushButton#removeBtn:hover {{
            background-color: {c['danger']};
            border-color: {c['danger']};
            color: #FFFFFF;
        }}
        QPushButton#removeBtn:disabled {{
            background-color: {c['bg_window']};
            color: {c['text_disabled']};
            border: 1px solid {c['border_subtle']};
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
            padding: 3px 10px;
            border-radius: 12px;
            letter-spacing: 0.5px;
        }}
        QLabel#codePhrase {{
            font-family: ui-monospace, SFMono-Regular, "JetBrains Mono", monospace;
            font-size: 12.5px;
            font-weight: 600;
            color: {c['accent_blue']};
            background: transparent;
            border: none;
        }}
        QComboBox {{
            background-color: {c['bg_input']};
            color: {c['text_primary']};
            border: 1px solid {c['border_color']};
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 12px;
            font-weight: 600;
            min-height: 22px;
        }}
        QComboBox:hover {{
            border-color: {c['accent_blue']};
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {c['bg_card']};
            color: {c['text_primary']};
            border: 1px solid {c['border_color']};
            border-radius: 6px;
            selection-background-color: {c['accent_blue']};
            selection-color: #FFFFFF;
            padding: 4px;
            outline: none;
        }}
        QMenu {{
            background-color: {c['bg_card']};
            color: {c['text_primary']};
            border: 1px solid {c['border_color']};
            border-radius: 8px;
            padding: 4px;
        }}
        QMenu::item {{
            padding: 6px 14px 6px 26px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }}
        QMenu::item:selected {{
            background-color: {c['accent_blue']};
            color: #FFFFFF;
        }}
        QMenu::item:disabled {{
            color: {c['text_disabled']};
        }}
        QMenu::separator {{
            height: 1px;
            background: {c['border_subtle']};
            margin: 4px 6px;
        }}
    """


def apply_dialog_theme(dialog, is_dark=None, resource_dir: str = "") -> bool:
    """Applies unified theme stylesheet to any modal QDialog and returns resolved is_dark."""
    if is_dark is None:
        win = dialog.window() if hasattr(dialog, "window") else None
        if win and hasattr(win, "is_dark_mode"):
            is_dark = win.is_dark_mode()
        elif hasattr(dialog, "parent") and dialog.parent() and hasattr(dialog.parent(), "is_dark_mode"):
            is_dark = dialog.parent().is_dark_mode()
        else:
            try:
                from PyQt6.QtCore import QSettings
                from PyQt6.QtGui import QPalette
                settings = QSettings("FocusGuard", "FocusGuardTray")
                mode = settings.value("theme_mode", "auto")
                if mode == "dark":
                    is_dark = True
                elif mode == "light":
                    is_dark = False
                else:
                    is_dark = dialog.palette().color(QPalette.ColorRole.Window).lightness() < 128
            except Exception:
                is_dark = True

    if not resource_dir and hasattr(dialog, "resource_dir") and dialog.resource_dir:
        resource_dir = dialog.resource_dir
    elif not resource_dir and dialog.parent() and hasattr(dialog.parent(), "resource_dir"):
        resource_dir = dialog.parent().resource_dir
    if not resource_dir:
        this_dir = os.path.dirname(os.path.realpath(__file__))
        candidates = [
            os.path.abspath(os.path.join(this_dir, "../resources")),
            "/usr/share/focus-guard/resources",
            "/usr/local/share/focus-guard/resources",
            "/opt/focus-guard/resources",
            os.path.expanduser("~/.local/share/focus-guard/resources")
        ]
        for candidate in candidates:
            if os.path.exists(candidate) and os.path.exists(os.path.join(candidate, "icon-active.svg")):
                resource_dir = candidate
                break
        if not resource_dir:
            resource_dir = candidates[0]
    dialog.setStyleSheet(get_theme_stylesheet(is_dark, resource_dir))
    return is_dark

