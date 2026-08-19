#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Running Focus-Guard in Development Mode ==="
echo "Mock Hosts File: /tmp/focus_guard_dev_hosts"
echo "Mock Socket:     /tmp/focus_guard_dev.sock"

# Initialize mock hosts file if it doesn't exist
if [ ! -f /tmp/focus_guard_dev_hosts ]; then
  echo -e "127.0.0.1 localhost\n::1 localhost" > /tmp/focus_guard_dev_hosts
fi

# Clean previous socket
rm -f /tmp/focus_guard_dev.sock

echo "Starting Daemon in background..."
python3 "$DIR/daemon/focus_daemon.py" --dev &
DAEMON_PID=$!

trap "echo 'Stopping dev daemon (PID $DAEMON_PID)...'; kill $DAEMON_PID 2>/dev/null || true" EXIT

sleep 1

echo "Starting Tray Applet..."
python3 "$DIR/client/main.py" --dev

