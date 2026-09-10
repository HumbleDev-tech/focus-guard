"""
Unit tests covering the logic fixes identified in the user-facing audit:
- Session preservation across temporary bypasses
- Strict curfew emergency bypass enforcement
- Selective lock precedence over prior manual locks
- Indefinite selective lock visibility during boot cooldown
- Indefinite selective lock preservation across Pomodoro sessions
"""
import os
import sys
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from daemon.scheduler import StateScheduler


class TestAuditFixes(unittest.TestCase):
    def setUp(self):
        self.config = {
            "version": "1.0.0",
            "curfew": {
                "enabled": False,
                "start_time": "23:00",
                "end_time": "07:00"
            },
            "boot_cooldown": {
                "enabled": False,
                "duration_minutes": 30
            },
            "bypasses": {
                "enabled": True,
                "allow_during_curfew": False,
                "emergency_phrase": "frase secreta"
            },
            "blocked_domains": ["youtube.com", "instagram.com"]
        }
        self.scheduler = StateScheduler(self.config, dev_mode=True)
        self.scheduler.daemon_start_time = datetime.now() - timedelta(hours=1)

    def test_bypass_preserves_indefinite_selective_lock(self):
        """Taking a temporary break should NOT delete an indefinite selective lock."""
        now = datetime.now()

        # 1. Start indefinite selective lock
        ok, msg = self.scheduler.request_selective_lock(["reddit.com"], 0)
        self.assertTrue(ok)

        st = self.scheduler.evaluate_state(now)
        self.assertEqual(st["state"], "LOCKED")
        self.assertEqual(st["reason"], "SELECTIVE_LOCK")
        self.assertTrue(st["is_indefinite"])
        self.assertEqual(st["domains_to_block"], ["reddit.com"])

        # 2. Request a 15-minute bypass
        ok, msg = self.scheduler.request_bypass(15)
        self.assertTrue(ok)

        st = self.scheduler.evaluate_state(now + timedelta(minutes=5))
        self.assertEqual(st["state"], "BYPASS")
        self.assertFalse(st["is_blocking"])
        self.assertEqual(st["domains_to_block"], [])
        # The underlying configuration must remain intact
        self.assertTrue(self.scheduler.selective_is_indefinite)
        self.assertEqual(self.scheduler.selective_domains, ["reddit.com"])

        # 3. Simulate bypass expiration (after 16 minutes)
        st = self.scheduler.evaluate_state(now + timedelta(minutes=16))
        self.assertEqual(st["state"], "LOCKED")
        self.assertEqual(st["reason"], "SELECTIVE_LOCK")
        self.assertTrue(st["is_indefinite"])
        self.assertEqual(st["domains_to_block"], ["reddit.com"])

        # 4. State export must still retain the lock
        state_export = self.scheduler.export_persistent_state()
        self.assertTrue(state_export["selective_is_indefinite"])
        self.assertEqual(state_export["selective_domains"], ["reddit.com"])

    def test_bypass_preserves_and_resumes_pomodoro_session(self):
        """Taking a break during a Pomodoro should pause and resume with remaining time."""
        now = datetime.now()

        # Start 25 minute Pomodoro
        self.scheduler.request_lock(25)
        st = self.scheduler.evaluate_state(now)
        self.assertEqual(st["state"], "LOCKED")
        self.assertEqual(st["reason"], "MANUAL_LOCK")

        # Request 15 min bypass
        ok, msg = self.scheduler.request_bypass(15)
        self.assertTrue(ok)

        st = self.scheduler.evaluate_state(now + timedelta(minutes=5))
        self.assertEqual(st["state"], "BYPASS")
        self.assertFalse(st["is_blocking"])

        # Cancel bypass early (simulating user clicking 'Finalizar Pausa')
        self.scheduler.cancel_bypass()

        # Session should resume as MANUAL_LOCK with remaining time
        st = self.scheduler.evaluate_state(now + timedelta(minutes=6))
        self.assertEqual(st["state"], "LOCKED")
        self.assertEqual(st["reason"], "MANUAL_LOCK")
        self.assertGreater(st["remaining_seconds"], 0)

    def test_curfew_strict_allow_during_curfew(self):
        """When allow_during_curfew is False, no bypasses (even with force=True) may pass."""
        # Set curfew to cover all day so datetime.now() is guaranteed to be in curfew
        self.config["curfew"] = {
            "enabled": True,
            "start_time": "00:00",
            "end_time": "23:59"
        }
        self.config["bypasses"]["allow_during_curfew"] = False
        self.scheduler.update_config(self.config)

        # Verify in curfew
        st = self.scheduler.evaluate_state()
        self.assertEqual(st["reason"], "CURFEW")
        self.assertFalse(st["can_bypass"])

        # 1. Normal bypass rejected
        ok, msg = self.scheduler.request_bypass(15, force=False)
        self.assertFalse(ok)
        self.assertIn("desactivados", msg.lower())

        # 2. Emergency bypass also strictly rejected
        ok, msg = self.scheduler.request_bypass(15, force=True)
        self.assertFalse(ok)
        self.assertIn("desactivados", msg.lower())

        # Now enable allow_during_curfew
        self.config["bypasses"]["allow_during_curfew"] = True
        self.scheduler.update_config(self.config)

        st = self.scheduler.evaluate_state()
        self.assertTrue(st["can_bypass"])

        # Standard bypass without force should be rejected directing to emergency phrase
        ok, msg = self.scheduler.request_bypass(15, force=False)
        self.assertFalse(ok)
        self.assertIn("emergencia", msg.lower())

        # Emergency bypass with force should be allowed
        ok, msg = self.scheduler.request_bypass(15, force=True)
        self.assertTrue(ok)

        st = self.scheduler.evaluate_state()
        self.assertEqual(st["state"], "BYPASS")
        self.assertEqual(st["reason"], "EMERGENCY_BYPASS")
        self.assertFalse(st["is_blocking"])

    def test_selective_lock_clears_manual_lock_conflict(self):
        """Requesting a selective lock while manual lock is active should cleanly switch to selective."""
        now = datetime.now()

        # 1. Manual lock active
        self.scheduler.request_lock(0)
        st = self.scheduler.evaluate_state(now)
        self.assertEqual(st["reason"], "MANUAL_LOCK")
        self.assertFalse(st["is_selective"])

        # 2. User starts selective lock for a specific domain
        ok, msg = self.scheduler.request_selective_lock(["x.com"], 20)
        self.assertTrue(ok)

        # 3. State must now be SELECTIVE_LOCK and domains_to_block only ["x.com"]
        st = self.scheduler.evaluate_state(now)
        self.assertEqual(st["state"], "LOCKED")
        self.assertEqual(st["reason"], "SELECTIVE_LOCK")
        self.assertTrue(st["is_selective"])
        self.assertEqual(st["domains_to_block"], ["x.com"])

    def test_boot_cooldown_reports_pending_selective_indefinite(self):
        """During boot cooldown, pending indefinite selective lock must be reported so UI knows it exists."""
        # Enable boot cooldown
        self.config["boot_cooldown"] = {
            "enabled": True,
            "duration_minutes": 30
        }
        self.scheduler.update_config(self.config)
        self.scheduler.daemon_start_time = datetime.now()

        # Restore indefinite selective lock
        self.scheduler.restore_persistent_state({
            "selective_is_indefinite": True,
            "selective_domains": ["reddit.com"]
        })

        st = self.scheduler.evaluate_state(datetime.now())
        self.assertEqual(st["reason"], "BOOT_COOLDOWN")
        self.assertTrue(st["has_pending_selective"])
        self.assertTrue(st["selective_is_indefinite"])
        self.assertEqual(st["selective_domains"], ["reddit.com"])

    def test_manual_lock_preserves_indefinite_selective_lock(self):
        """A Pomodoro session should not erase an indefinite selective lock."""
        now = datetime.now()

        # Indefinite lock on reddit.com
        self.scheduler.request_selective_lock(["reddit.com"], 0)
        self.assertTrue(self.scheduler.selective_is_indefinite)

        # Start a 25m Pomodoro
        self.scheduler.request_lock(25)
        st = self.scheduler.evaluate_state(now)
        self.assertEqual(st["reason"], "MANUAL_LOCK")

        # The selective lock configuration must not be erased
        self.assertTrue(self.scheduler.selective_is_indefinite)
        self.assertEqual(self.scheduler.selective_domains, ["reddit.com"])

        # Simulate Pomodoro completion (after 26 minutes)
        st = self.scheduler.evaluate_state(now + timedelta(minutes=26))
        # It must seamlessly return to the indefinite selective lock!
        self.assertEqual(st["state"], "LOCKED")
        self.assertEqual(st["reason"], "SELECTIVE_LOCK")
        self.assertTrue(st["is_indefinite"])
        self.assertEqual(st["domains_to_block"], ["reddit.com"])

    def test_bypass_preserves_indefinite_manual_lock(self):
        """Bypass should pause indefinite manual lock and restore it upon cancellation."""
        now = datetime.now()
        self.scheduler.request_lock(0)
        self.assertTrue(self.scheduler.manual_lock)
        self.assertIsNone(self.scheduler.manual_lock_end_time)

        # Bypass requested
        ok, msg = self.scheduler.request_bypass(15)
        self.assertTrue(ok)
        self.assertFalse(self.scheduler.manual_lock)
        self.assertTrue(self.scheduler.paused_manual_is_indefinite)

        # Cancel bypass
        self.scheduler.cancel_bypass()
        self.assertTrue(self.scheduler.manual_lock)
        self.assertIsNone(self.scheduler.manual_lock_end_time)
        self.assertFalse(self.scheduler.paused_manual_is_indefinite)

    def test_curfew_clears_daytime_paused_pomodoro_timers(self):
        """Curfew interrupting a daytime bypass must clear daytime timers so they don't resurrect."""
        now = datetime.now()
        self.scheduler.request_lock(25)
        self.scheduler.request_bypass(15)
        self.assertIsNotNone(self.scheduler.paused_manual_remaining_seconds)

        # Enable curfew to simulate nighttime arrival
        self.config["curfew"] = {
            "enabled": True,
            "start_time": "00:00",
            "end_time": "23:59"
        }
        self.config["bypasses"]["allow_during_curfew"] = False
        self.scheduler.update_config(self.config)

        st = self.scheduler.evaluate_state(now)
        self.assertEqual(st["reason"], "CURFEW")
        self.assertIsNone(self.scheduler.paused_manual_remaining_seconds)
        self.assertFalse(self.scheduler.paused_manual_is_indefinite)


if __name__ == "__main__":
    unittest.main()

