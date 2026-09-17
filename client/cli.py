"""
Focus-Guard Command-Line Interface (CLI).
Allows headless or terminal inspection and control of the Focus-Guard daemon.
"""
import os
import sys
import argparse
import json

_this_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_this_dir, "..")))

from client.ipc_client import FocusIPCClient


def format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "0s"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    parts = []
    if h > 0:
        parts.append(f"{h}h")
    if m > 0:
        parts.append(f"{m}m")
    if s > 0 or not parts:
        parts.append(f"{s}s")
    return " ".join(parts)


def cmd_status(ipc: FocusIPCClient, args) -> int:
    res = ipc.get_status()
    if args.json:
        print(json.dumps(res, indent=2))
        return 0 if res.get("status") == "ok" else 1

    if res.get("status") != "ok":
        print(f"Error: Could not connect to Focus-Guard daemon. ({res.get('error', 'Daemon offline')})")
        return 1

    state = res.get("state", "UNKNOWN")
    reason = res.get("reason", "UNKNOWN")
    is_blocking = res.get("is_blocking", False)
    rem = res.get("remaining_seconds", 0)
    target = res.get("target_time_str", "")
    domains_count = res.get("domains_count", 0)
    is_selective = res.get("is_selective", False)
    selective_domains = res.get("selective_domains", [])

    print("=== Focus-Guard Status ===")
    print(f"State:        {state}")
    print(f"Reason:       {reason}")
    print(f"Blocking:     {'YES (Distractions blocked)' if is_blocking else 'NO (Free navigation)'}")
    if rem > 0:
        target_info = f" (until {target})" if target else ""
        print(f"Remaining:    {format_duration(rem)}{target_info}")
    if is_selective:
        print(f"Selective:    YES ({len(selective_domains)} sites: {', '.join(selective_domains)})")
    else:
        print(f"Total Sites:  {domains_count}")
    return 0


def cmd_lock(ipc: FocusIPCClient, args) -> int:
    mins = args.minutes or 0
    res = ipc.lock_now(duration_minutes=mins)
    if res.get("status") == "ok":
        if mins > 0:
            print(f"Focus-Guard: Focus lock activated for {mins} minutes.")
        else:
            print("Focus-Guard: Focus lock activated indefinitely.")
        return 0
    else:
        print(f"Error: {res.get('message', res.get('error', 'Failed to lock'))}")
        return 1


def cmd_unlock(ipc: FocusIPCClient, args) -> int:
    res = ipc.unlock_now()
    if res.get("status") == "ok":
        print("Focus-Guard: Sites successfully unlocked.")
        return 0
    else:
        print(f"Error: {res.get('message', res.get('error', 'Unlock not permitted at this time.'))}")
        return 1


def cmd_bypass(ipc: FocusIPCClient, args) -> int:
    mins = args.minutes
    res = ipc.request_bypass(duration_minutes=mins)
    if res.get("status") == "ok":
        print(f"Focus-Guard: Temporary break granted for {mins} minutes.")
        return 0
    else:
        print(f"Error: {res.get('message', res.get('error', 'Failed to request break.'))}")
        return 1


def cmd_cancel_bypass(ipc: FocusIPCClient, args) -> int:
    res = ipc.cancel_bypass()
    if res.get("status") == "ok":
        print("Focus-Guard: Break ended. Focus protection resumed.")
        return 0
    else:
        print(f"Error: {res.get('message', res.get('error', 'Failed to cancel break.'))}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        prog="focus-guard-cli",
        description="Command-line interface for the Focus-Guard daemon"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # status
    p_status = subparsers.add_parser("status", help="Show current daemon state and active timer")
    p_status.add_argument("--json", action="store_true", help="Output raw JSON response")

    # lock
    p_lock = subparsers.add_parser("lock", help="Start a manual focus session")
    p_lock.add_argument("--minutes", "-m", type=int, default=0, help="Duration in minutes (0 for indefinite)")

    # unlock
    subparsers.add_parser("unlock", help="Release manual focus lock")

    # bypass
    p_bypass = subparsers.add_parser("bypass", help="Request a temporary break")
    p_bypass.add_argument("--minutes", "-m", type=int, choices=[15, 30, 45], default=15, help="Break duration in minutes")

    # cancel-bypass
    subparsers.add_parser("cancel-bypass", help="Cancel active break and re-enable blocking")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    ipc = FocusIPCClient()
    commands = {
        "status": cmd_status,
        "lock": cmd_lock,
        "unlock": cmd_unlock,
        "bypass": cmd_bypass,
        "cancel-bypass": cmd_cancel_bypass,
    }

    handler = commands.get(args.command)
    if handler:
        sys.exit(handler(ipc, args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
