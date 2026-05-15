from pydantic import BaseModel


class SwitchRequest(BaseModel):
    estado: bool


class DeviceHealthSchema(BaseModel):
    name: str
    status: str
    healthy: bool
    last_error: str


class DevicesStatusResponse(BaseModel):
    devices: dict[str, DeviceHealthSchema]


class PowerMetricsData(BaseModel):
    v_l1: float
    v_l2: float
    v_l3: float
    a_l1: float
    a_l2: float
    a_l3: float
    potencia_kw: float
    factor_potencia: float
    frecuencia: float
    timestamp: str
    source: str


class PowerMetricsResponse(BaseModel):
    success: bool
    status: str
    data: PowerMetricsData | None
    error: str | None = None


class HeartbeatResponse(BaseModel):
    status: str
    uptime_seconds: float
    rs485_status: str
