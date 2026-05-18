from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib import error, parse, request

logger = logging.getLogger("farm-control")


@dataclass(frozen=True)
class NotificationSettings:
    ntfy_server: str
    ntfy_topic: str
    telegram_bot_token: str
    telegram_chat_id: str

    @property
    def enabled(self) -> bool:
        return bool(self.ntfy_topic) or bool(
            self.telegram_bot_token and self.telegram_chat_id
        )


def load_notification_settings() -> NotificationSettings:
    return NotificationSettings(
        ntfy_server=os.getenv("NTFY_SERVER", "https://ntfy.sh").rstrip("/"),
        ntfy_topic=os.getenv("NTFY_TOPIC", "").strip(),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
    )


def _format_message(contactor_key: str, result: dict) -> tuple[str, str, str]:
    on = bool(result.get("requested_state"))
    state_label = "ENCENDIDO" if on else "APAGADO"
    name = str(result.get("name", contactor_key))
    success = bool(result.get("success"))
    ts = datetime.now(timezone.utc).strftime("%H:%M UTC")

    if success:
        title = f"Contactor {contactor_key} · {state_label}"
        body = f"{name} pasó a {state_label} ({ts})"
        priority = "default"
    else:
        title = f"Error · {contactor_key}"
        err = result.get("error") or "operación fallida"
        body = f"No se pudo conmutar {name}: {err} ({ts})"
        priority = "high"

    return title, body, priority


def _send_ntfy(settings: NotificationSettings, title: str, body: str, priority: str) -> None:
    url = f"{settings.ntfy_server}/{parse.quote(settings.ntfy_topic, safe='')}"
    req = request.Request(url, data=body.encode("utf-8"), method="POST")
    req.add_header("Title", title)
    req.add_header("Priority", priority)
    req.add_header("Tags", "zap,electric_plug")

    with request.urlopen(req, timeout=8) as response:
        logger.info("ntfy notification sent (%s)", response.status)


def _send_telegram(settings: NotificationSettings, title: str, body: str) -> None:
    text = f"*{title}*\n{body}"
    payload = json.dumps(
        {
            "chat_id": settings.telegram_chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
    ).encode("utf-8")
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    req = request.Request(
        url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=8) as response:
        logger.info("Telegram notification sent (%s)", response.status)


def notify_contactor_change(
    contactor_key: str,
    result: dict,
    settings: NotificationSettings | None = None,
) -> None:
    settings = settings or load_notification_settings()
    if not settings.enabled:
        return

    title, body, priority = _format_message(contactor_key, result)

    def _dispatch() -> None:
        if settings.ntfy_topic:
            try:
                _send_ntfy(settings, title, body, priority)
            except error.URLError as exc:
                logger.warning("ntfy notification failed for %s: %s", contactor_key, exc)
            except Exception as exc:
                logger.warning("ntfy unexpected error for %s: %s", contactor_key, exc)

        if settings.telegram_bot_token and settings.telegram_chat_id:
            try:
                _send_telegram(settings, title, body)
            except error.URLError as exc:
                logger.warning("Telegram notification failed for %s: %s", contactor_key, exc)
            except Exception as exc:
                logger.warning("Telegram unexpected error for %s: %s", contactor_key, exc)

    threading.Thread(
        target=_dispatch,
        daemon=True,
        name=f"notify-{contactor_key.lower()}",
    ).start()
