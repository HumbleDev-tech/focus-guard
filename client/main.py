"""
Focus-Guard GUI Entry Point (PyQt6 / KDE Plasma 6 Wayland).
"""
import os
import sys
import argparse
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from client.ipc_client import FocusIPCClient
from client.tray import FocusTrayApplet

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("focus-guard.client.main")


def resolve_resource_dir() -> str:
    """Finds the directory containing SVG icons."""
    candidates = [
        os.path.abspath(os.path.join(os.path.dirname(__file__), "../resources")),
        "/usr/share/focus-guard/resources",
        "/usr/local/share/focus-guard/resources",
        os.path.expanduser("~/.local/share/focus-guard/resources")
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.exists(os.path.join(c, "icon-active.svg")):
            return c
    return candidates[0]


def main():
    parser = argparse.ArgumentParser(description="Focus-Guard System Tray Applet")
    parser.add_argument("--socket-path", help="Path to custom Unix domain socket")
    parser.add_argument("--dev", action="store_true", help="Run in dev mode connecting to /tmp/focus_guard_dev.sock")
    args = parser.parse_args()

    sock_path = args.socket_path
    if args.dev and not sock_path:
        sock_path = "/tmp/focus_guard_dev.sock"

    app = QApplication(sys.argv)
    app.setApplicationName("Focus-Guard")
    app.setApplicationDisplayName("Focus-Guard")
    app.setOrganizationName("FocusGuard")
    app.setQuitOnLastWindowClosed(False)

    resource_dir = resolve_resource_dir()
    logger.info(f"Using resources from {resource_dir}")

    # Set default window/app icon
    icon_path = os.path.join(resource_dir, "icon-active.svg")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    ipc = FocusIPCClient(socket_path=sock_path)
    tray = FocusTrayApplet(ipc_client=ipc, resource_dir=resource_dir)
    tray.show()

    logger.info("Focus-Guard Tray Applet started.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
