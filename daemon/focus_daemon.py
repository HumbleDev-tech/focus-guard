"""
Focus-Guard Daemon: System service managing Unix socket IPC and /etc/hosts blocking.
"""
import os
import sys
import json
import time
import signal
import socket
import logging
import argparse
import threading
from typing import Dict, Any, Optional

# Add parent directory to path so relative imports work when executed directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from daemon.hosts_manager import HostsManager
from daemon.scheduler import StateScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("focus-guard.daemon")

DEFAULT_CONFIG_LOCATIONS = [
    "/etc/focus-guard/config.json",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../config/default_config.json"))
]


def load_config(custom_path: Optional[str] = None) -> Dict[str, Any]:
    """Finds and loads configuration JSON."""
    paths_to_check = [custom_path] if custom_path else DEFAULT_CONFIG_LOCATIONS
    for p in paths_to_check:
        if p and os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    logger.info(f"Loaded configuration from {p}")
                    return cfg
            except Exception as e:
                logger.error(f"Error reading config {p}: {e}")
    # Fallback minimal config
    return {
        "version": "1.0.0",
        "socket_path": "/run/focus-guard.sock",
        "hosts_path": "/etc/hosts",
        "boot_cooldown": {"enabled": True, "duration_minutes": 30},
        "curfew": {"enabled": True, "start_time": "23:15", "end_time": "07:00", "allow_bypass": False},
        "blocked_domains": ["x.com", "twitter.com", "instagram.com", "reddit.com", "youtube.com", "tiktok.com"]
    }


