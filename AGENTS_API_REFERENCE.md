# Farm Control API — Referencia para agentes e integradores

Este documento describe todos los endpoints de la API, qué reciben, qué devuelven y cómo usarlos para integrar Core-Swicht-V2 con otros agentes, paneles o sistemas externos.

- URL base: `http://<host>:8000`
- Interfaz interactiva OpenAPI: `http://<host>:8000/docs`
- Todos los endpoints de tipo `POST /switch/*` aceptan el mismo body JSON.

---

## Body común para conmutación

```json
{
  "estado": true
}
```

| Campo  | Tipo    | Descripción                          |
|--------|---------|--------------------------------------|
| estado | boolean | `true` = encender, `false` = apagar  |

---

## 1. Salud y diagnóstico

### `GET /health`

Estado básico de la API.

**Response `200 OK`**

```json
{
  "status": "ok",
  "contactors_loaded": 3
}
```

| Campo             | Tipo   | Descripción                              |
|-------------------|--------|------------------------------------------|
| status            | string | Siempre `"ok"` si la API responde        |
| contactors_loaded | int    | Número de contactores cargados desde INI |

---

### `GET /heartbeat`

Heartbeat extendido con uptime, estado de los buses RS485 y estado de protección.

**Response `200 OK`**

```json
{
  "status": "alive",
  "uptime_seconds": 86400.5,
  "rs485_status": "Online",
  "temperature_rs485_status": "Online",
  "manual_shutdown": false,
  "shutdown_reason": null
}
```

| Campo                      | Tipo    | Descripción                                                    |
|----------------------------|---------|----------------------------------------------------------------|
| status                     | string  | `"alive"`                                                      |
| uptime_seconds             | float   | Tiempo desde el arranque de la API                             |
| rs485_status               | string  | Estado del medidor eléctrico (`Online`, `Offline`, etc.)     |
| temperature_rs485_status   | string  | Estado del sensor de temperatura                               |
| manual_shutdown            | boolean | `true` si el último apagado fue manual (bloquea auto-arranque) |
| shutdown_reason            | string  | Razón del último apagado general automático o manual           |

---

### `GET /devices/status`

Estado de salud de cada dispositivo registrado.

**Response `200 OK`**

```json
{
  "devices": {
    "relay_controller": {
      "name": "Relay Controller",
      "status": "Online",
      "healthy": true,
      "last_error": ""
    },
    "industrial_multimeter": {
      "name": "Industrial Multimeter",
      "status": "Online",
      "healthy": true,
      "last_error": ""
    },
    "temperature_sensor": {
      "name": "Temperature Sensor",
      "status": "Online",
      "healthy": true,
      "last_error": ""
    }
  }
}
```

| Campo     | Tipo    | Descripción                              |
|-----------|---------|------------------------------------------|
| name      | string  | Nombre legible del dispositivo           |
| status    | string  | Estado textual                           |
| healthy   | boolean | `true` si el dispositivo está sano       |
| last_error| string  | Último error conocido (vacío si no hay)  |

---

## 2. Métricas eléctricas

### `GET /metrics/power`

Última lectura del medidor Modbus (multímetro industrial). Los datos se actualizan en segundo plano según `poll_interval_seconds`.

**Response `200 OK` con datos**

```json
{
  "success": true,
  "status": "Online",
  "data": {
    "v_l1": 231.1,
    "v_l2": 230.9,
    "v_l3": 231.4,
    "a_l1": 10.2,
    "a_l2": 9.8,
    "a_l3": 10.0,
    "potencia_kw": 6.3,
    "factor_potencia": 95.0,
    "frecuencia": 60.0,
    "timestamp": "2026-04-28T03:21:11.123456+00:00",
    "source": "modbus_rtu_rs485"
  },
  "error": null,
  "shutdown_reason": null
}
```

| Campo             | Tipo   | Unidad | Descripción                        |
|-------------------|--------|--------|------------------------------------|
| v_l1..v_l3        | float  | V      | Voltaje L1, L2, L3                |
| a_l1..a_l3        | float  | A      | Corriente L1, L2, L3              |
| potencia_kw       | float  | kW     | Potencia activa total               |
| factor_potencia   | float  | %/raw  | Factor de potencia (0-100 típico) |
| frecuencia        | float  | Hz     | Frecuencia de red                   |
| timestamp         | string | ISO    | Momento de la lectura               |
| source            | string | —      | Origen: `"modbus_rtu_rs485"`        |

