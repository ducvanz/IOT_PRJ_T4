"""
MQTT Client — connects to broker, subscribes to device topics, ingests data
Topic convention: devices/{device_id}/data
                  devices/{device_id}/status
"""
import json
import asyncio
from typing import Optional

import aiomqtt

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.logger import logger


class MQTTManager:
    def __init__(self):
        self.client: Optional[aiomqtt.Client] = None
        self._task: Optional[asyncio.Task] = None

    async def connect(self):
        """Start MQTT listener in background task"""
        self._task = asyncio.create_task(self._listen())

    async def disconnect(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _listen(self):
        """Main MQTT listening loop with auto-reconnect"""
        import ssl
        while True:
            try:
                logger.info(f"Connecting to MQTT broker {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
                tls_context = ssl.create_default_context()
                async with aiomqtt.Client(
                    hostname=settings.MQTT_BROKER_HOST,
                    port=settings.MQTT_BROKER_PORT,
                    username=settings.MQTT_USERNAME or None,
                    password=settings.MQTT_PASSWORD or None,
                    keepalive=settings.MQTT_KEEPALIVE,
                    identifier="nexusiot-platform",
                    tls_context=tls_context,
                ) as client:
                    self.client = client
                    # Subscribe to ALL device topics
                    await client.subscribe("devices/+/data")
                    await client.subscribe("devices/+/status")
                    logger.info("MQTT subscribed to devices/+/data and devices/+/status")

                    async for message in client.messages:
                        print("[MQTT RECEIVED]", message.topic, message.payload)
                        await self._handle_message(str(message.topic), message.payload)

            except aiomqtt.MqttError as e:
                logger.error(f"MQTT error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break

    async def _handle_message(self, topic: str, payload: bytes):
        """Route incoming MQTT messages"""
        try:
            parts = topic.split("/")
            if len(parts) < 3:
                return

            device_id = parts[1]
            msg_type = parts[2]

            data = json.loads(payload.decode("utf-8"))

            if msg_type == "data":
                await self._process_data(device_id, data)
            elif msg_type == "status":
                await self._process_status(device_id, data)

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"MQTT bad payload on {topic}: {e}")
        except Exception as e:
            logger.error(f"MQTT handler error: {e}")

    async def _process_data(self, device_id: str, data: dict):
        from app.models.device import Device
        from app.schemas.schemas import SensorDataIngest
        from app.services.sensor_service import ingest_data, ingest_bulk
        from sqlalchemy import select
        # from app.services.external import schedule_push_with_data
        from app.services.websocket_manager import ws_manager

        logger.info(
            "MQTT data received | device_id=%s | payload=%s",
            device_id,
            json.dumps(data, ensure_ascii=False, default=str),
        )

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Device).where(Device.id == device_id))
            device = result.scalar_one_or_none()

            if not device:
                logger.warning(f"MQTT data from unknown device: {device_id}")
                return

            if not device.is_active:
                return
            logger.info(
            "Dữ liệu trước khi chạm db")

            if "readings" in data:
                readings = data["readings"]

                parsed = [SensorDataIngest(**r) for r in readings]

                await ingest_bulk(db, device, parsed)
            else:
                reading = SensorDataIngest(**data)
                await ingest_data(db, device, reading)
            logger.info(
            "Nếu ws lỗi")
            msg = ws_manager.make_payload("data", device_id, data)
            await ws_manager.broadcast(msg)
            logger.info(
            "Dữ liệu đã gửi lên ws")
            await db.commit()
            # msg = ws_manager.make_payload("data", device_id, data)
            # await ws_manager.broadcast(msg)
            logger.info(
            "Dữ liệu nhận đã cập nhật lên db")
            # schedule_push_with_data()

    async def _process_status(self, device_id: str, data: dict):
        """Handle device online/offline status"""
        from app.models.device import Device
        from app.services.websocket_manager import ws_manager
        from sqlalchemy import select
        from datetime import datetime, timezone
        # from app.services.external import schedule_push_with_data

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Device).where(Device.id == device_id))
            device = result.scalar_one_or_none()
            if not device:
                return

            status = data.get("status", "online")
            device.is_online = status == "online"
            device.last_seen = datetime.now(timezone.utc)
            db.add(device)
            await db.commit()

            msg = ws_manager.make_payload("status", device_id, {"status": status, "device_name": device.name})
            await ws_manager.broadcast(msg)
            # schedule_push_with_data()
            logger.info(f"Device {device_id} status: {status}")

    async def publish(self, topic: str, payload: dict):
        """Publish a message (e.g. command to device)"""
        logger.info(f"Deviceooo {payload}")
        if self.client:
            await self.client.publish(topic, json.dumps(payload))


mqtt_manager = MQTTManager()
