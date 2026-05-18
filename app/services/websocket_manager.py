"""
WebSocket manager — maintains active connections and broadcasts data
"""
import json
from datetime import datetime, timezone
from typing import Dict, Set

from fastapi import WebSocket

from app.core.logger import logger


class ConnectionManager:
    def __init__(self):
        # All connected clients
        self.active_connections: list[WebSocket] = []
        # Clients subscribed to specific devices
        self.device_subscribers: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, device_id: str | None = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        if device_id:
            if device_id not in self.device_subscribers:
                self.device_subscribers[device_id] = set()
            self.device_subscribers[device_id].add(websocket)
            logger.info(f"WS client subscribed to device {device_id}")
        else:
            logger.info("WS client connected (all devices)")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        for device_id in list(self.device_subscribers.keys()):
            self.device_subscribers[device_id].discard(websocket)
        logger.info("WS client disconnected")

    async def broadcast(self, message: dict):
        """Broadcast to all connected clients"""
        data = json.dumps(message)
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def broadcast_to_device(self, device_id: str, message: dict):
        """Broadcast only to clients subscribed to a specific device"""
        data = json.dumps(message)
        dead = []
        subscribers = self.device_subscribers.get(device_id, set()).copy()
        for ws in subscribers:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    def make_payload(self, msg_type: str, device_id: str, payload: dict) -> dict:
        return {
            "type": msg_type,
            "device_id": device_id,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


ws_manager = ConnectionManager()
