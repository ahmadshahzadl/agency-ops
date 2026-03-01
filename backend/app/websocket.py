"""Simple WebSocket manager to broadcast activity updates to connected dashboard clients."""
import asyncio
import json
from fastapi import WebSocket


class ActivityConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast(self, message: dict) -> None:
        if not self._connections:
            return
        payload = json.dumps(message)
        dead = []
        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


activity_manager = ActivityConnectionManager()
