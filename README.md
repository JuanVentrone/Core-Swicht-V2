# Farm Control API (Tuya 3.4)

API en FastAPI para controlar contactores industriales Tuya con `tinytuya` usando protocolo **3.4**, con lectura de medidor eléctrico y sensor de temperatura Modbus RTU sobre RS485, protección por voltaje/temperatura, notificaciones móviles y webhook.

> **Documentación técnica para agentes / integradores:** consulta [AGENTS_API_REFERENCE.md](AGENTS_API_REFERENCE.md) para el catálogo completo de endpoints, ejemplos de request/response y variables de entorno.

## Estructura

- `config/`: archivos `.ini` por contactor (`C1.ini`, `C2.ini`, `C3.ini`), medidor Modbus, sensor de temperatura y alarmas
- `app/`: modelos, schemas Pydantic, carga de configuración, lógica de control, dispositivos y protección
- `main.py`: endpoints FastAPI
- `tests/`: pruebas del sistema

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

## Configuración

### Contactores principales

Edita `config/C1.ini`, `config/C2.ini`, `config/C3.ini` con `id`, `ip` y `key` reales de cada dispositivo Tuya:

```ini
[DEVICE]
name = Contactor 1
id   = tu-device-id
ip   = 192.168.1.101
key  = tu-local-key
version = 3.4
```

### Medidor de voltaje / potencia (RS485 Modbus)

Configura `config/modbus_voltage.ini`:

```ini
[MODBUS_VOLTAGE]
port = /dev/ttyUSB0
slave_address = 1
baudrate = 9600
poll_interval_seconds = 1.0
```

### Sensor de temperatura (RS485 Modbus)

Configura `config/modbus_temperature.ini`:

```ini
[MODBUS_TEMPERATURE]
port = /dev/ttyUSB1
slave_address = 1
baudrate = 9600
poll_interval_seconds = 2.0

[CHANNEL_1]
name = Transformador - 1
register = 0
decimals = 1
enabled = true

[CHANNEL_2]
name = Ambiente
register = 1
decimals = 1
enabled = true
```

### Protección por voltaje y temperatura

Edita `config/config.ini`:

```ini
[VOLTAGE_PROTECTION]
enabled = true
min_volts = 215
max_volts = 263
auto_start_enabled = true
auto_start_min_volts = 218
auto_start_max_volts = 260
auto_start_stable_seconds = 180

[TEMPERATURE_PROTECTION]
enabled = true
max_temperature_c = 80
```

### Variables de entorno (opcional)

```bash
# Notificaciones (ntfy o Telegram)
export NTFY_TOPIC="pain-farm-tugranja"
export TELEGRAM_BOT_TOKEN="123456:ABC..."
export TELEGRAM_CHAT_ID="123456789"

# Webhook opcional
export WEBHOOK_URL="https://tu-destino/webhook"
export WEBHOOK_TOKEN="token-opcional"
```

## Ejecutar la API

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Endpoints principales

- `GET /health` – estado básico de la API
- `GET /heartbeat` – uptime, estado RS485 y razones de apagado
- `GET /devices/status` – estado de salud de cada dispositivo
- `GET /metrics/power` – medidor eléctrico (lectura en segundo plano)
- `GET /metrics/temperature` – temperatura del sensor Modbus
- `GET /metrics/temperature/ambient` – temperatura ambiente
- `GET /status/general` – contactores + temperatura + protección
- `POST /switch/general` – encendido/apagado general con secuencia automática
- `POST /switch/C1`, `POST /switch/C2`, `POST /switch/C3`
- `POST /switch/bocina`
- `POST /switch/luces`

Body para cualquier `POST /switch/*`:

```json
{
  "estado": true
}
```

## Comportamiento del encendido/apagado general

- `estado=true`:
  - enciende `C1` inmediato
  - espera 180 segundos
  - enciende `C2`
  - espera 180 segundos
  - enciende `C3`
  - se ejecuta en segundo plano (thread) para no bloquear la API

- `estado=false`:
  - apaga `C1`, `C2`, `C3` de forma inmediata
  - marca `manual_shutdown = true` para bloquear el auto-arranque hasta el próximo encendido manual

## Protecciones automáticas

- **Voltaje fuera de rango**: si alguna de L1, L2, L3 sale de `[min_volts, max_volts]`, se apaga todo.
- **Auto-arranque**: si las tres fases permanecen en `[auto_start_min_volts, auto_start_max_volts]` durante `auto_start_stable_seconds`, se inicia el encendido secuencial automáticamente (salvo que haya un apagado manual previo).
- **Temperatura alta**: si `temperature_c` supera `max_temperature_c`, se apaga todo.
- **Arranque seguro**: al iniciar la API, si no hay datos Modbus a tiempo o las condiciones son críticas, se apagan los contactores.

## Webhook (plug-and-play)

Cada conmutación de contactor (`C1`, `C2`, `C3`, `bocina`, `luces`) envía un `POST` JSON en segundo plano a `WEBHOOK_URL` cuando está configurado. Incluye header `X-Webhook-Token` si se define `WEBHOOK_TOKEN`.

## Notificaciones al celular

Cuando **C1, C2 o C3** cambian de estado, la API puede enviar un aviso al móvil vía ntfy, Telegram o ambos.

### Opción A — ntfy (recomendada, app gratuita)

1. Instala **[ntfy](https://ntfy.sh/)** en iOS o Android.
2. Suscríbete a un tema privado, por ejemplo `pain-farm-tugranja`.
3. En el servidor:

```bash
export NTFY_TOPIC="pain-farm-tugranja"
# export NTFY_SERVER="https://ntfy.sh"  # servidor público por defecto
```

### Opción B — Telegram

1. Crea un bot con [@BotFather](https://t.me/BotFather) y copia el **token**.
2. Obtén tu **chat_id**.
3. En el servidor:

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC..."
export TELEGRAM_CHAT_ID="123456789"
```

## Documentación extendida

- [AGENTS_API_REFERENCE.md](AGENTS_API_REFERENCE.md) – referencia completa de endpoints para otros agentes e integradores.
- [ANALISIS_TEMPERATURA.md](ANALISIS_TEMPERATURA.md) – análisis del subsistema de temperatura.

## Nota técnica

Cada operación aplica handshake con `status()` antes de `set_status()`, fuerza versión `3.4`, usa `set_socketPersistent(True)` y cierra socket con seguridad.
