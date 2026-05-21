"""
Sensor data service: ingest, query, aggregate
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc, Integer

from app.models.sensor_data import SensorData
from app.models.device import Device
from app.schemas.schemas import SensorDataIngest
from app.services.websocket_manager import ws_manager
from app.core.logger import logger


async def ingest_data(
    db: AsyncSession,
    device: Device,
    reading: SensorDataIngest,
    broadcast: bool = True,
) -> SensorData:
    """Save a single reading and broadcast via WebSocket"""
    record = SensorData(
        device_id=device.id,
        floor=reading.floor,
        slot_number=reading.slot_number,
        is_occupied=reading.is_occupied,
        type=reading.type,
        locked=reading.locked,
    )
    db.add(record)

    # Update device last_seen and online status
    device.last_seen = datetime.now(timezone.utc)
    device.is_online = True
    db.add(device)

    await db.flush()

    if broadcast:
        payload = {
            "device_id": device.id,
            "device_name": device.name,
            "floor": record.floor,
            "slot_number": record.slot_number,
            "is_occupied": record.is_occupied,
            "type": record.type,
            "locked": record.locked,
            "timestamp": record.timestamp.isoformat(),
        }
        msg = ws_manager.make_payload("data", device.id, payload)

        await ws_manager.broadcast_to_device(device.id, msg)
        await ws_manager.broadcast(msg)

    return record

async def ingest_bulk(
    db: AsyncSession,
    device: Device,
    readings: list[SensorDataIngest],
) -> list[SensorData]:
    logger.info(f"INGEST_BULK CALLED count={len(readings)}")

    records = []
    for reading in readings:
        logger.info(f"INGEST_BULK LOOP slot={reading.slot_number}")
        rec = await ingest_data(db, device, reading, broadcast=True)
        records.append(rec)

    logger.info(f"INGEST_BULK DONE records={len(records)}")
    return records


async def get_latest(
    db: AsyncSession,
    device_id: str,
) -> list[SensorData]:
    """Get latest state of ALL parking slots (group by slot_number)"""

    subquery = (
        select(
            SensorData.slot_number,
            func.max(SensorData.timestamp).label("max_ts")
        )
        .where(SensorData.device_id == device_id)
        .group_by(SensorData.slot_number)
        .subquery()
    )

    stmt = (
        select(SensorData)
        .join(
            subquery,
            (SensorData.slot_number == subquery.c.slot_number)
            & (SensorData.timestamp == subquery.c.max_ts)
        )
        .where(SensorData.device_id == device_id)
        .order_by(SensorData.slot_number)
    )

    result = await db.execute(stmt)
    return result.scalars().all()

async def get_slots_state(db: AsyncSession):
    stmt = (
        select(
            SensorData.slot_number,
            SensorData.floor,
            SensorData.is_occupied,
            func.max(SensorData.timestamp).label("latest_time"),
        )
        .group_by(SensorData.slot_number)
        .order_by(SensorData.slot_number)
    )

    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "slot_number": r.slot_number,
            "floor": r.floor,
            "is_occupied": r.is_occupied,
            "timestamp": r.latest_time,
        }
        for r in rows
    ]


async def get_history(
    db: AsyncSession,
    device_id: str,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 1000,
) -> list[SensorData]:
    """Get historical readings for a device"""
    conditions = [SensorData.device_id == device_id]

    if start:
        conditions.append(SensorData.timestamp >= start)
    if end:
        conditions.append(SensorData.timestamp <= end)

    stmt = (
        select(SensorData)
        .where(and_(*conditions))
        .order_by(desc(SensorData.timestamp))
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(reversed(result.scalars().all()))


async def get_stats(
    db: AsyncSession,
    device_id: str,
    hours: int = 24,
) -> dict:
    """Aggregate stats: count occupied slots over time"""
    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    stmt = select(
        func.count(SensorData.id).label("count"),
        func.sum(func.cast(SensorData.is_occupied, Integer)).label("occupied"),
    ).where(
        and_(
            SensorData.device_id == device_id,
            SensorData.timestamp >= since,
        )
    )

    result = await db.execute(stmt)
    row = result.one()

    return {
        "total": row.count,
        "occupied": int(row.occupied or 0),
        "free": row.count - int(row.occupied or 0),
    }

