from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
EVENT_LOG_PATH = LOG_DIR / "system_events.log"


def get_event_log_path() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    EVENT_LOG_PATH.touch(exist_ok=True)
    return EVENT_LOG_PATH


def _ensure_event_handler() -> logging.Logger:
    logger = logging.getLogger("farm-control.events")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_path = get_event_log_path()
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    )
    logger.addHandler(file_handler)

    return logger


EVENT_LOGGER = _ensure_event_handler()


def log_system_event(
    action: str,
    reason: str | None = None,
    details: dict[str, Any] | None = None,
    level: str = "INFO",
) -> None:
    """Escribe un evento del sistema con fecha, acción y motivo claro."""
    log_path = get_event_log_path()
    if not log_path.exists():
        log_path.touch(exist_ok=True)

    logger = _ensure_event_handler()
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    payload = {
        "timestamp": timestamp,
        "action": str(action).upper(),
        "reason": reason or "UNKNOWN",
        "details": details or {},
    }
    message = f"{payload['timestamp']} | ACTION={payload['action']} | REASON={payload['reason']} | DETAILS={json.dumps(payload['details'], ensure_ascii=False, default=str)}"
    logger.log(getattr(logging, level.upper(), logging.INFO), message)
