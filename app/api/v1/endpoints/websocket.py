"""
WebSocket endpoint for real-time dashboard updates
ws://host/ws              → all device updates
ws://host/ws/{device_id} → single device updates
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

from app.services.websocket_manager import ws_manager
from app.core.logger import logger

ws_router = APIRouter(tags=["WebSocket"])


@ws_router.websocket("/ws")
async def websocket_all(websocket: WebSocket):
    """Subscribe to all device events"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; clients can send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@ws_router.websocket("/ws/{device_id}")
async def websocket_device(websocket: WebSocket, device_id: str):
    """Subscribe to a specific device's events"""
    await ws_manager.connect(websocket, device_id=device_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
