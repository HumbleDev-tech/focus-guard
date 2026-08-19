"""
Focus-Guard state machine and scheduler.
Manages Curfew, Wall-Clock Boot Cooldown (with sleep/suspend awareness), Manual Locks, and Configurable Bypasses.
"""
import os
import time
from datetime import datetime, time as dt_time, timedelta
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("focus-guard.scheduler")


def get_real_seconds_since_boot() -> Optional[float]:
    """
    Calculates actual wall-clock seconds since system boot using /proc/stat 'btime'.
    Accurate across laptop suspend/sleep cycles.
    """
    try:
        if os.path.exists("/proc/stat"):
            with open("/proc/stat", "r") as f:
                for line in f:
                    if line.startswith("btime"):
                        boot_epoch = float(line.split()[1])
                        return max(0.0, time.time() - boot_epoch)
        # Fallback to /proc/uptime if /proc/stat is unreadable
        if os.path.exists("/proc/uptime"):
            with open("/proc/uptime", "r") as f:
                return float(f.readline().split()[0])
    except Exception as e:
        logger.debug(f"Could not calculate boot time: {e}")
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

        start_dt = datetime.combine(now.date(), start_t)
        if now > start_dt and (now - start_dt).total_seconds() > 3600 * 12:
            start_dt += timedelta(days=1)

        diff = (start_dt - now).total_seconds()
        if 0 < diff <= (warning_minutes * 60):
            return True, int(diff)
        return False, 0

    def is_in_boot_cooldown(self, now: Optional[datetime] = None) -> Tuple[bool, int, Optional[datetime]]:
        """
        Checks if system boot cooldown is active.
        Uses wall-clock time from boot epoch to handle suspension correctly.
        """
        boot_cfg = self.config.get("boot_cooldown", {})
        if not boot_cfg.get("enabled", True):
            return False, 0, None

        now = now or datetime.now()
        duration_minutes = boot_cfg.get("duration_minutes", 30)
        cooldown_total_seconds = duration_minutes * 60

        elapsed_since_boot = get_real_seconds_since_boot() if not self.dev_mode else None

        if elapsed_since_boot is not None:
            if elapsed_since_boot < cooldown_total_seconds:
                remaining = max(0, int(cooldown_total_seconds - elapsed_since_boot))
                target = now + timedelta(seconds=remaining)
                return True, remaining, target
            return False, 0, None
        else:
            cooldown_end = self.daemon_start_time + timedelta(minutes=duration_minutes)
            if now < cooldown_end:
                remaining = max(0, int((cooldown_end - now).total_seconds()))
                return True, remaining, cooldown_end
            return False, 0, None

    def is_in_bypass(self, now: Optional[datetime] = None) -> Tuple[bool, int, Optional[datetime]]:
        """Checks if an authorized temporary bypass is active."""
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
        """Evaluates rules in strict priority."""
        now = now or datetime.now()
        bypasses_cfg = self.config.get("bypasses", {})
        bypasses_enabled = bypasses_cfg.get("enabled", True)
        allow_during_curfew = bypasses_cfg.get("allow_during_curfew", False)

        # 1. Curfew check
        in_curfew, curfew_remaining, curfew_target = self.is_in_curfew(now)
        if in_curfew:
            in_bypass, bypass_rem, bypass_target = self.is_in_bypass(now)
            if in_bypass and self.emergency_bypass_active:
                return {
                    "state": "BYPASS",
                    "reason": "EMERGENCY_BYPASS",
                    "remaining_seconds": bypass_rem,
                    "target_time_str": bypass_target.strftime("%H:%M:%S") if bypass_target else "",
                    "message": f"Desbloqueo de emergencia ({bypass_rem // 60}m restantes)",
                    "can_bypass": True,
                    "bypasses_enabled": bypasses_enabled,
                    "is_blocking": False,
                    "in_curfew": True
                }

            self.bypass_end_time = None
            self.emergency_bypass_active = False
            end_t_str = self.config.get("curfew", {}).get("end_time", "07:00")
            return {
                "state": "LOCKED",
                "reason": "CURFEW",
                "remaining_seconds": curfew_remaining,
                "target_time_str": end_t_str,
                "message": f"Toque de Queda nocturno hasta las {end_t_str}",
                "can_bypass": allow_during_curfew,
                "bypasses_enabled": bypasses_enabled,
                "is_blocking": True,
                "in_curfew": True
            }

        curfew_warn, warn_secs = self.is_curfew_approaching(now)

        # 2. Check Standard Bypass
        in_bypass, bypass_rem, bypass_target = self.is_in_bypass(now)
        if in_bypass and bypasses_enabled:
            return {
                "state": "BYPASS",
                "reason": "USER_BYPASS",
                "remaining_seconds": bypass_rem,
                "target_time_str": bypass_target.strftime("%H:%M:%S") if bypass_target else "",
                "message": f"Descanso temporal activo ({bypass_rem // 60}m restantes)",
                "can_bypass": True,
                "bypasses_enabled": bypasses_enabled,
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
                "message": f"Cooldown de Arranque ({boot_remaining // 60}m restantes)",
                "can_bypass": bypasses_enabled,
                "bypasses_enabled": bypasses_enabled,
                "is_blocking": True,
                "in_curfew": False,
                "curfew_warning": curfew_warn,
                "curfew_warning_seconds": warn_secs
            }

        # 4. Check Manual Lock / Pomodoro Session
        if self.manual_lock:
            remaining = 0
            target_str = ""
            if self.manual_lock_end_time:
                if now < self.manual_lock_end_time:
                    remaining = max(0, int((self.manual_lock_end_time - now).total_seconds()))
                    target_str = self.manual_lock_end_time.strftime("%H:%M:%S")
                else:
                    # Pomodoro session completed
                    self.manual_lock = False
                    self.manual_lock_end_time = None

            if self.manual_lock:
                msg = f"Sesión de Enfoque ({remaining // 60}m restantes)" if self.manual_lock_end_time else "Modo Focus Manual activo"
                return {
                    "state": "LOCKED",
                    "reason": "MANUAL_LOCK",
                    "remaining_seconds": remaining,
                    "target_time_str": target_str,
                    "message": msg,
                    "can_bypass": bypasses_enabled,
                    "bypasses_enabled": bypasses_enabled,
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
            "bypasses_enabled": bypasses_enabled,
            "is_blocking": False,
            "in_curfew": False,
            "curfew_warning": curfew_warn,
            "curfew_warning_seconds": warn_secs
        }

    def request_bypass(self, duration_minutes: int, force: bool = False) -> Tuple[bool, str]:
        """Requests a temporary bypass."""
        bypasses_cfg = self.config.get("bypasses", {})
        if not bypasses_cfg.get("enabled", True) and not force:
            return False, "La opción de descansos temporales está desactivada en los ajustes."

        now = datetime.now()
        in_curfew, _, _ = self.is_in_curfew(now)

        if in_curfew and not bypasses_cfg.get("allow_during_curfew", False) and not force:
            return False, f"Bypass denegado: El Toque de Queda está activo hasta las {self.config.get('curfew', {}).get('end_time', '07:00')}."

        if duration_minutes <= 0 or duration_minutes > 180:
            return False, "Duración inválida (debe ser entre 1 y 180 minutos)."

        self.bypass_end_time = now + timedelta(minutes=duration_minutes)
        self.emergency_bypass_active = force and in_curfew
        self.manual_lock = False
        self.manual_lock_end_time = None
        logger.info(f"Bypass granted for {duration_minutes} minutes")
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
        """Forces a manual lock or timed Pomodoro session immediately."""
        self.bypass_end_time = None
        self.emergency_bypass_active = False
        self.manual_lock = True
        if duration_minutes > 0:
            self.manual_lock_end_time = datetime.now() + timedelta(minutes=duration_minutes)
            msg = f"Sesión de enfoque iniciada por {duration_minutes} minutos."
        else:
            self.manual_lock_end_time = None
            msg = "Modo Focus bloqueado indefinidamente."
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