**Response `200 OK` sin datos**

```json
{
  "success": false,
  "status": "Offline",
  "data": null,
  "error": "No multimeter data available yet",
  "shutdown_reason": null
}
```

---

## 3. Métricas de temperatura

### `GET /metrics/temperature`

Última lectura del sensor de temperatura Modbus con todos los canales configurados.

**Response `200 OK` con datos**

```json
{
  "success": true,
  "status": "Online",
  "data": {
    "temperature_c": 42.5,
    "ambient_temperature_c": 28.1,
    "channels": {
      "Transformador - 1": 42.5,
      "Ambiente": 28.1
    },
    "timestamp": "2026-04-28T03:22:00.123456+00:00",
    "source": "modbus_rtu_rs485_temperature"
  },
  "error": null,
  "shutdown_reason": null
}
```

| Campo                  | Tipo   | Descripción                                              |
|------------------------|--------|----------------------------------------------------------|
| temperature_c          | float  | Valor del primer canal habilitado (canal principal)     |
| ambient_temperature_c  | float  | Valor del canal llamado "Ambiente" o del segundo canal   |
| channels               | dict   | Mapa `{nombre_canal: valor}` de todos los canales activos |
| timestamp              | string | ISO                                                      |
| source                 | string | `"modbus_rtu_rs485_temperature"`                         |

**Response `200 OK` sin datos**

```json
{
  "success": false,
  "status": "Offline",
  "data": null,
  "error": "No temperature data available yet",
  "shutdown_reason": null
}
```

---

### `GET /metrics/temperature/ambient`

Solo temperatura ambiente y canales, sin el campo `temperature_c` principal.

**Response `200 OK` con datos**

```json
{
  "success": true,
  "status": "Online",
  "data": {
    "ambient_temperature_c": 28.1,
    "channels": {
      "Transformador - 1": 42.5,
      "Ambiente": 28.1
    },
    "timestamp": "2026-04-28T03:22:00.123456+00:00",
    "source": "modbus_rtu_rs485_temperature"
  },
  "error": null,
  "shutdown_reason": null
}
```

---

## 4. Estado general

### `GET /status/general`

Combina el estado actual de cada contactor, la última temperatura leída y el estado de protección.

**Response `200 OK`**

```json
{
  "contactors": {
    "C1": {
      "name": "Contactor 1",
      "state": "ON",
      "raw": { "dps": { "1": true } }
    },
    "C2": {
      "name": "Contactor 2",
      "state": "OFF",
      "raw": { "dps": { "1": false } }
    },
    "C3": {
      "name": "Contactor 3",
      "state": "UNKNOWN",
      "error": "...",
      "config": { "name": "Contactor 3", "id": "...", "ip": "...", "key": "...", "version": "3.4" }
    }
  },
  "temperature": {
    "temperature_c": 42.5,
    "ambient_temperature_c": 28.1,
    "channels": {
      "Transformador - 1": 42.5,
      "Ambiente": 28.1
    },
    "source": "modbus_rtu_rs485_temperature",
    "timestamp": "2026-04-28T03:22:00.123456+00:00"
  },
  "manual_shutdown": false,
  "shutdown_reason": null
}
```

| Campo             | Tipo   | Descripción                                                   |
|-------------------|--------|---------------------------------------------------------------|
| contactors        | dict   | Estado de cada contactor configurado                          |
| temperature       | dict   | Snapshot de temperatura (puede ser `null` si no hay datos)   |
| manual_shutdown   | boolean| Bloquea auto-arranque hasta próximo encendido manual          |
| shutdown_reason   | string | Razón del último apagado                                      |

Posibles valores de `state`: `"ON"`, `"OFF"`, `"UNKNOWN"`.

---

## 5. Conmutación general

### `POST /switch/general`

Enciende o apaga `C1`, `C2` y `C3` como grupo.

- **Encender (`estado=true`)**: inicia el encendido secuencial en segundo plano (`C1` → espera 180 s → `C2` → espera 180 s → `C3`).
- **Apagar (`estado=false`)**: apaga inmediatamente los tres contactores y marca `manual_shutdown = true`.

**Request**

```json
{
  "estado": true
}
```

**Response `estado=true` aceptado**

