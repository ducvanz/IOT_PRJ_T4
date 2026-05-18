"""
Pydantic schemas — request/response validation
"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, field_validator


# ─── Auth ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    username: str
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ─── Device ──────────────────────────────────────────────────────────────────

class DeviceCreate(BaseModel):
    name: str
    description: str = ""
    device_type: str = "generic"
    meta: dict = {}


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    device_type: Optional[str] = None
    is_active: Optional[bool] = None
    meta: Optional[dict] = None


class DeviceOut(BaseModel):
    id: str
    name: str
    description: str
    device_type: str
    api_key: str
    mqtt_topic: str
    is_active: bool
    is_online: bool
    last_seen: Optional[datetime]
    meta: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

class DeviceOut2(BaseModel):
    name: str
    description: str
    is_online: bool
    last_seen: Optional[datetime]
    meta: dict
    updated_at: datetime

    model_config = {"from_attributes": True}



# ─── Sensor Data ─────────────────────────────────────────────────────────────

class SensorDataIngest(BaseModel):
    floor: str
    slot_number: str = None
    is_occupied: Optional[bool] = None
    type: Optional[str] = None
    locked: Optional[bool] = None

class SensorDataBulk(BaseModel):
    """Multiple readings in one request"""
    readings: list[SensorDataIngest]


class SensorDataOut(BaseModel):
    id: str
    device_id: str
    floor: str
    slot_number: str
    is_occupied: Optional[bool]
    type: Optional[str]
    timestamp: datetime
    locked: Optional[bool]

    model_config = {"from_attributes": True}


class SensorDataQuery(BaseModel):
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    limit: int = 100

    @field_validator("limit")
    @classmethod
    def cap_limit(cls, v):
        return min(v, 10000)


# ─── WebSocket messages ───────────────────────────────────────────────────────

class WSMessage(BaseModel):
    type: str  # "data", "status", "alert"
    device_id: str
    payload: Any
    timestamp: str


#---------other------------------------
class DeviceWithDataOut(DeviceOut2):
    sensor_data: list[SensorDataOut] = []

    model_config = {"from_attributes": True}
