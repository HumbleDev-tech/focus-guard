"""
Tests for focus-guard-cli command-line tool.
"""
import unittest
from unittest.mock import MagicMock, patch
import io
import sys
from client.cli import main, format_duration


class TestFocusCLI(unittest.TestCase):
    def test_format_duration(self):
        self.assertEqual(format_duration(0), "0s")
        self.assertEqual(format_duration(45), "45s")
        self.assertEqual(format_duration(120), "2m")
        self.assertEqual(format_duration(125), "2m 5s")
        self.assertEqual(format_duration(3600), "1h")
        self.assertEqual(format_duration(3665), "1h 1m 5s")

    @patch("client.cli.FocusIPCClient")
    def test_status_command(self, mock_ipc_cls):
        mock_ipc = mock_ipc_cls.return_value
        mock_ipc.get_status.return_value = {
            "status": "ok",
            "state": "LOCKED",
            "reason": "CURFEW",
            "is_blocking": True,
            "remaining_seconds": 3600,
            "target_time_str": "07:00",
            "domains_count": 9,
            "is_selective": False
        }

        with patch("sys.argv", ["focus-guard-cli", "status"]):
            with patch("sys.stdout", new_callable=io.StringIO) as fake_out:
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 0)
                output = fake_out.getvalue()
                self.assertIn("Focus-Guard Status", output)
                self.assertIn("LOCKED", output)
                self.assertIn("CURFEW", output)

    @patch("client.cli.FocusIPCClient")
    def test_lock_command(self, mock_ipc_cls):
        mock_ipc = mock_ipc_cls.return_value
        mock_ipc.lock_now.return_value = {"status": "ok"}

        with patch("sys.argv", ["focus-guard-cli", "lock", "--minutes", "25"]):
            with patch("sys.stdout", new_callable=io.StringIO) as fake_out:
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 0)
                mock_ipc.lock_now.assert_called_once_with(duration_minutes=25)
                self.assertIn("25 minutes", fake_out.getvalue())

    @patch("client.cli.FocusIPCClient")
    def test_bypass_command(self, mock_ipc_cls):
        mock_ipc = mock_ipc_cls.return_value
        mock_ipc.request_bypass.return_value = {"status": "ok"}

        with patch("sys.argv", ["focus-guard-cli", "bypass", "--minutes", "15"]):
            with patch("sys.stdout", new_callable=io.StringIO) as fake_out:
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 0)
                mock_ipc.request_bypass.assert_called_once_with(duration_minutes=15)
                self.assertIn("15 minutes", fake_out.getvalue())

    @patch("client.cli.FocusIPCClient")
    def test_cancel_bypass_command(self, mock_ipc_cls):
        mock_ipc = mock_ipc_cls.return_value
        mock_ipc.cancel_bypass.return_value = {"status": "ok"}

        with patch("sys.argv", ["focus-guard-cli", "cancel-bypass"]):
            with patch("sys.stdout", new_callable=io.StringIO) as fake_out:
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 0)
                mock_ipc.cancel_bypass.assert_called_once()
                self.assertIn("Break ended", fake_out.getvalue())


if __name__ == "__main__":
    unittest.main()
