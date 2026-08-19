# Focus-Guard

> Anti-procrastination and dopamine regulator for Linux (CachyOS / Arch Linux / KDE Plasma 6 & Wayland)

Focus-Guard blocks distracting websites directly at the system level (`/etc/hosts`) with privilege separation, an automated systemd daemon, and a minimalist KDE Plasma StatusNotifier tray applet and dashboard.

---

## Features

- **Boot Cooldown:** Mandatory 30-minute focus block automatically applied when your computer boots up (based on `/proc/uptime`).
- **Night Curfew:** Automated non-negotiable block every night from **23:15 to 07:00** to protect your sleep schedule.
- **Timed Bypasses:** Request temporary 15, 30, or 45-minute breaks directly from the tray or dashboard (strictly restricted during Night Curfew with an emergency friction mechanism).
- **Manual Lock:** Trigger immediate deep work focus sessions whenever needed.
- **Native Settings UI & Dashboard:** Minimalist, adaptive interface matching KDE Plasma 6 Light & Dark themes to manage domains and rules effortlessly.
- **KDE Plasma 6 / Wayland Integration:** Standard `StatusNotifierItem` via PyQt6 with vector icons and transition desktop notifications.
- **Strict Privilege Separation:** The GUI and settings run exclusively as your standard user (`$USER`). Only the system daemon runs with root permissions to update `/etc/hosts`.

---

## Architecture

```
┌────────────────────────────────────────────────────────┐
│  FRONTEND: Tray Applet & Settings UI (PyQt6)           │
│  • Runs as standard user ($USER) in KDE Plasma 6       │
│  • Visual status: Active (Red) / Break (Amber) / Idle  │
│  • Context Menu & Dashboard: Domains, Rules, Bypasses  │
└──────────────────────────┬─────────────────────────────┘
                           │ (IPC: JSON over Unix Socket /run/focus-guard.sock)
┌──────────────────────────▼─────────────────────────────┐
│  BACKEND: Systemd Daemon (Root)                        │
│  • Runs in background as focus-guard.service           │
│  • Atomic, delimited updates to /etc/hosts             │
│  • Enforces Curfew, Uptime Cooldown, and State Machine │
└────────────────────────────────────────────────────────┘
```

---

## Installation & Quick Start

### 1. Requirements (Arch Linux / CachyOS)
```bash
sudo pacman -S python-pyqt6
```

### 2. Install as System Service
Run the automated installation script with `sudo`:
```bash
sudo ./scripts/install.sh
```

This will:
- Install the backend and frontend to `/opt/focus-guard`
- Create `/etc/focus-guard/config.json`
- Enable and start `focus-guard.service` in Systemd
- Add desktop launcher and autostart entries for KDE Plasma

### 3. Launch the Tray Applet
After installation, you can launch the tray applet:
```bash
python3 /opt/focus-guard/client/main.py &
```
*(Or search for **Focus-Guard** in your KDE Application Launcher)*.

---

## Testing Locally (Development Mode)

Run both the daemon and GUI in development mode without `sudo` and without modifying your real `/etc/hosts` file:

```bash
./scripts/run_dev.sh
```

---

## Configuration

Custom domains, curfew hours, and cooldown durations can be adjusted directly from the GUI (Ajustes y Sitios Bloqueados) or in `/etc/focus-guard/config.json`:

```json
{
  "boot_cooldown": {
    "enabled": true,
    "duration_minutes": 30
  },
  "curfew": {
    "enabled": true,
    "start_time": "23:15",
    "end_time": "07:00",
    "allow_bypass": false
  },
  "blocked_domains": [
    "x.com",
    "twitter.com",
    "instagram.com",
    "reddit.com",
    "youtube.com",
    "tiktok.com",
    "facebook.com",
    "twitch.tv",
    "netflix.com"
  ]
}
```

---

## Browser Note: DNS-over-HTTPS (DoH)

Modern web browsers sometimes have **DNS-over-HTTPS (DoH)** enabled by default. Since DoH queries external DNS servers directly, it can bypass `/etc/hosts`.

To ensure Focus-Guard works effectively:
- **Firefox:** Go to `Settings` -> `Privacy & Security` -> `DNS over HTTPS` -> Select **Off** (or "Default Protection").
- **Chrome / Brave:** Go to `Settings` -> `Privacy and security` -> `Security` -> Toggle off "Use secure DNS" or set to OS default.

---

## Uninstallation

To cleanly remove Focus-Guard and restore `/etc/hosts`:
```bash
sudo ./scripts/uninstall.sh
```

---

## License
MIT License.
