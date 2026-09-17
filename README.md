# Focus-Guard

<div align="center">

![Focus-Guard Banner](resources/icon-active.svg)

### **Friction over Willpower** • Anti-procrastination & Dopamine Regulator for Linux
*System-level website blocking with strict privilege separation, automated kernel/systemd enforcement, and a native KDE Plasma 6 / Wayland desktop applet.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Linux](https://img.shields.io/badge/Platform-Arch%20%7C%20CachyOS%20%7C%20KDE%20Plasma%206-1793d1.svg)](#installation)
[![AUR Package](https://img.shields.io/badge/AUR-focus--guard-blueviolet.svg)](#install-via-aur-arch-linux--cachyos)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-yellow.svg)](https://www.python.org/)
[![GUI: PyQt6 / Wayland](https://img.shields.io/badge/GUI-PyQt6%20%7C%20Wayland-success.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Privacy: 100% Offline](https://img.shields.io/badge/Privacy-100%25%20Offline%20%7C%20Zero%20Telemetry-brightgreen.svg)](PRIVACY.md)

[English](README.md) • [Español](README.es.md) • [Installation](#installation) • [AUR](#install-via-aur-arch-linux--cachyos) • [Architecture](#architecture) • [Privacy](PRIVACY.md)

</div>

---

## The Philosophy: *Friction over Willpower*

Willpower is an exhaustible cognitive resource. When high-dopamine triggers (infinite algorithmic feeds, short-form video platforms, social networks) are just a browser keystroke away, relying solely on self-discipline inevitably leads to friction-fatigue and compulsive tab-opening.

### Why Browser Extensions Fail

Browser-based blockers (e.g., LeechBlock, StayFocusd) fail in real-world dopamine regulation due to three fundamental architectural weaknesses:
1. **Zero Resistance to Disabling:** Deactivating a browser extension takes exactly two clicks in `chrome://extensions` or opening an Incognito / Private window.
2. **Process Isolation:** They only cover one browser. Opening another browser, a development WebView, or an electron app completely bypasses the block.
3. **No Night Protection:** During late-night fatigue, willpower hits its lowest threshold. Extensions provide no friction against being toggled off.

### The Focus-Guard Solution

Focus-Guard enforces **deterministic friction directly at the Linux kernel/resolver level** (`/etc/hosts` mapped to `0.0.0.0`):

| Metric / Capability | Typical Browser Extension | Focus-Guard (System Level) |
| :--- | :--- | :--- |
| **Enforcement Layer** | User-space Browser JavaScript | Kernel OS Resolver (`/etc/hosts`) |
| **Bypass via Incognito / New Profile** | ❌ Trivial (disabled by default) | 🛡️ **Impossible** (system-wide) |
| **Cross-Browser & App Coverage** | ❌ Per-browser only | 🛡️ **100% System-wide** (Firefox, Chrome, Electron, CLI) |
| **Anti-Impulse Deliberate Friction** | ❌ Instant click to disable | 🛡️ **Typing security phrases required** |
| **Night Rest Protection** | ❌ Vulnerable to fatigue | 🛡️ **Hard Night Curfew with emergency barrier** |
| **Startup Defense** | ❌ None | 🛡️ **Automatic Boot Cooldown on PC startup** |
| **Telemetry & Analytics** | ⚠️ Often third-party trackers | 🛡️ **100% Offline, Zero Telemetry** |

---

## Key Features

- 🛡️ **Boot Focus Cooldown:** Automatically blocks distracting websites for the first 30 minutes after turning on your computer (calculated via `/proc/uptime`). Start your workday reading, planning, or executing without algorithmic hijack.
- 🌙 **Automated Night Curfew:** Non-negotiable lock every night (e.g., from **23:15 to 07:00**) to protect your circadian rhythm and sleep schedule.
- ⏱️ **Focus Sessions & Pomodoro:** Instant 25-minute Pomodoro, 50-minute deep work blocks, or indefinite locks triggered in one click from the tray.
- ☕ **Controlled Breaks (Bypasses):** Request temporary 15, 30, or 45-minute pauses during daytime focus. Bypasses are strictly locked during Night Curfew unless you pass an anti-impulse friction challenge.
- ⚡ **Anti-Impulse Security Challenge:** Deleting sites or bypassing curfew requires intentionally typing a configured confirmation phrase, breaking subconscious dopamine loops.
- 🎯 **Selective Locking:** Lock specific high-friction sites (e.g., only `youtube.com` and `reddit.com`) while keeping reference sites open.
- 🌐 **Full Internationalization (i18n):** Native **Español** and **English** with real-time on-the-fly language switching.
- 🎨 **Adaptive Design System:** Clean vector iconography (Lucide-inspired) and harmonious Light / Dark themes tailored for KDE Plasma 6 (Breeze / Wayland).
- 🔒 **Zero Telemetry & 100% Offline:** Read our [PRIVACY.md](PRIVACY.md) manifest. No remote servers, no cloud dependency, no tracking.

---

## Architecture & Privilege Separation

Focus-Guard employs a strict multi-tier privilege separation architecture:

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND: Focus-Guard Tray & Dashboard (PyQt6 / Wayland)   │
│  • Runs entirely as standard, unprivileged user ($USER)      │
│  • StatusNotifierItem tray applet with dynamic vector icons │
│  • 4 Main Views: Domains, Selective Lock, Rules, Dashboard  │
│  • Zero sudo required to launch or view status              │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ Local UNIX Socket IPC (/var/run/focus-guard.sock)
                               │ Mode 0666 • Structured JSON commands
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  BACKEND: focus-guard.service (Systemd Daemon / Root)       │
│  • Background daemon running as root                        │
│  • Atomic /etc/hosts updates using 0.0.0.0 sinkhole entries │
│  • State machine enforcing Curfew, Boot Cooldown & Timers   │
│  • Automatic rollback backup saved to /etc/hosts.fg.bak     │
└─────────────────────────────────────────────────────────────┘
```

---

## Installation

### Install via AUR (Arch Linux / CachyOS)

Focus-Guard is prepared for standard Arch Linux packaging via the AUR:

```bash
# Using yay
yay -S focus-guard

# Using paru
paru -S focus-guard

# Or build manually using makepkg
git clone https://aur.archlinux.org/focus-guard.git
cd focus-guard
makepkg -si
```

Enable and start the system service:
```bash
sudo systemctl enable --now focus-guard.service
```

---

### Manual / Git Installation

If you are running another Linux distribution or installing directly from source:

```bash
# 1. Clone repository
git clone https://github.com/HumbleDev-tech/focus-guard.git
cd focus-guard

# 2. Install dependencies (Arch Linux / CachyOS)
sudo pacman -S python-pyqt6

# 3. Run the automated installer
sudo ./scripts/install.sh
```

---

## CLI & Service Management

Focus-Guard includes a command-line interface (`focus-guard-cli`) for headless or scripted environments:

```bash
# Check current daemon state, active timers, and blocked domains
focus-guard-cli status

# Trigger an immediate 25-minute Pomodoro focus block
focus-guard-cli lock --minutes 25

# Lock sites indefinitely
focus-guard-cli lock

# Request a 15-minute temporary break
focus-guard-cli bypass --minutes 15

# Cancel an active break and resume protection
focus-guard-cli cancel-bypass

# Unlock sites (only permitted during manual lock / free time)
focus-guard-cli unlock

# Manage the system daemon
sudo systemctl status focus-guard.service
sudo systemctl restart focus-guard.service
```

---

## Configuration

Configuration is stored in `/etc/focus-guard/config.json`. You can modify it visually via the native desktop dashboard or edit it directly:

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
  "bypasses": {
    "enabled": true,
    "allow_emergency_during_curfew": true,
    "emergency_phrase": "necesito desbloqueo de emergencia"
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

## Important: DNS-over-HTTPS (DoH) in Web Browsers

Because Focus-Guard operates by intercepting DNS queries via `/etc/hosts`, browsers configured with **DNS-over-HTTPS (DoH)** bypass local operating system lookups.

To ensure Focus-Guard blocks websites reliably:
- **Mozilla Firefox:** Go to `Settings` → `Privacy & Security` → `DNS over HTTPS` → Choose **Off** (or "Default Protection").
- **Google Chrome / Chromium / Brave:** Go to `Settings` → `Privacy and security` → `Security` → Turn off **"Use secure DNS"** (or select "Use current provider / System DNS").

---

## Privacy & Security

Focus-Guard is committed to total privacy:
- **100% Offline:** No cloud connections, analytics, or licensing checks.
- **Local Storage Only:** Everything is stored locally in `/etc/focus-guard/` and `~/.config/focus-guard/`.
- **Delimited Hosts Injection:** Focus-Guard never overwrites custom user host mappings; it injects and removes entries within strict `# FOCUS-GUARD-BEGIN` and `# FOCUS-GUARD-END` markers.

Read our complete policy in [PRIVACY.md](PRIVACY.md).

---

## License

Focus-Guard is open-source software released under the [MIT License](LICENSE).
