# Política de Privacidad y Transparencia de Arquitectura

**Última Actualización:** Septiembre 2026  
**Focus-Guard** ha sido concebido desde sus primeros principios en torno a la **Soberanía de Datos, Cero Telemetría y Operación 100% Fuera de Línea (Offline)**.

[English](PRIVACY.md) • [Español](PRIVACY.es.md)

---

## 1. Cero Actividad de Red (100% Offline)

Focus-Guard **no contiene llamadas a clientes de red**, **no incluye SDKs de analítica**, **no posee generadores de reportes de fallos en la nube** y **no emite telemetría remota**.

- **Sin Servidores Remotos:** Focus-Guard no se comunica con ningún servicio en la nube, servidor externo ni API de terceros.
- **Sin Validación de Licencias:** El software funciona de manera totalmente independiente sin validación de licencias, llamadas de verificación de estado ("phone-home") ni registro previo.
- **Inspección de Dominios Local:** Al agregar sitios web a tu lista de bloqueo, los dominios se analizan y validan íntegramente en tu propia máquina. Jamás se consultan bases de datos externas de reputación o DNS por internet.

---

## 2. Almacenamiento Local y Soberanía de Datos

Todos los archivos de configuración, registros de estado y preferencias residen exclusivamente en tu sistema de archivos local:

| Ruta | Propietario / Alcance | Propósito |
| :--- | :--- | :--- |
| `/etc/focus-guard/config.json` | `root:root` (Lectura para usuarios) | Reglas de bloqueo globales, horarios y frases de seguridad. |
| `/var/run/focus-guard.sock` | `root:root` (Modo `0666`) | Socket de dominio UNIX local para comunicación entre procesos (IPC). |
| `/var/lib/focus-guard/runtime_state.json` | `root:root` | Estado efímero de bloqueos en curso, temporizadores y fin programado. |
| `/etc/hosts.fg.bak` | `root:root` | Copia de seguridad de respaldo seguro de tu archivo `/etc/hosts` original. |
| `~/.config/focus-guard/` / `QSettings` | Sesión del usuario | Preferencias visuales del cliente gráfico (Modo Claro/Oscuro, idioma). |

Bajo ninguna circunstancia se recopila, almacena ni transmite telemetría, información de identificación personal (PII) ni historiales de navegación web.

---

## 3. Separación de Privilegios y Modelo de Seguridad

Focus-Guard implementa una estricta separación de privilegios entre el motor de ejecución en segundo plano y la interfaz gráfica del usuario:

```mermaid
graph LR
    User[Escritorio de Usuario sin Privilegios] -->|IPC vía Socket UNIX| Client[Bandeja / GUI Focus-Guard]
    Client -->|Comandos Locales: /var/run/focus-guard.sock| Daemon[focus-guard.service (root)]
    Daemon -->|Modificación Atómica de Archivo| Hosts[/etc/hosts]
```

1. **Demonio del Sistema (`focus-guard.service`):**
   - Se ejecuta como `root` porque modificar `/etc/hosts` en Linux exige privilegios de superusuario.
   - Restringe estrictamente sus operaciones de archivo a `/etc/hosts` y `/etc/focus-guard/`.
   - Jamás expone un puerto de red TCP ni UDP; la comunicación está estrictamente confinada al socket UNIX local (`/var/run/focus-guard.sock`).
2. **Cliente de Escritorio (`focus-guard-tray`):**
   - Se ejecuta como **usuario normal sin privilegios**.
   - No requiere **permisos sudo**. No puede modificar archivos de sistema de forma directa, limitándose a enviar órdenes JSON estructuradas a través del socket UNIX.
   - Gestiona el desafío de confirmación anti-impulso en memoria, comparándolo con la configuración local del demonio.

---

## 4. Aviso Importante sobre DNS-over-HTTPS (DoH)

Focus-Guard opera en el nivel de resolución del kernel/sistema operativo mediante `/etc/hosts`.

> [!NOTE]
> Los navegadores modernos (como Firefox, Chrome o Brave) pueden activar por defecto **DNS sobre HTTPS (DoH)** o "DNS seguro", omitiendo la resolución a través de `/etc/hosts`.
> Para asegurar que Focus-Guard bloquee los sitios distractores correctamente, la configuración de DNS de tu navegador debe apuntar al **DNS del Sistema** (por ejemplo, en Firefox: *Ajustes → Privacidad y Seguridad → DNS sobre HTTPS → "Desactivado" o "Protección predeterminada"*).

---

## 5. Auditabilidad y Verificación de Código Abierto

Puedes auditar el aislamiento total de red de Focus-Guard en cualquier momento mediante las herramientas estándar de Linux:

```bash
# Verificar que ningún socket de red esté abierto por Focus-Guard
sudo ss -tulpn | grep focus-guard

# Inspeccionar descriptores de archivos y conexiones de socket del demonio
sudo lsof -c focus-guard

# Comunicarse directamente mediante la interfaz de depuración IPC
socat - UNIX-CONNECT:/var/run/focus-guard.sock
```

Focus-Guard es Software 100% Libre y de Código Abierto (FOSS). Puedes auditar el código, verificar el protocolo IPC y adaptarlo a tus necesidades.

---

*Focus-Guard garantiza privacidad absoluta. Tus hábitos de concentración, horarios y listas de bloqueo te pertenecen únicamente a ti.*
