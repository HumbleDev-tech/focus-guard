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

from daemon.hosts_manager import HostsManager, is_valid_domain
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


class FocusDaemon:
    def __init__(self, config_path: Optional[str] = None, hosts_path: Optional[str] = None, socket_path: Optional[str] = None, dev_mode: bool = False):
        self.config_path = self._resolve_config_path(config_path)
        self.config = self._load_config()
        self.hosts_path = hosts_path or self.config.get("hosts_path", "/etc/hosts")
        self.socket_path = socket_path or self.config.get("socket_path", "/run/focus-guard.sock")
        self.dev_mode = dev_mode
        
        self.hosts_mgr = HostsManager(self.hosts_path)
        self.scheduler = StateScheduler(self.config, dev_mode=self.dev_mode)
        self.running = False
        self.server_socket: Optional[socket.socket] = None
        self._last_block_state: Optional[bool] = None
        self._last_applied_domains: Optional[tuple] = None

    def _resolve_config_path(self, custom_path: Optional[str] = None) -> str:
        """Determines active config file path."""
        if custom_path:
            return custom_path
        for p in DEFAULT_CONFIG_LOCATIONS:
            if os.path.exists(p):
                return p
        return DEFAULT_CONFIG_LOCATIONS[0]

    def _load_config(self) -> Dict[str, Any]:
        """Loads configuration from active config path."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    logger.info(f"Loaded configuration from {self.config_path}")
                    return cfg
            except Exception as e:
                logger.error(f"Error reading config {self.config_path}: {e}")

        return {
            "version": "1.0.0",
            "socket_path": "/run/focus-guard.sock",
            "hosts_path": "/etc/hosts",
            "boot_cooldown": {"enabled": True, "duration_minutes": 30},
            "curfew": {"enabled": True, "start_time": "23:15", "end_time": "07:00"},
            "bypasses": {"enabled": True, "allow_during_curfew": False, "emergency_phrase": "necesito desbloqueo de emergencia"},
            "blocked_domains": ["x.com", "twitter.com", "instagram.com", "reddit.com", "youtube.com", "tiktok.com"],
            "redirect_ipv4": "0.0.0.0",
            "redirect_ipv6": "::1"
        }

    def _save_config(self, new_config: Dict[str, Any]) -> bool:
        """Saves updated configuration to disk safely."""
        try:
            cfg_dir = os.path.dirname(os.path.abspath(self.config_path))
            os.makedirs(cfg_dir, exist_ok=True)

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=2, ensure_ascii=False)
            
            self.config = new_config
            self.scheduler.update_config(new_config)
            logger.info(f"Configuration successfully updated in {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False

    def _apply_current_state(self, force: bool = False):
        """Evaluates scheduler and applies or removes the /etc/hosts block only when state or domains change."""
        state = self.scheduler.evaluate_state()
        should_block = state.get("is_blocking", False)
        current_domains = tuple(sorted(self.config.get("blocked_domains", [])))

        state_changed = (should_block != self._last_block_state)
        domains_changed = (current_domains != self._last_applied_domains)

        if state_changed or (should_block and domains_changed) or force:
            domains = self.config.get("blocked_domains", [])
            ipv4 = self.config.get("redirect_ipv4", "0.0.0.0")
            ipv6 = self.config.get("redirect_ipv6", "::1")

            if should_block:
                logger.info(f"Applying block: {state.get('reason')} - {state.get('message')}")
                self.hosts_mgr.apply_block(domains, ipv4, ipv6)
            else:
                logger.info(f"Removing block: {state.get('reason')} - {state.get('message')}")
                self.hosts_mgr.remove_block()

            self._last_block_state = should_block
            self._last_applied_domains = current_domains

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
                "target_time_str": state.get("target_time_str", ""),
                "message": state.get("message", ""),
                "can_bypass": state.get("can_bypass", True),
                "is_blocking": state.get("is_blocking", False),
                "in_curfew": state.get("in_curfew", False),
                "curfew_warning": state.get("curfew_warning", False),
                "curfew_warning_seconds": state.get("curfew_warning_seconds", 0),
                "domains_count": len(self.config.get("blocked_domains", [])),
                "version": self.config.get("version", "1.0.0")
            }

        elif action == "bypass":
            duration = int(req.get("duration_minutes", 15))
            force = bool(req.get("force", False))
            ok, msg = self.scheduler.request_bypass(duration, force=force)
            self._apply_current_state(force=True)
            return {"status": "ok" if ok else "denied", "message": msg, "success": ok}

        elif action == "emergency_bypass":
            duration = int(req.get("duration_minutes", 15))
            ok, msg = self.scheduler.request_bypass(duration, force=True)
            self._apply_current_state(force=True)
            return {"status": "ok" if ok else "denied", "message": msg, "success": ok}

        elif action == "cancel_bypass":
            ok, msg = self.scheduler.cancel_bypass()
            self._apply_current_state(force=True)
            return {"status": "ok", "message": msg, "success": ok}

        elif action == "lock":
            duration = int(req.get("duration_minutes", 0))
            ok, msg = self.scheduler.request_lock(duration)
            self._apply_current_state(force=True)
            return {"status": "ok", "message": msg, "success": ok}

        elif action == "unlock":
            ok, msg = self.scheduler.request_unlock()
            self._apply_current_state(force=True)
            return {"status": "ok" if ok else "denied", "message": msg, "success": ok}

        elif action == "get_config":
            return {"status": "ok", "config": self.config}

        elif action == "save_config":
            new_cfg = req.get("config")
            if not isinstance(new_cfg, dict):
                return {"status": "error", "error": "Invalid config data (must be a dictionary)"}

            # Security: Whitelist allowed config fields and validate types
            merged_config = dict(self.config)

            # 1. Blocked Domains
            if "blocked_domains" in new_cfg:
                raw_domains = new_cfg["blocked_domains"]
                if not isinstance(raw_domains, list):
                    return {"status": "error", "error": "'blocked_domains' must be a list of domain strings"}
                valid_domains = []
                for d in raw_domains:
                    if isinstance(d, str) and is_valid_domain(d.strip()):
                        valid_domains.append(d.strip().lower())
                merged_config["blocked_domains"] = sorted(list(set(valid_domains)))

            # 2. Curfew
            if "curfew" in new_cfg:
                curfew_in = new_cfg["curfew"]
                if not isinstance(curfew_in, dict):
                    return {"status": "error", "error": "'curfew' must be an object"}
                curfew_obj = dict(merged_config.get("curfew", {}))
                if "enabled" in curfew_in:
                    curfew_obj["enabled"] = bool(curfew_in["enabled"])
                for t_key in ["start_time", "end_time"]:
                    if t_key in curfew_in:
                        val = str(curfew_in[t_key]).strip()
                        parts = val.split(":")
                        if len(parts) != 2 or not (parts[0].isdigit() and parts[1].isdigit() and 0 <= int(parts[0]) <= 23 and 0 <= int(parts[1]) <= 59):
                            return {"status": "error", "error": f"Invalid time format for '{t_key}' (expected HH:MM)"}
                        curfew_obj[t_key] = f"{int(parts[0]):02d}:{int(parts[1]):02d}"
                merged_config["curfew"] = curfew_obj

            # 3. Boot Cooldown
            if "boot_cooldown" in new_cfg:
                boot_in = new_cfg["boot_cooldown"]
                if not isinstance(boot_in, dict):
                    return {"status": "error", "error": "'boot_cooldown' must be an object"}
                boot_obj = dict(merged_config.get("boot_cooldown", {}))
                if "enabled" in boot_in:
                    boot_obj["enabled"] = bool(boot_in["enabled"])
                if "duration_minutes" in boot_in:
                    try:
                        dur = int(boot_in["duration_minutes"])
                        if dur < 1 or dur > 1440:
                            return {"status": "error", "error": "boot_cooldown duration must be between 1 and 1440 minutes"}
                        boot_obj["duration_minutes"] = dur
                    except (ValueError, TypeError):
                        return {"status": "error", "error": "Invalid boot_cooldown duration_minutes"}
                merged_config["boot_cooldown"] = boot_obj

            # 4. Bypasses
            if "bypasses" in new_cfg:
                byp_in = new_cfg["bypasses"]
                if not isinstance(byp_in, dict):
                    return {"status": "error", "error": "'bypasses' must be an object"}
                byp_obj = dict(merged_config.get("bypasses", {}))
                if "enabled" in byp_in:
                    byp_obj["enabled"] = bool(byp_in["enabled"])
                if "allow_during_curfew" in byp_in:
                    byp_obj["allow_during_curfew"] = bool(byp_in["allow_during_curfew"])
                if "emergency_phrase" in byp_in:
                    phrase = str(byp_in["emergency_phrase"]).strip()[:100]
                    byp_obj["emergency_phrase"] = phrase or "necesito desbloqueo de emergencia"
                merged_config["bypasses"] = byp_obj

            # 5. IP Redirections (Optional overrides)
            if "redirect_ipv4" in new_cfg and isinstance(new_cfg["redirect_ipv4"], str):
                ip4 = new_cfg["redirect_ipv4"].strip()
                if ip4 in ("0.0.0.0", "127.0.0.1"):
                    merged_config["redirect_ipv4"] = ip4
            if "redirect_ipv6" in new_cfg and isinstance(new_cfg["redirect_ipv6"], str):
                ip6 = new_cfg["redirect_ipv6"].strip()
                if ip6 in ("::1", "::"):
                    merged_config["redirect_ipv6"] = ip6

            if self._save_config(merged_config):
                self._apply_current_state(force=True)
                return {"status": "ok", "message": "Configuración guardada y aplicada."}
            else:
                return {"status": "error", "error": "No se pudo guardar la configuración en disco."}

        else:
            return {"status": "error", "error": f"Unknown action '{action}'"}

    def _client_handler_thread(self, conn: socket.socket):
        """Handles a connected Unix socket client connection."""
        try:
            conn.settimeout(5.0)
            data = conn.recv(16384).decode("utf-8")
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

        worker_thread = threading.Thread(target=self._state_worker_loop, daemon=True)
        worker_thread.start()

        try:
            self.start_socket_server()
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt, stopping...")
        finally:
            self.stop(clean_hosts=True)

    def stop(self, clean_hosts: bool = True):
        """Cleans up sockets and restores hosts."""
        self.running = False
        if clean_hosts:
            try:
                self.hosts_mgr.remove_block()
                logger.info("Removed Focus-Guard block from hosts on shutdown.")
            except Exception as e:
                logger.warning(f"Could not remove block on stop: {e}")

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
    parser.add_argument("--clean", action="store_true", help="Clean hosts block and exit immediately")
    args = parser.parse_args()

    hosts_file = args.hosts_file
    socket_path = args.socket_path
    config_file = args.config

    if args.dev:
        if not config_file:
            config_file = "/tmp/focus_guard_dev_config.json"
            if not os.path.exists(config_file):
                default_cfg = os.path.abspath(os.path.join(os.path.dirname(__file__), "../config/default_config.json"))
                if os.path.exists(default_cfg):
                    import shutil
                    shutil.copyfile(default_cfg, config_file)
        if not hosts_file:
            hosts_file = "/tmp/focus_guard_dev_hosts"
            if not os.path.exists(hosts_file):
                with open(hosts_file, "w") as f:
                    f.write("127.0.0.1 localhost\n::1 localhost\n")
        if not socket_path:
            socket_path = "/tmp/focus_guard_dev.sock"
        logger.info(f"Running in DEV MODE (Config: {config_file}, Hosts: {hosts_file}, Socket: {socket_path})")

    if args.clean:
        mgr = HostsManager(hosts_file or "/etc/hosts")
        if mgr.remove_block():
            print("Successfully cleaned Focus-Guard block from hosts.")
        else:
            print("Failed to clean hosts.")
        return

    daemon = FocusDaemon(
        config_path=config_file,
        hosts_path=hosts_file,
        socket_path=socket_path,
        dev_mode=args.dev
    )

    def sig_handler(signum, frame):
        logger.info(f"Signal {signum} received, stopping daemon...")
        daemon.stop(clean_hosts=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)

    daemon.run()


if __name__ == "__main__":
    main()
