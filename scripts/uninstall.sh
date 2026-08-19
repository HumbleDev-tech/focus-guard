#!/usr/bin/env bash
set -e

if [ "$EUID" -ne 0 ]; then
  echo "Error: Please run as root (sudo ./scripts/uninstall.sh)"
  exit 1
fi

echo "=== Uninstalling Focus-Guard ==="

echo "1. Stopping and disabling systemd service..."
systemctl stop focus-guard.service 2>/dev/null || true
systemctl disable focus-guard.service 2>/dev/null || true
rm -f /etc/systemd/system/focus-guard.service
systemctl daemon-reload

echo "2. Cleaning /etc/hosts blocks..."
python3 -c "
import sys; sys.path.insert(0, '/opt/focus-guard')
try:
    from daemon.hosts_manager import HostsManager
    HostsManager('/etc/hosts').remove_block()
    print('Hosts file cleaned.')
except Exception as e:
    print('Could not clean hosts file automatically:', e)
" || true

echo "3. Removing application files..."
rm -rf /opt/focus-guard
rm -f /usr/share/applications/focus-guard.desktop
rm -f /etc/xdg/autostart/focus-guard.desktop
rm -f /run/focus-guard.sock

echo "=== Focus-Guard has been completely uninstalled ==="