```json
{
  "accepted": true,
  "message": "Sequential ON routine started in background",
  "manual_shutdown_cleared": true
}
```

**Response `estado=true` ya en ejecución**

```json
{
  "accepted": false,
  "message": "Sequential ON routine is already running"
}
```

**Response `estado=false`**

```json
{
  "accepted": true,
  "message": "Immediate OFF executed",
  "results": {
    "C1": { "success": true, "name": "Contactor 1", "requested_state": false, "device_response": "..." },
    "C2": { "success": true, "name": "Contactor 2", "requested_state": false, "device_response": "..." },
    "C3": { "success": false, "error": "Not configured" }
  },
  "shutdown_reason": "Manual general shutdown"
}
```

---

## 6. Conmutación individual

### `POST /switch/C1`

Conmuta el contactor `C1` directamente.

**Response éxito**

```json
{
  "success": true,
  "name": "Contactor 1",
  "requested_state": true,
  "device_response": "..."
}
```

**Response error de configuración**

```json
{
  "success": false,
  "error": "C1 is not configured"
}
```

### `POST /switch/C2`

Igual que `C1`, para el contactor `C2`.

### `POST /switch/C3`

Igual que `C1`, para el contactor `C3`.

---

## 7. Dispositivos de alarma

### `POST /switch/bocina`

Conmuta el dispositivo Tuya configurado como `BOCINA` en `config/device_alarm/`.

**Response éxito**

```json
{
  "success": true,
  "name": "Bocina",
  "requested_state": true,
  "device_response": "..."
}
```

**Response sin configurar**

```json
{
  "success": false,
  "error": "Bocina is not configured"
}
```

### `POST /switch/luces`

Conmuta los dispositivos `LIGHT1`, `LIGHT2` y `LIGHT3` configurados en `config/device_alarm/`.

**Response**

```json
{
  "success": true,
  "requested_state": true,
  "results": {
    "LIGHT1": { "success": true, "name": "Luz 1", "requested_state": true, "device_response": "..." },
    "LIGHT2": { "success": true, "name": "Luz 2", "requested_state": true, "device_response": "..." },
    "LIGHT3": { "success": false, "error": "LIGHT3 is not configured" }
  }
}
```

| Campo           | Tipo    | Descripción                                         |
|-----------------|---------|-----------------------------------------------------|
| success         | boolean | `true` si **todos** los dispositivos respondieron OK |
| requested_state | boolean | Estado solicitado                                   |
| results         | dict    | Resultado individual por luz                        |

---

## 8. Protecciones automáticas

El sistema ejecuta un hilo de protección (`VoltageProtectionMonitor`) que:

1. **Arranque seguro**: al iniciar, espera datos válidos del multímetro y del sensor de temperatura. Si hay condiciones críticas, apaga todo.
2. **Protección por voltaje**: si cualquiera de L1, L2, L3 sale de `[min_volts, max_volts]`, ejecuta apagado general y guarda `shutdown_reason`.
3. **Auto-arranque**: si las tres fases están dentro de `[auto_start_min_volts, auto_start_max_volts]` durante `auto_start_stable_seconds`, inicia encendido secuencial automático.
4. **Protección por temperatura**: si `temperature_c` supera `max_temperature_c`, apaga todo.
5. **Apagado manual**: cuando se apaga manualmente (`POST /switch/general` con `estado=false` o protección dispara apagado), se establece `manual_shutdown = true`, lo que **bloquea el auto-arranque** hasta el próximo encendido manual o reinicio.

Configuración en `config/config.ini`.

---

## 9. Notificaciones y webhook

### Notificaciones móviles

Variables de entorno:

| Variable            | Descripción                                    |
|---------------------|------------------------------------------------|
| `NTFY_TOPIC`        | Tema privado en ntfy.sh                        |
| `NTFY_SERVER`       | Servidor ntfy (por defecto `https://ntfy.sh`)  |
| `TELEGRAM_BOT_TOKEN`| Token del bot de Telegram                      |
| `TELEGRAM_CHAT_ID`  | Chat ID de destino                             |

Se envían cuando cambia de estado C1, C2 o C3 (por cualquier medio: panel, API o secuencia automática).

### Webhook

Variables de entorno:

