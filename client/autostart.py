"""
Focus-Guard Desktop Autostart Integration
Manages XDG compliant autostart desktop entries for desktop environments (KDE Plasma, GNOME, etc.).
"""

import os

USER_AUTOSTART_PATH = os.path.expanduser("~/.config/autostart/focus-guard.desktop")
SYSTEM_AUTOSTART_PATH = "/etc/xdg/autostart/focus-guard.desktop"
AUTOSTART_PATH = USER_AUTOSTART_PATH  # Backward compatibility


def is_autostart_enabled() -> bool:
    """Checks if autostart is enabled per XDG specifications."""
    if os.path.exists(USER_AUTOSTART_PATH):
        try:
            with open(USER_AUTOSTART_PATH, "r", encoding="utf-8") as f:
                content = f.read()
                if "Hidden=true" in content or "X-GNOME-Autostart-enabled=false" in content:
                    return False
                return True
        except Exception:
            return False
    return os.path.exists(SYSTEM_AUTOSTART_PATH)


def set_autostart_enabled(enabled: bool) -> bool:
    """Enables or disables desktop autostart conforming to XDG Desktop specifications."""
    try:
        os.makedirs(os.path.dirname(USER_AUTOSTART_PATH), exist_ok=True)
        if enabled:
            content = (
                "[Desktop Entry]\n"
                "Name=Focus-Guard\n"
                "Comment=Anti-procrastination website blocker and focus regulator\n"
                "Exec=python3 /opt/focus-guard/client/main.py\n"
                "Icon=/opt/focus-guard/resources/icon-active.svg\n"
                "Terminal=false\n"
                "Type=Application\n"
                "Categories=Utility;System;\n"
                "StartupNotify=false\n"
                "Hidden=false\n"
                "X-GNOME-Autostart-enabled=true\n"
            )
            with open(USER_AUTOSTART_PATH, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            if os.path.exists(SYSTEM_AUTOSTART_PATH):
                content = (
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    "Name=Focus-Guard\n"
                    "Hidden=true\n"
                    "X-GNOME-Autostart-enabled=false\n"
                )
                with open(USER_AUTOSTART_PATH, "w", encoding="utf-8") as f:
                    f.write(content)
            else:
                if os.path.exists(USER_AUTOSTART_PATH):
                    os.unlink(USER_AUTOSTART_PATH)
        return True
    except Exception:
        return False
