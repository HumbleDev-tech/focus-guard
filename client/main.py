"""
Focus-Guard GUI Entry Point (PyQt6 / KDE Plasma 6 Wayland).
Includes Single Instance enforcement via QLocalServer and graceful shutdown.
"""
import os
import sys
import argparse
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtNetwork import QLocalSocket, QLocalServer

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

SINGLE_INSTANCE_KEY = "focus-guard-tray-instance"


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


def check_single_instance(dev_mode: bool = False) -> bool:
    """
    Checks if another instance of Focus-Guard GUI is already running.
    If running, notifies it to show its window and returns False (exit current).
    """
    socket_key = f"{SINGLE_INSTANCE_KEY}_dev" if dev_mode else SINGLE_INSTANCE_KEY
    socket = QLocalSocket()
    socket.connectToServer(socket_key)
    if socket.waitForConnected(500):
        logger.info("Another instance is already running. Bringing it to focus.")
        socket.write(b"SHOW\n")
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        return False
    return True


def setup_single_instance_server(tray: FocusTrayApplet, dev_mode: bool = False) -> QLocalServer:
    """Sets up local server to listen for new instance launch requests."""
    socket_key = f"{SINGLE_INSTANCE_KEY}_dev" if dev_mode else SINGLE_INSTANCE_KEY
    server = QLocalServer()
    # Remove stale server socket if present
    server.removeServer(socket_key)
    server.listen(socket_key)

    def on_new_connection():
        client_sock = server.nextPendingConnection()
        if client_sock:
            client_sock.waitForReadyRead(500)
            msg = bytes(client_sock.readAll()).decode("utf-8").strip()
            if "SHOW" in msg:
                tray.show_settings_dialog()
            client_sock.disconnectFromServer()

    server.newConnection.connect(on_new_connection)
    return server


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

    # Check for existing running instance
    if not check_single_instance(dev_mode=args.dev):
        sys.exit(0)

    resource_dir = resolve_resource_dir()
    logger.info(f"Using resources from {resource_dir}")

    icon_path = os.path.join(resource_dir, "icon-active.svg")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    ipc = FocusIPCClient(socket_path=sock_path)
    tray = FocusTrayApplet(ipc_client=ipc, resource_dir=resource_dir)
    tray.show()

    # Listen for duplicate launches
    local_server = setup_single_instance_server(tray, dev_mode=args.dev)

    def cleanup():
        try:
            tray.timer.stop()
            local_server.close()
        except Exception:
            pass

    app.aboutToQuit.connect(cleanup)

    logger.info("Focus-Guard Tray Applet started.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
