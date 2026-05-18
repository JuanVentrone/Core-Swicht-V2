# Farm Control API (Tuya 3.4)

API en FastAPI para controlar contactores industriales Tuya con `tinytuya` usando protocolo **3.4**.

## Estructura

- `config/`: archivos `.ini` por contactor (`C1.ini`, `C2.ini`, `C3.ini`)
- `app/models.py`: clase `Contactor`
- `app/config_loader.py`: carga de configuración con `ConfigParser`
- `app/services.py`: lógica de control y estado
- `main.py`: endpoints FastAPI

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuración

Edita `config/C1.ini`, `config/C2.ini`, `config/C3.ini` con `id`, `ip` y `key` reales.

## Ejecutar API

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /health`
- `GET /metrics/power` (lectura RS485 en segundo plano cada 1 segundo)
- `POST /switch/general` con body JSON:

```json
{
  "estado": true
}
```

- `GET /status/general`
- `POST /switch/C1`
- `POST /switch/C2`
- `POST /switch/C3`
- `POST /switch/bocina`
- `POST /switch/luces`

Respuesta de `GET /metrics/power` (si hay datos):

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
  "error": null
}
```

## Notificaciones al celular (contactores)

Cuando **C1, C2 o C3** cambian de estado (desde el panel Pain Farm, la API o el encendido secuencial), la API puede enviar un aviso al móvil.

### Opción A — ntfy (recomendada, app gratuita)

1. Instala **[ntfy](https://ntfy.sh/)** en iOS o Android.
2. En la app, suscríbete a un tema privado, por ejemplo `pain-farm-tugranja` (elige un nombre difícil de adivinar).
3. En el servidor donde corre Core Swicht:

```bash
export NTFY_TOPIC="pain-farm-tugranja"
# Servidor público por defecto; o tu instancia propia:
# export NTFY_SERVER="https://ntfy.sh"
```

4. Reinicia la API (`systemctl --user restart core-swicht` o `uvicorn`).

Cada conmutación envía título y mensaje, por ejemplo: `Contactor C1 · ENCENDIDO`.

### Opción B — Telegram

1. Crea un bot con [@BotFather](https://t.me/BotFather) y copia el **token**.
2. Obtén tu **chat_id** (mensaje al bot + `https://api.telegram.org/bot<TOKEN>/getUpdates`).
3. Variables:

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC..."
export TELEGRAM_CHAT_ID="123456789"
```

Puedes usar **ntfy y Telegram a la vez**.

Plantilla de variables: `.env.example`.

---

## Webhook (plug-and-play)

El webhook es opcional y queda desactivado por defecto.

- Si `WEBHOOK_URL` esta vacia, no se envia nada.
- Si `WEBHOOK_URL` tiene valor, cada `switch` envia un `POST` JSON en segundo plano.
- Si defines `WEBHOOK_TOKEN`, se envia en header `X-Webhook-Token`.

Ejemplo (PowerShell):

```powershell
$env:WEBHOOK_URL="https://tu-destino/webhook"
$env:WEBHOOK_TOKEN="token-opcional"
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Comportamiento principal

- `estado=true`:
  - enciende `C1` inmediato
  - espera 180 segundos
  - enciende `C2`
  - espera 180 segundos
  - enciende `C3`
  - se ejecuta en segundo plano (thread) para no bloquear la API

- `estado=false`:
  - apaga `C1`, `C2`, `C3` de forma inmediata

## Nota técnica

Cada operación aplica handshake con `status()` antes de `set_status()`, fuerza versión `3.4`, usa `set_socketPersistent(True)` y cierra socket con seguridad.
