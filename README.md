# 🛡️ Focus-Guard

> **Anti-procrastination and dopamine regulator for Linux (CachyOS / Arch Linux / KDE Plasma 6 & Wayland)**

Focus-Guard blocks distracting websites directly at the system level (`/etc/hosts`) with privilege separation, an automated systemd daemon, and a modern KDE Plasma StatusNotifier tray applet.

---

## ✨ Features

- **🚀 Boot Cooldown:** Mandatory 30-minute focus block automatically applied when your computer boots up or the daemon starts.
- **🌙 Night Curfew (Toque de Queda):** Non-negotiable block every night from **23:15 to 07:00** to protect your sleep schedule.
- **☕ Timed Bypasses:** Need a quick break? Request a temporary 15, 30, or 45-minute bypass directly from the system tray (bypasses are strictly disallowed during Night Curfew).
- **🔒 Manual Lock:** Trigger immediate focus sessions whenever you need to get into deep work.
- **🎨 KDE Plasma 6 / Wayland Native:** Uses standard `StatusNotifierItem` via PyQt6 with dynamic vector icons and informative status tooltips.
- **🛡️ Secure Privilege Separation:** The GUI runs strictly as your unprivileged user. Only the lightweight daemon runs as root via Systemd to manage `/etc/hosts`.

---

## 🏛️ Architecture

```
┌────────────────────────────────────────────────────────┐
│  FRONTEND: Tray Applet (PyQt6 / QSystemTrayIcon)       │
│  • Runs as standard user ($USER) in KDE Plasma 6       │
│  • Visual status: Active (Red) / Break (Green)         │
│  • Context Menu: Timed Bypasses, Manual Lock, Info     │
└──────────────────────────┬─────────────────────────────┘
                           │ (IPC: JSON over Unix Socket /run/focus-guard.sock)
┌──────────────────────────▼─────────────────────────────┐
│  BACKEND: Systemd Daemon (Root)                        │
│  • Runs in background as focus-guard.service           │
│  • Atomic, safe updates to /etc/hosts with delimiters  │
│  • Enforces Curfew, Boot Cooldown, and Timers          │
└────────────────────────────────────────────────────────┘
```

---

## 🚀 Installation & Quick Start

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
*(Or simply search for **Focus-Guard** in your KDE Application Launcher)*.

---

## 🧪 Testing Locally (Development Mode)

You can run both the daemon and the GUI locally without `sudo` and without modifying your real `/etc/hosts` file using mock files in `/tmp`:

```bash
./scripts/run_dev.sh
```

---

## ⚙️ Configuration

Custom domains, curfew hours, and cooldown durations can be adjusted in `/etc/focus-guard/config.json` (or `config/default_config.json`):

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

## 🌐 Browser Note: DNS-over-HTTPS (DoH)

Modern web browsers (such as Firefox, Chrome, or Brave) sometimes have **DNS-over-HTTPS (DoH)** enabled by default. Since DoH queries external DNS servers directly, it can bypass `/etc/hosts`.

To ensure Focus-Guard works effectively:
- **Firefox:** Go to `Settings` ➔ `Privacy & Security` ➔ `DNS over HTTPS` ➔ Select **Off** (or "Default Protection").
- **Chrome / Brave:** Go to `Settings` ➔ `Privacy and security` ➔ `Security` ➔ Toggle off "Use secure DNS" or set to OS default.

---

## 🗑️ Uninstallation

To cleanly remove Focus-Guard and restore `/etc/hosts`:
```bash
sudo ./scripts/uninstall.sh
```

---

## 📄 License
MIT License.
