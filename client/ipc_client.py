"""
IPC Client for Focus-Guard Daemon via Unix Domain Socket.
"""
import os
import json
import socket
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("focus-guard.client.ipc")

DEFAULT_SOCKET_PATHS = [
    "/run/focus-guard.sock",
    "/tmp/focus_guard_dev.sock"
]


class FocusIPCClient:
    def __init__(self, socket_path: Optional[str] = None):
        self.socket_path = socket_path

    def _resolve_socket_path(self) -> Optional[str]:
        """Finds the first existing socket path."""
        if self.socket_path and os.path.exists(self.socket_path):
            return self.socket_path
        for p in DEFAULT_SOCKET_PATHS:
            if os.path.exists(p):
                return p
        return self.socket_path or DEFAULT_SOCKET_PATHS[0]

    def send_command(self, payload: Dict[str, Any], timeout: float = 3.0) -> Dict[str, Any]:
        """Sends a JSON request to the daemon and returns parsed JSON response."""
        sock_path = self._resolve_socket_path()
        if not sock_path or not os.path.exists(sock_path):
            return {
                "status": "offline",
                "error": "Daemon socket not found. Is focus-guard service running?"
            }

        client_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client_sock.settimeout(timeout)

        try:
            client_sock.connect(sock_path)
            message = json.dumps(payload) + "\n"
            client_sock.sendall(message.encode("utf-8"))

            buffer = ""
            while True:
                chunk = client_sock.recv(4096).decode("utf-8")
                if not chunk:
                    break
                buffer += chunk
                if "\n" in buffer:
                    break

            if not buffer:
                return {"status": "offline", "error": "Daemon closed connection with no response."}

            return json.loads(buffer.strip())
        except socket.timeout:
            return {"status": "error", "error": "Request timed out waiting for daemon response."}
        except ConnectionRefusedError:
            return {"status": "offline", "error": "Connection refused. Focus-Guard daemon is not active."}
        except Exception as e:
            logger.debug(f"IPC communication error: {e}")
            return {"status": "offline", "error": str(e)}
        finally:
            try:
                client_sock.close()
            except Exception:
                pass

    def get_status(self) -> Dict[str, Any]:
        """Fetches current blocking state and remaining times."""
        return self.send_command({"action": "status"})

    def request_bypass(self, duration_minutes: int) -> Dict[str, Any]:
        """Requests a timed bypass (15, 30, 45 mins)."""
        return self.send_command({
            "action": "bypass",
            "duration_minutes": duration_minutes
        })

    def cancel_bypass(self) -> Dict[str, Any]:
        """Cancels an active bypass immediately."""
        return self.send_command({"action": "cancel_bypass"})

    def lock_now(self, duration_minutes: int = 0) -> Dict[str, Any]:
        """Forces an immediate manual lock."""
        return self.send_command({
            "action": "lock",
            "duration_minutes": duration_minutes
        })

    def unlock_now(self) -> Dict[str, Any]:
        """Unlocks manual mode if permissible."""
        return self.send_command({"action": "unlock"})

    def is_daemon_alive(self) -> bool:
        """Pings daemon to check health."""
        res = self.get_status()
        return res.get("status") == "ok"
