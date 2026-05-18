"""
Data endpoints:
  POST /data          → Device sends data via HTTP (uses API key)
  GET  /data/{id}/latest   → Dashboard queries latest values
  GET  /data/{id}/history  → Historical time-series
  GET  /data/{id}/stats    → Aggregate stats
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.device import Device
from app.models.user import User
from app.schemas.schemas import (
    SensorDataIngest, SensorDataBulk, SensorDataOut
)
from app.services.sensor_service import (
    ingest_data, ingest_bulk, get_latest, get_history, get_stats, get_slots_state
)
from app.api.v1.deps import get_device_from_api_key, get_current_user
from app.models.sensor_data import SensorData
from sqlalchemy import select

router = APIRouter(prefix="/data", tags=["Data"])


# ─── Device-facing (uses API key) ────────────────────────────────────────────

@router.post("/ingest", status_code=201)
async def device_send_single(
    reading: SensorDataIngest,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_device_from_api_key),
):
    """Device POSTs a single sensor reading. Auth: X-API-Key header."""
    record = await ingest_data(db, device, reading)
    await db.commit()
    return {"status": "ok", "id": record.id, "timestamp": record.timestamp}


@router.post("/ingest/bulk", status_code=201)
async def device_send_bulk(
    body: SensorDataBulk,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_device_from_api_key),
):
    """Device POSTs multiple readings in one request."""
    records = await ingest_bulk(db, device, body.readings)
    await db.commit()
    return {"status": "ok", "count": len(records)}


# ─── Dashboard / backend-facing (uses Bearer token) ──────────────────────────

@router.get("/{device_id}/latest", response_model=list[SensorDataOut])
async def latest_values(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get latest readings for a device."""
    return await get_latest(db, device_id)

@router.get("/latest-event")
async def get_latest_events(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SensorData, Device.name.label("device_name"))
        .join(Device, SensorData.device_id == Device.id)
        .where(Device.owner_id == current_user.id)
        .order_by(SensorData.timestamp.desc())
        .limit(limit)
    )

    rows = result.all()

    return [
        {
            "type": "data",
            "device_id": record.device_id,
            "timestamp": record.timestamp.isoformat(),
            "payload": {
                "device_name": device_name,
                "floor": record.floor,
                "slot_number": record.slot_number,
                "is_occupied": record.is_occupied,
                "type": record.type,
                "locked": record.locked,
                "timestamp": record.timestamp.isoformat(),
            },
        }
        for record, device_name in rows
    ]

@router.get("/{device_id}/history", response_model=list[SensorDataOut])
async def historical_data(
    device_id: str,
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    limit: int = Query(100, le=10000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Get historical data for a device."""
    return await get_history(db, device_id, start, end, limit)


@router.get("/{device_id}/stats")
async def field_stats(
    device_id: str,
    hours: int = Query(24, ge=1, le=720),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Aggregate occupancy stats over time."""
    return await get_stats(db, device_id, hours)

@router.get("/slots")
async def get_slots(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await get_slots_state(db)
