"""Device CRUD endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from fastapi import Header, Request

from app.core.database import get_db
from app.core.security import generate_api_key
from app.models.device import Device
from app.models.user import User
from app.schemas.schemas import DeviceCreate, DeviceUpdate, DeviceOut, DeviceWithDataOut
from sqlalchemy.orm import selectinload
from app.api.v1.deps import get_current_user
from app.mqtt.client import mqtt_manager

router = APIRouter(prefix="/devices", tags=["Devices"])

@router.get("", response_model=list[DeviceOut])
async def list_devices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Device)
        .where(Device.owner_id == current_user.id)
        .order_by(desc(Device.created_at))
    )
    return result.scalars().all()


@router.post("", response_model=DeviceOut, status_code=201)
async def create_device(
    body: DeviceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device_id = None  # Will be auto-generated
    api_key = generate_api_key()

    device = Device(
        name=body.name,
        description=body.description,
        device_type=body.device_type,
        api_key=api_key,
        mqtt_topic="",
        meta=body.meta,
        owner_id=current_user.id,
    )
    db.add(device)
    await db.flush()  # Get the generated ID

    device.mqtt_topic = f"devices/{device.id}/data"
    db.add(device)
    return device


@router.get("/with-data", response_model=list[DeviceWithDataOut])
async def list_devices_with_data(
    request: Request,
    db: AsyncSession = Depends(get_db),
    apiKey: str = Header(None),
):
    if apiKey != "abc":
        raise HTTPException(status_code=401, detail="Invalid API key")

    result = await db.execute(
        select(Device)
        .options(selectinload(Device.sensor_data))
        .order_by(desc(Device.created_at))
    )

    devices = result.scalars().unique().all()

    response = []
    for device in devices:
        latest_by_slot: dict = {}

        for data in device.sensor_data:
            slot = data.slot_number
            existing = latest_by_slot.get(slot)
            if existing is None or (
                data.timestamp is not None
                and (existing.timestamp is None or data.timestamp > existing.timestamp)
            ):
                latest_by_slot[slot] = data

        filtered_data = sorted(latest_by_slot.values(), key=lambda d: d.slot_number)

        # Build response dict thay vì mutate ORM object
        device_dict = {
            **device.__dict__,
            "sensor_data": filtered_data,
        }
        device_dict.pop("_sa_instance_state", None)

        response.append(DeviceWithDataOut.model_validate(device_dict))

    return response

@router.post("/{device_id}/command/lock")
async def send_lock_command(
    device_id: str,
    slot_number: str = Body(...),
    locked: bool = Body(...),
):
    await mqtt_manager.publish(
        f"devices/{device_id}/command",
        {
            "command": "lock" if locked else "unlock",
            "slot_number": slot_number,
            "locked": locked,
        },
    )

    return {"ok": True}

@router.get("/{device_id}", response_model=DeviceOut)
async def get_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = await _get_device_or_404(db, device_id, current_user.id)
    return device


@router.patch("/{device_id}", response_model=DeviceOut)
async def update_device(
    device_id: str,
    body: DeviceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = await _get_device_or_404(db, device_id, current_user.id)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(device, field, value)

    db.add(device)
    return device


@router.delete("/{device_id}", status_code=204)
async def delete_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = await _get_device_or_404(db, device_id, current_user.id)
    await db.delete(device)


@router.post("/{device_id}/regenerate-key", response_model=DeviceOut)
async def regenerate_api_key(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rotate the API key of a device"""
    device = await _get_device_or_404(db, device_id, current_user.id)
    device.api_key = generate_api_key()
    db.add(device)
    return device


async def _get_device_or_404(db: AsyncSession, device_id: str, owner_id: str) -> Device:
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.owner_id == owner_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device
