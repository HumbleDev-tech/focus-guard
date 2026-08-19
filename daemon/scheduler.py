"""
Focus-Guard state machine and scheduler.
Manages Curfew, Boot Cooldown, Manual Locks, and Timed Bypasses.
"""
from datetime import datetime, time, timedelta
import logging
from typing import Dict, Any, Tuple, Optional

logger = logging.getLogger("focus-guard.scheduler")


class StateScheduler:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.daemon_start_time = datetime.now()
        self.bypass_end_time: Optional[datetime] = None
        self.manual_lock: bool = False
        self.manual_lock_end_time: Optional[datetime] = None

    def update_config(self, config: Dict[str, Any]):
        """Updates internal configuration."""
        self.config = config

    def _parse_time_str(self, time_str: str) -> time:
        """Parses HH:MM into a datetime.time object."""
        parts = time_str.strip().split(":")
        return time(hour=int(parts[0]), minute=int(parts[1]))

    def is_in_curfew(self, now: Optional[datetime] = None) -> Tuple[bool, int]:
        """
        Checks if current time falls into the curfew window (e.g., 23:15 to 07:00).
        Returns (is_curfew, remaining_seconds).
        """
        curfew_cfg = self.config.get("curfew", {})
        if not curfew_cfg.get("enabled", True):
            return False, 0

        now = now or datetime.now()
        start_t = self._parse_time_str(curfew_cfg.get("start_time", "23:15"))
        end_t = self._parse_time_str(curfew_cfg.get("end_time", "07:00"))

        now_t = now.time()

        if start_t > end_t:
            # Curfew crosses midnight (e.g. 23:15 to 07:00)
            in_curfew = now_t >= start_t or now_t < end_t
            if in_curfew:
                if now_t >= start_t:
                    # Target is end_t on tomorrow's date
                    tomorrow = now.date() + timedelta(days=1)
                    target = datetime.combine(tomorrow, end_t)
                else:
                    # Target is end_t on today's date
                    target = datetime.combine(now.date(), end_t)
                remaining = max(0, int((target - now).total_seconds()))
                return True, remaining
        else:
            # Curfew in same day (e.g. 14:00 to 18:00)
            in_curfew = start_t <= now_t < end_t
            if in_curfew:
                target = datetime.combine(now.date(), end_t)
                remaining = max(0, int((target - now).total_seconds()))
                return True, remaining

        return False, 0

    def is_in_boot_cooldown(self, now: Optional[datetime] = None) -> Tuple[bool, int]:
        """
        Checks if the boot cooldown is currently active.
        Returns (is_boot_cooldown, remaining_seconds).
        """
        boot_cfg = self.config.get("boot_cooldown", {})
        if not boot_cfg.get("enabled", True):
            return False, 0

        now = now or datetime.now()
        duration_minutes = boot_cfg.get("duration_minutes", 30)
        cooldown_end = self.daemon_start_time + timedelta(minutes=duration_minutes)

        if now < cooldown_end:
            remaining = max(0, int((cooldown_end - now).total_seconds()))
            return True, remaining

        return False, 0

    def is_in_bypass(self, now: Optional[datetime] = None) -> Tuple[bool, int]:
        """
        Checks if an authorized temporary bypass is active.
        Returns (is_bypass, remaining_seconds).
        """
        if not self.bypass_end_time:
            return False, 0

        now = now or datetime.now()
        if now < self.bypass_end_time:
            remaining = max(0, int((self.bypass_end_time - now).total_seconds()))
            return True, remaining
        else:
            # Bypass expired
            self.bypass_end_time = None
            return False, 0

    def evaluate_state(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Evaluates current rules in order of priority:
        1. Curfew (Strict, non-negotiable)
        2. Bypass (if permitted outside curfew)
        3. Boot Cooldown
        4. Manual Lock
        5. Free / Unlocked
        """
        now = now or datetime.now()

        # 1. Check Curfew
        in_curfew, curfew_remaining = self.is_in_curfew(now)
        if in_curfew:
            # If bypass was running, cancel it when curfew hits
            self.bypass_end_time = None
            return {
                "state": "LOCKED",
                "reason": "CURFEW",
                "remaining_seconds": curfew_remaining,
                "message": f"Night Curfew active until {self.config.get('curfew', {}).get('end_time', '07:00')}",
                "can_bypass": self.config.get("curfew", {}).get("allow_bypass", False),
                "is_blocking": True
            }

        # 2. Check Active Bypass
        in_bypass, bypass_remaining = self.is_in_bypass(now)
        if in_bypass:
            return {
                "state": "BYPASS",
                "reason": "USER_BYPASS",
                "remaining_seconds": bypass_remaining,
                "message": f"Temporary break active ({bypass_remaining // 60}m {bypass_remaining % 60}s left)",
                "can_bypass": True,
                "is_blocking": False
            }

        # 3. Check Boot Cooldown
        in_boot, boot_remaining = self.is_in_boot_cooldown(now)
        if in_boot:
            return {
                "state": "LOCKED",
                "reason": "BOOT_COOLDOWN",
                "remaining_seconds": boot_remaining,
                "message": f"Boot Focus Cooldown ({boot_remaining // 60}m {boot_remaining % 60}s remaining)",
                "can_bypass": True,
                "is_blocking": True
            }

        # 4. Check Manual Lock
        if self.manual_lock:
            remaining = 0
            if self.manual_lock_end_time:
                if now < self.manual_lock_end_time:
                    remaining = max(0, int((self.manual_lock_end_time - now).total_seconds()))
                else:
                    self.manual_lock = False
                    self.manual_lock_end_time = None

            if self.manual_lock:
                return {
                    "state": "LOCKED",
                    "reason": "MANUAL_LOCK",
                    "remaining_seconds": remaining,
                    "message": "Manual Focus Mode active",
                    "can_bypass": True,
                    "is_blocking": True
                }

        # 5. Free Time (Unlocked)
        return {
            "state": "UNLOCKED",
            "reason": "FREE_TIME",
            "remaining_seconds": 0,
            "message": "Focus-Guard Idle (Sites Unblocked)",
            "can_bypass": False,
            "is_blocking": False
        }

    def request_bypass(self, duration_minutes: int, force: bool = False) -> Tuple[bool, str]:
        """Requests a temporary bypass."""
        now = datetime.now()
        in_curfew, _ = self.is_in_curfew(now)

        if in_curfew and not self.config.get("curfew", {}).get("allow_bypass", False) and not force:
            return False, f"Bypass denied: Night Curfew is strictly active until {self.config.get('curfew', {}).get('end_time', '07:00')}."

        if duration_minutes <= 0 or duration_minutes > 180:
            return False, "Invalid bypass duration (must be between 1 and 180 minutes)."

        self.bypass_end_time = now + timedelta(minutes=duration_minutes)
        self.manual_lock = False
        self.manual_lock_end_time = None
        logger.info(f"Bypass granted for {duration_minutes} minutes (until {self.bypass_end_time.strftime('%H:%M:%S')})")
        return True, f"Bypass granted for {duration_minutes} minutes."

    def cancel_bypass(self) -> Tuple[bool, str]:
        """Cancels any active bypass immediately."""
        if self.bypass_end_time is not None:
            self.bypass_end_time = None
            logger.info("Bypass cancelled by user.")
            return True, "Bypass cancelled. Focus mode resumed."
        return True, "No active bypass to cancel."

    def request_lock(self, duration_minutes: int = 0) -> Tuple[bool, str]:
        """Forces a manual lock immediately."""
        self.bypass_end_time = None
        self.manual_lock = True
        if duration_minutes > 0:
            self.manual_lock_end_time = datetime.now() + timedelta(minutes=duration_minutes)
            msg = f"Locked manually for {duration_minutes} minutes."
        else:
            self.manual_lock_end_time = None
            msg = "Locked manually until next unlocked period or bypass."
        logger.info(msg)
        return True, msg

    def request_unlock(self) -> Tuple[bool, str]:
        """Unlocks manual mode if not restricted by curfew or boot cooldown."""
        now = datetime.now()
        in_curfew, _ = self.is_in_curfew(now)
        if in_curfew:
            return False, "Cannot unlock during Night Curfew."

        in_boot, remaining = self.is_in_boot_cooldown(now)
        if in_boot:
            return False, f"Cannot unlock during Boot Cooldown ({remaining // 60}m remaining). Use temporary bypass instead."

        self.manual_lock = False
        self.manual_lock_end_time = None
        self.bypass_end_time = None
        logger.info("Manual lock cleared.")
        return True, "Sites unlocked."
