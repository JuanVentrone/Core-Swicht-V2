from pathlib import Path

from app.event_logger import get_event_log_path, log_system_event


def test_event_logger_creates_file_and_records_event():
    log_path = get_event_log_path()
    if log_path.exists():
        log_path.unlink()

    log_system_event(
        action="OFF",
        reason="LOW_VOLTAGE",
        details={"L1": 210.0, "L2": 219.0, "L3": 218.0, "range": "210-240V"},
    )

    assert log_path.exists(), "Debe crearse el archivo de log del sistema"
    text = log_path.read_text(encoding="utf-8")
    assert "OFF" in text
    assert "LOW_VOLTAGE" in text
    assert "L1" in text
