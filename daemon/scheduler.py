"""
Focus-Guard state machine and scheduler.
Manages Curfew, System Uptime Boot Cooldown, Manual Locks, and Timed Bypasses.
"""
import os
import time
from datetime import datetime, time as dt_time, timedelta
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("focus-guard.scheduler")


def get_system_uptime_seconds() -> Optional[float]:
    """Reads system uptime from /proc/uptime if on Linux."""
    try:
        if os.path.exists("/proc/uptime"):
            with open("/proc/uptime", "r") as f:
                uptime_str = f.readline().split()[0]
                return float(uptime_str)
    except Exception as e:
        logger.debug(f"Could not read /proc/uptime: {e}")
    return None


class StateScheduler:
    def __init__(self, config: Dict[str, Any], dev_mode: bool = False):
        self.config = config
        self.dev_mode = dev_mode
        self.daemon_start_time = datetime.now()
        self.bypass_end_time: Optional[datetime] = None
        self.manual_lock: bool = False
        self.manual_lock_end_time: Optional[datetime] = None
        self.emergency_bypass_active: bool = False

    def update_config(self, config: Dict[str, Any]):
        """Updates internal configuration."""
        self.config = config

    def _parse_time_str(self, time_str: str) -> dt_time:
        """Parses HH:MM into a datetime.time object."""
        parts = time_str.strip().split(":")
        return dt_time(hour=int(parts[0]), minute=int(parts[1]))

    def is_in_curfew(self, now: Optional[datetime] = None) -> Tuple[bool, int, Optional[datetime]]:
        """
        Checks if current time falls into the curfew window (e.g., 23:15 to 07:00).
        Returns (is_curfew, remaining_seconds, target_end_datetime).
        """
        curfew_cfg = self.config.get("curfew", {})
        if not curfew_cfg.get("enabled", True):
            return False, 0, None

        now = now or datetime.now()
        start_t = self._parse_time_str(curfew_cfg.get("start_time", "23:15"))
        end_t = self._parse_time_str(curfew_cfg.get("end_time", "07:00"))

        now_t = now.time()

        if start_t > end_t:
            # Curfew crosses midnight (e.g. 23:15 to 07:00)
            in_curfew = now_t >= start_t or now_t < end_t
            if in_curfew:
                if now_t >= start_t:
                    tomorrow = now.date() + timedelta(days=1)
                    target = datetime.combine(tomorrow, end_t)
                else:
                    target = datetime.combine(now.date(), end_t)
                remaining = max(0, int((target - now).total_seconds()))
                return True, remaining, target
        else:
            # Curfew in same day (e.g. 14:00 to 18:00)
            in_curfew = start_t <= now_t < end_t
            if in_curfew:
                target = datetime.combine(now.date(), end_t)
                remaining = max(0, int((target - now).total_seconds()))
                return True, remaining, target

        return False, 0, None

    def is_curfew_approaching(self, now: Optional[datetime] = None, warning_minutes: int = 10) -> Tuple[bool, int]:
        """Checks if curfew will start within the next `warning_minutes`."""
        curfew_cfg = self.config.get("curfew", {})
        if not curfew_cfg.get("enabled", True):
            return False, 0

        now = now or datetime.now()
        start_t = self._parse_time_str(curfew_cfg.get("start_time", "23:15"))

        # Build start datetime for today
        start_dt = datetime.combine(now.date(), start_t)
        if now > start_dt and (now - start_dt).total_seconds() > 3600 * 12:
            start_dt += timedelta(days=1)

        diff = (start_dt - now).total_seconds()
        if 0 < diff <= (warning_minutes * 60):
            return True, int(diff)
        return False, 0

    def is_in_boot_cooldown(self, now: Optional[datetime] = None) -> Tuple[bool, int, Optional[datetime]]:
        """
        Checks if system boot cooldown is active using /proc/uptime (or daemon start in dev mode).
        Returns (is_boot_cooldown, remaining_seconds, target_end_datetime).
        """
        boot_cfg = self.config.get("boot_cooldown", {})
        if not boot_cfg.get("enabled", True):
            return False, 0, None

        now = now or datetime.now()
        duration_minutes = boot_cfg.get("duration_minutes", 30)
        cooldown_total_seconds = duration_minutes * 60

        uptime = get_system_uptime_seconds() if not self.dev_mode else None

        if uptime is not None:
            # Real Linux system uptime
            if uptime < cooldown_total_seconds:
                remaining = max(0, int(cooldown_total_seconds - uptime))
                target = now + timedelta(seconds=remaining)
                return True, remaining, target
            return False, 0, None
        else:
            # Fallback to daemon start time
            cooldown_end = self.daemon_start_time + timedelta(minutes=duration_minutes)
            if now < cooldown_end:
                remaining = max(0, int((cooldown_end - now).total_seconds()))
                return True, remaining, cooldown_end
            return False, 0, None

    def is_in_bypass(self, now: Optional[datetime] = None) -> Tuple[bool, int, Optional[datetime]]:
        """
        Checks if an authorized temporary bypass is active.
        Returns (is_bypass, remaining_seconds, target_end_datetime).
        """
        if not self.bypass_end_time:
            return False, 0, None

        now = now or datetime.now()
        if now < self.bypass_end_time:
            remaining = max(0, int((self.bypass_end_time - now).total_seconds()))
            return True, remaining, self.bypass_end_time
        else:
            self.bypass_end_time = None
            self.emergency_bypass_active = False
            return False, 0, None

    def evaluate_state(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Evaluates current rules in strict priority:
        1. Curfew (unless emergency bypass active)
        2. Bypass
        3. Boot Cooldown
        4. Manual Lock
        5. Free / Unlocked
        """
        now = now or datetime.now()

        # 1. Curfew check
        in_curfew, curfew_remaining, curfew_target = self.is_in_curfew(now)
        if in_curfew:
            # Check if an emergency bypass is authorized
            in_bypass, bypass_rem, bypass_target = self.is_in_bypass(now)
            if in_bypass and self.emergency_bypass_active:
                return {
                    "state": "BYPASS",
                    "reason": "EMERGENCY_BYPASS",
                    "remaining_seconds": bypass_rem,
                    "target_time_str": bypass_target.strftime("%H:%M:%S") if bypass_target else "",
                    "message": f"Desbloqueo de emergencia ({bypass_rem // 60}m {bypass_rem % 60}s restantes)",
                    "can_bypass": True,
                    "is_blocking": False,
                    "in_curfew": True
                }

            # Normal Curfew active
            self.bypass_end_time = None
            self.emergency_bypass_active = False
            end_t_str = self.config.get("curfew", {}).get("end_time", "07:00")
            return {
                "state": "LOCKED",
                "reason": "CURFEW",
                "remaining_seconds": curfew_remaining,
                "target_time_str": end_t_str,
                "message": f"Toque de Queda nocturno hasta las {end_t_str}",
                "can_bypass": self.config.get("curfew", {}).get("allow_bypass", False),
                "is_blocking": True,
                "in_curfew": True
            }

        # Curfew approaching warning check
        curfew_warn, warn_secs = self.is_curfew_approaching(now)

        # 2. Check Standard Bypass
        in_bypass, bypass_rem, bypass_target = self.is_in_bypass(now)
        if in_bypass:
            return {
                "state": "BYPASS",
                "reason": "USER_BYPASS",
                "remaining_seconds": bypass_rem,
                "target_time_str": bypass_target.strftime("%H:%M:%S") if bypass_target else "",
                "message": f"Descanso temporal activo ({bypass_rem // 60}m {bypass_rem % 60}s restantes)",
                "can_bypass": True,
                "is_blocking": False,
                "in_curfew": False,
                "curfew_warning": curfew_warn,
                "curfew_warning_seconds": warn_secs
            }

        # 3. Check Boot Cooldown
        in_boot, boot_remaining, boot_target = self.is_in_boot_cooldown(now)
        if in_boot:
            target_str = boot_target.strftime("%H:%M:%S") if boot_target else ""
            return {
                "state": "LOCKED",
                "reason": "BOOT_COOLDOWN",
                "remaining_seconds": boot_remaining,
                "target_time_str": target_str,
                "message": f"Cooldown de Arranque ({boot_remaining // 60}m {boot_remaining % 60}s restantes)",
                "can_bypass": True,
                "is_blocking": True,
                "in_curfew": False,
                "curfew_warning": curfew_warn,
                "curfew_warning_seconds": warn_secs
            }

        # 4. Check Manual Lock
        if self.manual_lock:
            remaining = 0
            target_str = ""
            if self.manual_lock_end_time:
                if now < self.manual_lock_end_time:
                    remaining = max(0, int((self.manual_lock_end_time - now).total_seconds()))
                    target_str = self.manual_lock_end_time.strftime("%H:%M:%S")
                else:
                    self.manual_lock = False
                    self.manual_lock_end_time = None

            if self.manual_lock:
                return {
                    "state": "LOCKED",
                    "reason": "MANUAL_LOCK",
                    "remaining_seconds": remaining,
                    "target_time_str": target_str,
                    "message": "Modo Focus Manual activo",
                    "can_bypass": True,
                    "is_blocking": True,
                    "in_curfew": False,
                    "curfew_warning": curfew_warn,
                    "curfew_warning_seconds": warn_secs
                }

        # 5. Free Time
        return {
            "state": "UNLOCKED",
            "reason": "FREE_TIME",
            "remaining_seconds": 0,
            "target_time_str": "",
            "message": "Modo Libre (Sitios desbloqueados)",
            "can_bypass": False,
            "is_blocking": False,
            "in_curfew": False,
            "curfew_warning": curfew_warn,
            "curfew_warning_seconds": warn_secs
        }

    def request_bypass(self, duration_minutes: int, force: bool = False) -> Tuple[bool, str]:
        """Requests a temporary bypass."""
        now = datetime.now()
        in_curfew, _, _ = self.is_in_curfew(now)

        if in_curfew and not self.config.get("curfew", {}).get("allow_bypass", False) and not force:
            return False, f"Bypass denegado: El Toque de Queda nocturno está activo hasta las {self.config.get('curfew', {}).get('end_time', '07:00')}."

        if duration_minutes <= 0 or duration_minutes > 180:
            return False, "Duración inválida (debe ser entre 1 y 180 minutos)."

        self.bypass_end_time = now + timedelta(minutes=duration_minutes)
        self.emergency_bypass_active = force and in_curfew
        self.manual_lock = False
        self.manual_lock_end_time = None
        logger.info(f"Bypass granted for {duration_minutes} minutes (until {self.bypass_end_time.strftime('%H:%M:%S')})")
        return True, f"Bypass activado por {duration_minutes} minutos."

    def cancel_bypass(self) -> Tuple[bool, str]:
        """Cancels any active bypass immediately."""
        if self.bypass_end_time is not None:
            self.bypass_end_time = None
            self.emergency_bypass_active = False
            logger.info("Bypass cancelled by user.")
            return True, "Descanso cancelado. Modo Focus reactivado."
        return True, "No hay descanso activo."

    def request_lock(self, duration_minutes: int = 0) -> Tuple[bool, str]:
        """Forces a manual lock immediately."""
        self.bypass_end_time = None
        self.emergency_bypass_active = False
        self.manual_lock = True
        if duration_minutes > 0:
            self.manual_lock_end_time = datetime.now() + timedelta(minutes=duration_minutes)
            msg = f"Bloqueado manualmente por {duration_minutes} minutos."
        else:
            self.manual_lock_end_time = None
            msg = "Bloqueado manualmente."
        logger.info(msg)
        return True, msg

    def request_unlock(self) -> Tuple[bool, str]:
        """Unlocks manual mode if not restricted by curfew or boot cooldown."""
        now = datetime.now()
        in_curfew, _, _ = self.is_in_curfew(now)
        if in_curfew:
            return False, "No se puede desbloquear durante el Toque de Queda nocturno."

        in_boot, remaining, _ = self.is_in_boot_cooldown(now)
        if in_boot:
            return False, f"No se puede desbloquear durante el Cooldown de Arranque ({remaining // 60}m restantes)."

        self.manual_lock = False
        self.manual_lock_end_time = None
        self.bypass_end_time = None
        self.emergency_bypass_active = False
        logger.info("Manual lock cleared.")
        return True, "Sitios desbloqueados."
