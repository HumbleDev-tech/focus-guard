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

echo "2. Setting up configuration in /etc/focus-guard..."
mkdir -p /etc/focus-guard
if [ ! -f /etc/focus-guard/config.json ]; then
  cp "$SOURCE_DIR/config/default_config.json" /etc/focus-guard/config.json
  echo "   Default config copied to /etc/focus-guard/config.json"
else
  echo "   Preserving existing /etc/focus-guard/config.json"
fi

echo "3. Installing systemd service..."
cp "$SOURCE_DIR/systemd/focus-guard.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now focus-guard.service

echo "4. Creating desktop entry for user autostart / launcher..."
mkdir -p /usr/share/applications
cat << 'DESKTOP_EOF' > /usr/share/applications/focus-guard.desktop
[Desktop Entry]
Name=Focus-Guard
Comment=Anti-procrastination website blocker and focus manager
Exec=python3 /opt/focus-guard/client/main.py
Icon=/opt/focus-guard/resources/icon-active.svg
Terminal=false
Type=Application
Categories=Utility;System;
StartupNotify=false
DESKTOP_EOF

echo "5. Creating autostart entry for KDE Plasma / Wayland..."
mkdir -p /etc/xdg/autostart
cp /usr/share/applications/focus-guard.desktop /etc/xdg/autostart/

echo ""
echo "=== Installation Complete! ==="
echo "Status of Daemon Service:"
systemctl status focus-guard.service --no-pager
echo ""
echo "To launch the tray applet now as your normal user, run:"
echo "   python3 /opt/focus-guard/client/main.py &"
