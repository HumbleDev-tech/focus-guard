# Privacy Policy & Architecture Transparency / Política de Privacidad

**Last Updated:** September 2026  
**Focus-Guard** is designed from first principles around **Data Sovereignty, Zero Telemetry, and Complete Offline Operation**.

[English](PRIVACY.md) • [Español](PRIVACY.es.md)

---

## 1. Zero Network Activity (100% Offline)

Focus-Guard contains **no network client calls**, **no analytics SDKs**, **no crash reporters**, and **no remote telemetry**.

- **No Remote Servers:** Focus-Guard does not communicate with any cloud service, external server, or third-party endpoint.
- **No Licensing Checks:** The software operates fully standalone without license validation, phone-home mechanisms, or registration.
- **Local Domain Inspection:** When you add websites to your blocklist, domains are parsed and validated entirely on your local machine. No external DNS or reputation databases are consulted over the network.

---

## 2. Local Storage & Data Sovereignty

All configuration files, state logs, and preferences reside exclusively on your local filesystem:

| Path | Ownership / Scope | Purpose |
| :--- | :--- | :--- |
| `/etc/focus-guard/config.json` | `root:root` (Read-only to users) | System-wide blocking rules, schedules, and security phrases. |
| `/var/run/focus-guard.sock` | `root:root` (Mode `0666`) | Local UNIX domain socket for inter-process communication (IPC). |
| `/var/lib/focus-guard/runtime_state.json` | `root:root` | Ephemeral state tracking current locks, timers, and scheduled end times. |
| `/etc/hosts.fg.bak` | `root:root` | Safe rollback backup of your original `/etc/hosts` file. |
| `~/.config/focus-guard/` / `QSettings` | User desktop session | GUI client visual preferences (Dark/Light theme, interface language). |

No telemetry, personal identifiable information (PII), or web browsing histories are ever collected, recorded, or written to disk.

---

## 3. Privilege Separation & Security Model

Focus-Guard implements strict privilege separation between the background enforcement engine and the desktop UI:

```mermaid
graph LR
    User[Non-privileged User Desktop] -->|IPC via UNIX Socket| Client[Focus-Guard Tray / GUI]
    Client -->|Local Commands: /var/run/focus-guard.sock| Daemon[focus-guard.service (root)]
    Daemon -->|Atomic File Replacement| Hosts[/etc/hosts]
```

1. **System Daemon (`focus-guard.service`):**
   - Runs as `root` because modifying `/etc/hosts` requires superuser access on Linux.
   - Restricts its file operations strictly to `/etc/hosts` and `/etc/focus-guard/`.
   - Never exposes a TCP or UDP network port; communication is strictly isolated to a local UNIX domain socket (`/var/run/focus-guard.sock`).
2. **Desktop Client (`focus-guard-tray`):**
   - Runs as a **standard, unprivileged user**.
   - Requires **zero sudo privileges**. It cannot modify system files directly, only issuing structured commands over the local UNIX socket.
   - Employs anti-impulse confirmation phrases directly in memory; phrases are checked against the daemon's local configuration.

---

## 4. DNS-over-HTTPS (DoH) Notice

Focus-Guard operates at the kernel/OS resolver level via `/etc/hosts`.

> [!NOTE]
> Modern web browsers (such as Firefox, Chrome, or Brave) may enable **DNS-over-HTTPS (DoH)** or "Secure DNS" by default, bypassing the local `/etc/hosts` file.
> To ensure Focus-Guard blocks distracting websites reliably, your browser's DNS settings should be configured to use your **System Resolver** (e.g., in Firefox: *Settings → Privacy & Security → DNS over HTTPS → "Off" or "Default Protection"*).

---

## 5. Auditability & Open Source Verification

You can verify Focus-Guard's network isolation at any time using standard Linux auditing tools:

```bash
# Verify no network sockets are opened by Focus-Guard
sudo ss -tulpn | grep focus-guard

# Monitor file descriptors and socket connections of the daemon
sudo lsof -c focus-guard

# Inspect all local IPC communications
socat - UNIX-CONNECT:/var/run/focus-guard.sock
```

Focus-Guard is 100% Free and Open Source Software (FOSS). Inspect the code, audit the IPC protocol, and adapt it to your workflow.

---

*Focus-Guard guarantees absolute privacy. Your focus habits, schedule, and blocklists belong strictly to you.*
