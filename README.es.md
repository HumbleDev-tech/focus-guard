# Focus-Guard

<div align="center">

![Focus-Guard Banner](resources/icon-active.svg)

### **Fricción sobre Fuerza de Voluntad** • Regulador Anti-procrastinación y Dopamina para Linux
*Bloqueo de sitios web a nivel de sistema con estricta separación de privilegios, ejecución automática vía systemd y applet nativo para KDE Plasma 6 / Wayland.*

[![Licencia: MIT](https://img.shields.io/badge/Licencia-MIT-blue.svg)](LICENSE)
[![Plataforma: Linux](https://img.shields.io/badge/Plataforma-Arch%20%7C%20CachyOS%20%7C%20KDE%20Plasma%206-1793d1.svg)](#instalación)
[![Paquete AUR](https://img.shields.io/badge/AUR-focus--guard-blueviolet.svg)](#instalación-mediante-aur-arch-linux--cachyos)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-yellow.svg)](https://www.python.org/)
[![GUI: PyQt6 / Wayland](https://img.shields.io/badge/GUI-PyQt6%20%7C%20Wayland-success.svg)](https://www.riverbankcomputing.com/software/pyqt/)
[![Privacidad: 100% Offline](https://img.shields.io/badge/Privacidad-100%25%20Offline%20%7C%20Cero%20Telemetr%C3%ADa-brightgreen.svg)](PRIVACY.md)

[English](README.md) • [Español](README.es.md) • [Instalación](#instalación) • [AUR](#instalación-mediante-aur-arch-linux--cachyos) • [Arquitectura](#arquitectura-y-separación-de-privilegios) • [Privacidad](PRIVACY.md)

</div>

---

## Filosofía: *Fricción sobre Fuerza de Voluntad*

La fuerza de voluntad es un recurso cognitivo biológico finito. Cuando los disparadores de alta dopamina (feeds algorítmicos infinitos, videos cortos, redes sociales) están a un solo clic de distancia en el navegador, depender exclusivamente del autocontrol conduce inevitablemente a la fatiga por fricción y a la apertura compulsiva de pestañas.

### Por qué fallan las extensiones de navegador

Los bloqueadores basados en extensiones de navegador (como LeechBlock o StayFocusd) fracasan en la regulación real del comportamiento debido a tres fallas arquitectónicas fundamentales:

1. **Cero resistencia al desactivarse:** Apagar una extensión toma exactamente dos clics en la barra de extensiones o simplemente abrir una ventana de incógnito/privada.
2. **Aislamiento por proceso:** Solo cubren un navegador específico. Abrir un segundo navegador, un WebView de desarrollo o una aplicación Electron evade por completo el bloqueo.
3. **Vulnerabilidad al cansancio nocturno:** Durante las últimas horas de la noche, la fuerza de voluntad llega a su punto más bajo. Las extensiones no ofrecen ninguna fricción cognitiva que impida deshabilitarlas en un arranque impulsivo.

### La Solución de Focus-Guard

Focus-Guard aplica **fricción determinista directamente en la capa de resolución del kernel de Linux** (`/etc/hosts` enrutado a `0.0.0.0`):

| Métrica / Capacidad | Extensión Típica de Navegador | Focus-Guard (Nivel de Sistema) |
| :--- | :--- | :--- |
| **Capa de Ejecución** | JavaScript en espacio de usuario del navegador | Resolución del Kernel del SO (`/etc/hosts`) |
| **Bypass en Modo Incógnito / Perfil Nuevo** | ❌ Trivial (desactivado por defecto) | 🛡️ **Imposible** (a nivel de todo el sistema) |
| **Cobertura Multinavegador y Apps** | ❌ Solo el navegador actual | 🛡️ **100% Global** (Firefox, Chrome, Electron, CLI) |
| **Fricción Deliberada Anti-Impulso** | ❌ Desactivación inmediata con 1 clic | 🛡️ **Requiere escribir frases de confirmación** |
| **Protección del Descanso Nocturno** | ❌ Vulnerable al cansancio mental | 🛡️ **Toque de Queda Nocturno con barrera estricta** |
| **Defensa en el Arranque (Boot)** | ❌ Ninguna | 🛡️ **Enfoque de Inicio automático tras encender el PC** |
| **Telemetría y Analíticas** | ⚠️ Frecuentemente recopilan datos | 🛡️ **100% Offline, Cero Telemetría** |

---

## Características Principales

- 🛡️ **Enfoque de Inicio (Boot Cooldown):** Bloquea automáticamente las distracciones durante los primeros 30 minutos tras encender el ordenador (calculado mediante `/proc/uptime`). Empieza tu jornada leyendo, planificando o programando sin secuestro algorítmico.
- 🌙 **Toque de Queda Nocturno (Curfew):** Bloqueo programado automático cada noche (por ejemplo, de **23:15 a 07:00**) para proteger tus ritmos circadianos y horario de descanso.
- ⏱️ **Sesiones de Enfoque y Pomodoro:** Bloques de trabajo profundo instantáneos de 25 minutos (Pomodoro), 50 minutos o tiempo indefinido desde el applet de la bandeja del sistema.
- ☕ **Pausas y Descansos Controlados (Bypasses):** Solicita recreos temporales de 15, 30 o 45 minutos durante el día. Los descansos se bloquean de manera estricta durante el Toque de Queda nocturno a menos que superes un reto de fricción.
- ⚡ **Desafío de Seguridad Anti-Impulso:** Eliminar dominios o solicitar descansos de emergencia requiere escribir conscientemente una frase configurada, interrumpiendo el bucle subconsciente de dopamina.
- 🎯 **Bloqueo Selectivo:** Bloquea sitios específicos de distracción extrema (por ejemplo, solo `youtube.com` y `reddit.com`) manteniendo disponibles plataformas de consulta técnica (como GitHub o StackOverflow).
- 🌐 **Internacionalización Completa (i18n):** Soporte nativo y conmutación en caliente en tiempo real entre **Español** e **Inglés**.
- 🎨 **Diseño Moderno y Adaptativo:** Iconografía vectorial inspirada en Lucide y paletas armónicas en modos Claro y Oscuro adaptadas a KDE Plasma 6 (Breeze / Wayland).
- 🔒 **Cero Telemetría y 100% Offline:** Consulta nuestro manifiesto [PRIVACY.md](PRIVACY.md). Sin servidores remotos, sin nube y sin rastreo.

---

## Arquitectura y Separación de Privilegios

Focus-Guard implementa un modelo de seguridad multi-nivel con estricta separación de privilegios:

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND: Bandeja y Panel Focus-Guard (PyQt6 / Wayland)    │
│  • Se ejecuta como usuario estándar sin privilegios ($USER) │
│  • Applet StatusNotifierItem con iconos vectoriales         │
│  • 4 Vistas: Sitios, Bloqueo Selectivo, Reglas, Estado      │
│  • Cero sudo requerido para abrir o consultar el estado     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ Socket UNIX local (/var/run/focus-guard.sock)
                               │ Modo 0666 • Mensajes JSON estructurados
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  BACKEND: focus-guard.service (Demonio Systemd / Root)      │
│  • Demonio en segundo plano ejecutado como root             │
│  • Modificación atómica de /etc/hosts usando 0.0.0.0        │
│  • Máquina de estados para Toque de Queda, Arranque y Timer │
│  • Respaldo y restauración segura en /etc/hosts.fg.bak      │
└─────────────────────────────────────────────────────────────┘
```

---

## Instalación

### Instalación mediante AUR (Arch Linux / CachyOS)

Focus-Guard cuenta con empaquetado oficial para el repositorio de usuarios de Arch (AUR):

```bash
# Mediante yay
yay -S focus-guard

# Mediante paru
paru -S focus-guard

# O compilando manualmente mediante makepkg
git clone https://aur.archlinux.org/focus-guard.git
cd focus-guard
makepkg -si
```

Habilita e inicia el servicio del sistema:
```bash
sudo systemctl enable --now focus-guard.service
```

---

### Instalación Manual / Git

Para otras distribuciones de Linux o instalación directa desde el código fuente:

```bash
# 1. Clonar el repositorio
git clone https://github.com/HumbleDev-tech/focus-guard.git
cd focus-guard

# 2. Instalar dependencias (Arch Linux / CachyOS)
sudo pacman -S python-pyqt6

# 3. Ejecutar el instalador automatizado
sudo ./scripts/install.sh
```

---

## Interfaz de Línea de Comandos (CLI)

Focus-Guard incluye una herramienta de terminal (`focus-guard-cli`) para entornos headless o automatización:

```bash
# Consultar el estado actual del demonio, temporizadores y sitios bloqueados
focus-guard-cli status

# Iniciar un bloque de concentración Pomodoro de 25 minutos
focus-guard-cli lock --minutes 25

# Bloquear sitios indefinidamente
focus-guard-cli lock

# Solicitar una pausa temporal de 15 minutos
focus-guard-cli bypass --minutes 15

# Cancelar una pausa activa y retomar el bloqueo protector
focus-guard-cli cancel-bypass

# Desbloquear manualmente (permitido solo en bloqueo manual o modo libre)
focus-guard-cli unlock

# Gestionar el servicio del sistema
sudo systemctl status focus-guard.service
sudo systemctl restart focus-guard.service
```

---

## Configuración

La configuración del sistema se almacena en `/etc/focus-guard/config.json`. Puedes modificarla visualmente desde el panel de control o editarla directamente:

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

## Aviso Importante: DNS-over-HTTPS (DoH) en Navegadores

Dado que Focus-Guard funciona interceptando resoluciones de nombres en `/etc/hosts`, los navegadores configurados con **DNS seguro / DNS-over-HTTPS (DoH)** evaden el archivo hosts del sistema operativo.

Para garantizar que Focus-Guard bloquee los sitios correctamente:
- **Mozilla Firefox:** Ve a `Ajustes` → `Privacidad y Seguridad` → `DNS sobre HTTPS` → Selecciona **Desactivado** (o "Protección predeterminada").
- **Google Chrome / Chromium / Brave:** Ve a `Configuración` → `Privacidad y seguridad` → `Seguridad` → Desactiva **"Usar DNS seguro"** (o selecciona el proveedor del sistema operativo).

---

## Privacidad y Seguridad

Focus-Guard garantiza privacidad absoluta:
- **100% Offline:** Sin conexiones en la nube, sin analíticas ni validación remota.
- **Almacenamiento Local Únicamente:** Toda la información reside en `/etc/focus-guard/` y `~/.config/focus-guard/`.
- **Inyección Segura y Delimitada en Hosts:** Nunca sobreescribe entradas del usuario; inserta y retira bloques delimitados por etiquetas `# FOCUS-GUARD-BEGIN` y `# FOCUS-GUARD-END`.

Consulta la política completa en [PRIVACY.md](PRIVACY.md).

---

## Licencia

Focus-Guard es software de código abierto publicado bajo la [Licencia MIT](LICENSE).