class FocusDaemon:
    def __init__(self, config_path: Optional[str] = None, hosts_path: Optional[str] = None, socket_path: Optional[str] = None):
        self.config = load_config(config_path)
        self.hosts_path = hosts_path or self.config.get("hosts_path", "/etc/hosts")
        self.socket_path = socket_path or self.config.get("socket_path", "/run/focus-guard.sock")
        
        self.hosts_mgr = HostsManager(self.hosts_path)
        self.scheduler = StateScheduler(self.config)
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self._last_block_state: Optional[bool] = None

    def _apply_current_state(self):
        """Evaluates scheduler and applies or removes the /etc/hosts block."""
        state = self.scheduler.evaluate_state()
        should_block = state.get("is_blocking", False)

        if should_block != self._last_block_state:
            domains = self.config.get("blocked_domains", [])
            ipv4 = self.config.get("redirect_ipv4", "127.0.0.1")
            ipv6 = self.config.get("redirect_ipv6", "::1")

            if should_block:
                logger.info(f"Applying block: {state.get('reason')} - {state.get('message')}")
                self.hosts_mgr.apply_block(domains, ipv4, ipv6)
            else:
                logger.info(f"Removing block: {state.get('reason')} - {state.get('message')}")
                self.hosts_mgr.remove_block()

            self._last_block_state = should_block

    def _state_worker_loop(self):
        """Periodic background loop that monitors curfew and timers."""
        while self.running:
            try:
                self._apply_current_state()
            except Exception as e:
                logger.error(f"Error in state worker: {e}", exc_info=True)
            time.sleep(2)

    def handle_client_request(self, raw_data: str) -> Dict[str, Any]:
        """Processes a single JSON command from the IPC client."""
        try:
            req = json.loads(raw_data)
        except json.JSONDecodeError:
            return {"status": "error", "error": "Invalid JSON payload"}

        action = req.get("action", "status")

        if action == "status":
            state = self.scheduler.evaluate_state()
            return {
                "status": "ok",
                "state": state.get("state"),
                "reason": state.get("reason"),
                "remaining_seconds": state.get("remaining_seconds", 0),
                "message": state.get("message", ""),
                "can_bypass": state.get("can_bypass", True),
                "is_blocking": state.get("is_blocking", False),
                "domains_count": len(self.config.get("blocked_domains", [])),
                "version": self.config.get("version", "1.0.0")
            }

        elif action == "bypass":
            duration = int(req.get("duration_minutes", 15))
            force = bool(req.get("force", False))
            ok, msg = self.scheduler.request_bypass(duration, force=force)
            self._apply_current_state()
            return {"status": "ok" if ok else "denied", "message": msg, "success": ok}

        elif action == "cancel_bypass":
            ok, msg = self.scheduler.cancel_bypass()
            self._apply_current_state()
            return {"status": "ok", "message": msg, "success": ok}

        elif action == "lock":
            duration = int(req.get("duration_minutes", 0))
            ok, msg = self.scheduler.request_lock(duration)
            self._apply_current_state()
            return {"status": "ok", "message": msg, "success": ok}

        elif action == "unlock":
            ok, msg = self.scheduler.request_unlock()
            self._apply_current_state()
            return {"status": "ok" if ok else "denied", "message": msg, "success": ok}

        elif action == "get_config":
            return {"status": "ok", "config": self.config}

        else:
            return {"status": "error", "error": f"Unknown action '{action}'"}

    def _client_handler_thread(self, conn: socket.socket):
        """Handles a connected Unix socket client connection."""
        try:
            conn.settimeout(5.0)
            data = conn.recv(8192).decode("utf-8")
            if data:
                response = self.handle_client_request(data.strip())
                payload = json.dumps(response) + "\n"
                conn.sendall(payload.encode("utf-8"))
        except Exception as e:
            logger.debug(f"IPC client error: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def start_socket_server(self):
        """Initializes and runs the Unix Domain Socket listener."""
        # Ensure parent directory of socket exists
        sock_dir = os.path.dirname(os.path.abspath(self.socket_path))
        os.makedirs(sock_dir, exist_ok=True)

        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError as e:
                logger.error(f"Cannot remove existing socket {self.socket_path}: {e}")
                sys.exit(1)

        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.bind(self.socket_path)

        # Grant read/write permissions to all users so non-root GUI client can connect
        try:
            os.chmod(self.socket_path, 0o666)
            logger.info(f"Socket created at {self.socket_path} (mode 0666)")
        except Exception as e:
            logger.warning(f"Could not set permissions on socket: {e}")

        self.server_socket.listen(10)
        self.server_socket.settimeout(1.0)

        while self.running:
            try:
                conn, _ = self.server_socket.accept()
                t = threading.Thread(target=self._client_handler_thread, args=(conn,), daemon=True)
                t.start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Error accepting connection: {e}")

    def run(self):
        """Starts daemon services."""
        self.running = True
        logger.info("Starting Focus-Guard Daemon...")

        # Start background state monitor
        worker_thread = threading.Thread(target=self._state_worker_loop, daemon=True)
        worker_thread.start()

        # Start socket server on main thread
        try:
            self.start_socket_server()
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt, stopping...")
        finally:
            self.stop()

    def stop(self):
        """Cleans up sockets and state."""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except Exception:
                pass
        logger.info("Focus-Guard Daemon stopped cleanly.")


def main():
    parser = argparse.ArgumentParser(description="Focus-Guard System Daemon")
    parser.add_argument("--config", help="Path to config JSON file")
    parser.add_argument("--hosts-file", help="Path to custom hosts file (e.g. for testing)")
    parser.add_argument("--socket-path", help="Path to custom Unix socket")
    parser.add_argument("--dev", action="store_true", help="Run in dev mode with local paths")
    args = parser.parse_args()

    hosts_file = args.hosts_file
    socket_path = args.socket_path

    if args.dev:
        if not hosts_file:
            hosts_file = "/tmp/focus_guard_dev_hosts"
            if not os.path.exists(hosts_file):
                with open(hosts_file, "w") as f:
                    f.write("127.0.0.1 localhost\n::1 localhost\n")
        if not socket_path:
            socket_path = "/tmp/focus_guard_dev.sock"
        logger.info(f"Running in DEV MODE (Hosts: {hosts_file}, Socket: {socket_path})")

    daemon = FocusDaemon(
        config_path=args.config,
        hosts_path=hosts_file,
        socket_path=socket_path
    )

    def sig_handler(signum, frame):
        logger.info(f"Signal {signum} received, stopping daemon...")
        daemon.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    daemon.run()


if __name__ == "__main__":
    main()
