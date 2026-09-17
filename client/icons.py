"""
Focus-Guard Icon Engine
Lightweight, zero-dependency Lucide SVG vector icon loader with dynamic tinting,
HiDPI / Wayland awareness, and LRU memory caching.
"""

import os
import functools
from typing import Optional

from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QGuiApplication
from PyQt6.QtSvg import QSvgRenderer


# Standard color roles for themes
ROLE_COLORS = {
    "dark": {
        "primary": "#F0F6FC",
        "secondary": "#8B949E",
        "muted": "#484F58",
        "accent": "#388BFD",
        "accent_hover": "#58A6FF",
        "danger": "#F85149",
        "success": "#2EA043",
        "warning": "#D29922",
        "white": "#FFFFFF",
    },
    "light": {
        "primary": "#1F2328",
        "secondary": "#656D76",
        "muted": "#8C959F",
        "accent": "#0969DA",
        "accent_hover": "#0550AE",
        "danger": "#CF222E",
        "success": "#1A7F37",
        "warning": "#9A6700",
        "white": "#FFFFFF",
    }
}


def _find_icons_dir() -> str:
    """Locates the resources/icons directory across development and system install paths."""
    this_dir = os.path.dirname(os.path.realpath(__file__))
    candidates = [
        os.path.abspath(os.path.join(this_dir, "../resources/icons")),
        os.path.abspath(os.path.join(this_dir, "resources/icons")),
        "/usr/share/focus-guard/resources/icons",
        "/usr/local/share/focus-guard/resources/icons",
        "/opt/focus-guard/resources/icons",
        os.path.expanduser("~/.local/share/focus-guard/resources/icons"),
    ]
    for c in candidates:
        if os.path.isdir(c) and os.path.exists(os.path.join(c, "shield.svg")):
            return c
    return candidates[0]


ICONS_DIR = _find_icons_dir()


def get_icon_path(name: str) -> Optional[str]:
    """Returns absolute path to an icon SVG file if it exists."""
    clean_name = name.removesuffix(".svg")
    target = os.path.join(ICONS_DIR, f"{clean_name}.svg")
    if os.path.isfile(target):
        return target
    return None


@functools.lru_cache(maxsize=128)
def _read_svg_template(name: str) -> Optional[str]:
    """Reads raw SVG template content from disk."""
    path = get_icon_path(name)
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def tint_svg(svg_data: str, color_hex: str) -> str:
    """Replaces currentColor with target color hex string."""
    # Handle standard Lucide stroke="currentColor"
    tinted = svg_data.replace('stroke="currentColor"', f'stroke="{color_hex}"')
    tinted = tinted.replace("currentColor", color_hex)
    return tinted


@functools.lru_cache(maxsize=256)
def _render_pixmap_cached(
    name: str,
    color_hex: str,
    size: int,
    dpr: float = 1.0
) -> QPixmap:
    """Renders a tinted SVG to a crisp QPixmap, scaling for devicePixelRatio."""
    raw_svg = _read_svg_template(name)
    if not raw_svg:
        return QPixmap()

    tinted_svg = tint_svg(raw_svg, color_hex)
    byte_arr = QByteArray(tinted_svg.encode("utf-8"))
    renderer = QSvgRenderer(byte_arr)

    if not renderer.isValid():
        return QPixmap()

    pixel_size = max(1, int(round(size * dpr)))
    pixmap = QPixmap(pixel_size, pixel_size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    pixmap.setDevicePixelRatio(dpr)
    return pixmap


def get_pixmap(
    name: str,
    color: Optional[str] = None,
    size: int = 16,
    dpr: Optional[float] = None
) -> QPixmap:
    """
    Returns a crisp QPixmap for the requested icon.
    Automatically accounts for screen DPR if not explicitly specified.
    """
    if dpr is None:
        app = QGuiApplication.instance()
        if app:
            screen = app.primaryScreen()
            dpr = screen.devicePixelRatio() if screen else 1.0
        else:
            dpr = 1.0

    color_hex = color if color else "#F0F6FC"
    return _render_pixmap_cached(name, color_hex, size, float(dpr))


@functools.lru_cache(maxsize=128)
def get_icon(name: str, color: Optional[str] = None, size: int = 16) -> QIcon:
    """
    Builds a QIcon containing both 1x and 2x pixel ratio pixmaps for crisp
    Wayland and fractional scaling support, plus a disabled state pixmap.
    """
    icon = QIcon()
    color_hex = color if color else "#F0F6FC"

    # 1x and 2x DPR pixmaps for active / normal states
    pm1 = _render_pixmap_cached(name, color_hex, size, 1.0)
    pm2 = _render_pixmap_cached(name, color_hex, size, 2.0)
    if not pm1.isNull():
        icon.addPixmap(pm1, QIcon.Mode.Normal, QIcon.State.Off)
        icon.addPixmap(pm2, QIcon.Mode.Normal, QIcon.State.Off)

    # Disabled state pixmap (soft muted tone)
    muted_color = "#484F58" if color_hex != "#FFFFFF" else "#656D76"
    dis1 = _render_pixmap_cached(name, muted_color, size, 1.0)
    dis2 = _render_pixmap_cached(name, muted_color, size, 2.0)
    if not dis1.isNull():
        icon.addPixmap(dis1, QIcon.Mode.Disabled, QIcon.State.Off)
        icon.addPixmap(dis2, QIcon.Mode.Disabled, QIcon.State.Off)

    return icon


def get_themed_icon(
    name: str,
    is_dark: bool = True,
    role: str = "primary",
    size: int = 16
) -> QIcon:
    """
    Convenience helper to retrieve an icon tinted according to theme and role.
    Roles: 'primary', 'secondary', 'muted', 'accent', 'accent_hover', 'danger', 'success', 'warning', 'white'.
    """
    mode_key = "dark" if is_dark else "light"
    palette = ROLE_COLORS[mode_key]
    color_hex = palette.get(role, palette["primary"])
    return get_icon(name, color=color_hex, size=size)
