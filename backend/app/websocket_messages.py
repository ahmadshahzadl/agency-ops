"""Per-user WebSocket manager for real-time messaging. Clients connect with token; we send new-message payloads to recipient."""
import asyncio
import json
from uuid import UUID
from fastapi import WebSocket
from app.core.security import decode_token


class MessageConnectionManager:
    def __init__(self):
        self._by_user: dict[UUID, list[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: UUID) -> None:
        await websocket.accept()
        async with self._lock:
            self._by_user.setdefault(user_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: UUID) -> None:
        if user_id in self._by_user:
            conns = self._by_user[user_id]
            if websocket in conns:
                conns.remove(websocket)
            if not conns:
                del self._by_user[user_id]

    async def send_to_user(self, user_id: UUID, message: dict) -> None:
        conns = self._by_user.get(user_id, [])
        if not conns:
            return
        payload = json.dumps(message)
        dead = []
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        async with self._lock:
            for ws in dead:
                if ws in self._by_user.get(user_id, []):
                    self._by_user[user_id].remove(ws)
            if self._by_user.get(user_id) == []:
                del self._by_user[user_id]


message_ws_manager = MessageConnectionManager()
