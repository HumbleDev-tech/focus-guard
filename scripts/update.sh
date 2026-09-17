#!/usr/bin/env bash
set -e

echo "=== Focus-Guard Updater ==="

if [ "$EUID" -ne 0 ]; then
  echo "Error: Debes ejecutar este script con permisos de root."
  echo "Uso: sudo ./scripts/update.sh"
  exit 1
fi

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "1. Sincronizando archivos del código hacia /opt/focus-guard..."
mkdir -p /opt/focus-guard
cp -rf "$SOURCE_DIR/daemon" /opt/focus-guard/
cp -rf "$SOURCE_DIR/client" /opt/focus-guard/
cp -rf "$SOURCE_DIR/resources" /opt/focus-guard/
cp -rf "$SOURCE_DIR/config" /opt/focus-guard/

echo "2. Actualizando archivo de servicio systemd y enlaces ejecutables..."
chmod +x /opt/focus-guard/daemon/focus_daemon.py /opt/focus-guard/client/main.py /opt/focus-guard/client/cli.py
ln -sf /opt/focus-guard/daemon/focus_daemon.py /usr/bin/focus-guard-daemon
ln -sf /opt/focus-guard/client/main.py /usr/bin/focus-guard-tray
ln -sf /opt/focus-guard/client/cli.py /usr/bin/focus-guard-cli
cp -f "$SOURCE_DIR/systemd/focus-guard.service" /etc/systemd/system/
systemctl daemon-reload

echo "3. Reiniciando el demonio Focus-Guard..."
systemctl restart focus-guard.service

echo ""
echo "=== ¡Actualización Completada con Éxito! ==="
systemctl status focus-guard.service --no-pager
echo ""
echo "Los últimos cambios del cliente y demonio ya están instalados en el sistema."
echo "Para abrir la interfaz con los últimos cambios:"
echo "   - Ábrela desde el lanzador de aplicaciones de tu escritorio, o"
echo "   - Ejecuta: python3 /opt/focus-guard/client/main.py &"