| Variable        | Descripción                                              |
|-----------------|----------------------------------------------------------|
| `WEBHOOK_URL`   | URL destino. Si está vacía, no se envía nada.            |
| `WEBHOOK_TOKEN` | Token opcional enviado en header `X-Webhook-Token`.      |

Payload enviado en cada conmutación:

```json
{
  "event": "switch_changed",
  "timestamp": "2026-04-28T03:25:00.000000+00:00",
  "device_key": "C1",
  "name": "Contactor 1",
  "requested_state": "ON",
  "success": true,
  "device_response": "...",
  "error": null,
  "source": "farm-control-api"
}
```

---

## 10. Configuración de dispositivos

### Contactores principales (`config/C1.ini`, `C2.ini`, `C3.ini`)

```ini
[DEVICE]
name    = Contactor 1
id      = bf1234567890abcdef1234
ip      = 192.168.1.101
key     = 0123456789abcdef
version = 3.4
```

### Dispositivos de alarma (`config/device_alarm/Light1.ini`, etc.)

Mismo formato `[DEVICE]`. La clave del archivo (sin extensión, en mayúsculas) determina el rol: `BOCINA`, `LIGHT1`, `LIGHT2`, `LIGHT3`.

### Medidor eléctrico (`config/modbus_voltage.ini`)

```ini
[MODBUS_VOLTAGE]
port = /dev/ttyUSB0
slave_address = 1
baudrate = 9600
bytesize = 8
stopbits = 1
parity = N
timeout = 1.0
poll_interval_seconds = 1.0
reconnect_delay_seconds = 3.0
```

### Sensor de temperatura (`config/modbus_temperature.ini`)

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

### Protección (`config/config.ini`)

```ini
[VOLTAGE_PROTECTION]
enabled = false
min_volts = 215
max_volts = 263
check_interval_seconds = 2
startup_read_timeout_seconds = 90
auto_start_enabled = false
auto_start_min_volts = 218
auto_start_max_volts = 260
auto_start_stable_seconds = 180

[TEMPERATURE_PROTECTION]
enabled = false
max_temperature_c = 80
check_interval_seconds = 2
```

---

## 11. Errores comunes

| Síntoma                                                              | Posible causa                                           |
|----------------------------------------------------------------------|---------------------------------------------------------|
| `status: "Offline"` en `/metrics/power`                              | Puerto RS485 incorrecto, medidor apagado o sin respuesta |
| `status: "Offline"` en `/metrics/temperature`                         | Puerto RS485 incorrecto o sensor sin respuesta           |
| `state: "UNKNOWN"`                                                   | Contactor no responde al handshake Tuya (red/key/IP)     |
| `Sequential ON routine is already running`                           | Ya hay un encendido secuencial en curso                  |
| Apagado automático inesperado                                        | Protección por voltaje o temperatura activada            |
| Auto-arranque no ocurre                                              | `manual_shutdown` está activo o voltaje no es estable    |

---

## 12. Ejemplos de uso con curl

### Encender todo

```bash
curl -X POST http://localhost:8000/switch/general \
  -H "Content-Type: application/json" \
  -d '{"estado": true}'
```

### Apagar todo

```bash
curl -X POST http://localhost:8000/switch/general \
  -H "Content-Type: application/json" \
  -d '{"estado": false}'
```

### Estado de contactores y temperatura

```bash
curl http://localhost:8000/status/general
```

### Última lectura eléctrica

```bash
curl http://localhost:8000/metrics/power
```

### Encender C1

```bash
curl -X POST http://localhost:8000/switch/C1 \
  -H "Content-Type: application/json" \
  -d '{"estado": true}'
```

### Encender bocina

```bash
curl -X POST http://localhost:8000/switch/bocina \
  -H "Content-Type: application/json" \
  -d '{"estado": true}'
```

---

## 13. Modelos de datos internos

### `Contactor` (`app/models.py`)

```python
@dataclass
class Contactor:
    name: str
    id: str      # device ID Tuya
    ip: str      # IP local
    key: str     # local key
    version: str = "3.4"
```

### `SwitchRequest` (`app/schemas.py`)

```python
class SwitchRequest(BaseModel):
    estado: bool
```

### `PowerMetricsResponse` (`app/schemas.py`)

Véase la respuesta de `/metrics/power`.

### `TemperatureMetricsResponse` (`app/schemas.py`)

Véase la respuesta de `/metrics/temperature`.

---

*Última actualización: 2026-08-29*
