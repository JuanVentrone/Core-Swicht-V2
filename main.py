import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.alarm_services import AlarmController
from app.config import ModbusSettings
from app.config_loader import (
    load_alarm_devices,
    load_contactors,
    load_modbus_settings,
    load_temperature_modbus_settings,
    load_temperature_protection_settings,
    load_voltage_protection_settings,
)
from app.device_manager import DeviceManager
from app.devices.industrial_multimeter import IndustrialMultimeterDevice
from app.devices.relay_controller import RelayControllerDevice
from app.devices.temperature_sensor import TemperatureSensorDevice
from app.voltage_protection import VoltageProtectionMonitor
from app.schemas import (
    DevicesStatusResponse,
    HeartbeatResponse,
    PowerMetricsData,
    PowerMetricsResponse,
    SwitchRequest,
    TemperatureMetricsResponse,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app_started_at = time.monotonic()
relay_device = RelayControllerDevice(
    contactors=load_contactors(),
    webhook_url=os.getenv("WEBHOOK_URL", ""),
    webhook_token=os.getenv("WEBHOOK_TOKEN", ""),
)
voltage_modbus_settings = load_modbus_settings()
multimeter_device = IndustrialMultimeterDevice(settings=voltage_modbus_settings)
temperature_modbus_settings = load_temperature_modbus_settings()
temperature_sensor_device = TemperatureSensorDevice(settings=temperature_modbus_settings)
temperature_protection_settings = load_temperature_protection_settings()
voltage_protection = VoltageProtectionMonitor(
    multimeter=multimeter_device,
    controller=relay_device.controller,
    settings=load_voltage_protection_settings(),
    temperature_settings=temperature_protection_settings,
)
device_manager = DeviceManager(
    devices={
        "relay_controller": relay_device,
        "industrial_multimeter": multimeter_device,
        "temperature_sensor": temperature_sensor_device,
    },
    startup_gate=voltage_protection.run_startup_gate,
)
alarm_controller = AlarmController(load_alarm_devices(), relay_device.controller)


@asynccontextmanager
async def lifespan(_: FastAPI):
    device_manager.initialize_all()
    voltage_protection.start()
    try:
        yield
    finally:
        voltage_protection.stop()
        device_manager.shutdown_all()


app = FastAPI(title="Farm Control API", version="1.0.0", lifespan=lifespan)
controller = relay_device.controller


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "contactors_loaded": len(controller.contactors)}


@app.get("/heartbeat", response_model=HeartbeatResponse)
def heartbeat() -> HeartbeatResponse:
    return {
        "status": "alive",
        "uptime_seconds": round(time.monotonic() - app_started_at, 2),
        "rs485_status": multimeter_device.health.value,
        "temperature_rs485_status": temperature_sensor_device.health.value,
        "manual_shutdown": controller.manual_shutdown,
        "shutdown_reason": controller.shutdown_reason,
    }


@app.get("/devices/status", response_model=DevicesStatusResponse)
def devices_status() -> DevicesStatusResponse:
    return {"devices": device_manager.health_status()}


@app.get("/metrics/power", response_model=PowerMetricsResponse)
def power_metrics() -> PowerMetricsResponse:
    snapshot = multimeter_device.last_snapshot
    if snapshot is None:
        return {
            "success": False,
            "status": "Offline",
            "data": None,
            "error": multimeter_device.last_error or "No multimeter data available yet",
            "shutdown_reason": controller.shutdown_reason,
        }
    return {
        "success": True,
        "status": multimeter_device.health.value,
        "data": PowerMetricsData(**snapshot.__dict__),
        "error": None,
        "shutdown_reason": controller.shutdown_reason,
    }


@app.post("/switch/general")
def switch_general(payload: SwitchRequest) -> dict:
    return controller.General_Switch_System(payload.estado, manual=not payload.estado)


@app.post("/switch/C1")
def switch_c1(payload: SwitchRequest) -> dict:
    contactor = controller.contactors.get("C1")
    if contactor is None:
        return {"success": False, "error": "C1 is not configured"}
    return controller.ctr_contactor(contactor, payload.estado)


@app.post("/switch/C2")
def switch_c2(payload: SwitchRequest) -> dict:
    contactor = controller.contactors.get("C2")
    if contactor is None:
        return {"success": False, "error": "C2 is not configured"}
    return controller.ctr_contactor(contactor, payload.estado)


@app.post("/switch/C3")
def switch_c3(payload: SwitchRequest) -> dict:
    contactor = controller.contactors.get("C3")
    if contactor is None:
        return {"success": False, "error": "C3 is not configured"}
    return controller.ctr_contactor(contactor, payload.estado)


@app.post("/switch/bocina")
def switch_bocina(payload: SwitchRequest) -> dict:
    return alarm_controller.switch_buzzer(payload.estado)


@app.post("/switch/luces")
def switch_luces(payload: SwitchRequest) -> dict:
    return alarm_controller.switch_lights(payload.estado)


@app.get("/status/general")
def status_general() -> dict:
    status = controller.General_Status()
    snapshot = multimeter_device.last_snapshot
    return {
        "contactors": status,
        "temperature": {
            "temperature_c": snapshot.temperature_c if snapshot is not None else None,
            "source": snapshot.source if snapshot is not None else None,
            "timestamp": snapshot.timestamp if snapshot is not None else None,
        },
        "manual_shutdown": controller.manual_shutdown,
        "shutdown_reason": controller.shutdown_reason,
    }


@app.get("/metrics/temperature", response_model=TemperatureMetricsResponse)
def temperature_metrics() -> TemperatureMetricsResponse:
    snapshot = multimeter_device.last_snapshot
    if snapshot is None:
        return {
            "success": False,
            "status": "Offline",
            "data": None,
            "error": multimeter_device.last_error or "No multimeter data available yet",
            "shutdown_reason": controller.shutdown_reason,
        }
    return {
        "success": True,
        "status": multimeter_device.health.value,
        "data": {
            "temperature_c": snapshot.temperature_c,
            "timestamp": snapshot.timestamp,
            "source": snapshot.source,
        },
        "error": None,
        "shutdown_reason": controller.shutdown_reason,
    }
