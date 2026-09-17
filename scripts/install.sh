#!/usr/bin/env bash
set -e

echo "=== Focus-Guard Installer for Arch / CachyOS / Linux ==="

if [ "$EUID" -ne 0 ]; then
  echo "Error: Please run as root (sudo ./scripts/install.sh)"
  exit 1
fi

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "1. Installing files to /opt/focus-guard..."
mkdir -p /opt/focus-guard
cp -r "$SOURCE_DIR/daemon" /opt/focus-guard/
cp -r "$SOURCE_DIR/client" /opt/focus-guard/
cp -r "$SOURCE_DIR/resources" /opt/focus-guard/
cp -r "$SOURCE_DIR/config" /opt/focus-guard/

echo "2. Setting up executable binaries in /usr/bin..."
chmod +x /opt/focus-guard/daemon/focus_daemon.py /opt/focus-guard/client/main.py /opt/focus-guard/client/cli.py
ln -sf /opt/focus-guard/daemon/focus_daemon.py /usr/bin/focus-guard-daemon
ln -sf /opt/focus-guard/client/main.py /usr/bin/focus-guard-tray
ln -sf /opt/focus-guard/client/cli.py /usr/bin/focus-guard-cli

echo "3. Installing icons and desktop files..."
mkdir -p /usr/share/icons/hicolor/scalable/apps
cp "$SOURCE_DIR/resources/icon-active.svg" /usr/share/icons/hicolor/scalable/apps/focus-guard.svg 2>/dev/null || true
mkdir -p /usr/share/applications
cp "$SOURCE_DIR/resources/focus-guard.desktop" /usr/share/applications/focus-guard.desktop

echo "4. Setting up configuration in /etc/focus-guard..."
mkdir -p /etc/focus-guard
if [ ! -f /etc/focus-guard/config.json ]; then
  cp "$SOURCE_DIR/config/default_config.json" /etc/focus-guard/config.json
  echo "   Default config copied to /etc/focus-guard/config.json"
else
  echo "   Preserving existing /etc/focus-guard/config.json"
fi

echo "5. Installing systemd service..."
cp "$SOURCE_DIR/systemd/focus-guard.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable focus-guard.service
systemctl restart focus-guard.service

echo "6. Creating autostart entry for KDE Plasma / Wayland..."
mkdir -p /etc/xdg/autostart
cp /usr/share/applications/focus-guard.desktop /etc/xdg/autostart/

echo ""
echo "=== Installation Complete! ==="
echo "Status of Daemon Service:"
systemctl status focus-guard.service --no-pager
echo ""
echo "To launch the tray applet now as your normal user, run:"
echo "   python3 /opt/focus-guard/client/main.py &"
