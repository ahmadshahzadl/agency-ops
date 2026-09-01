from uuid import UUID
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api.v1 import auth, clients, projects, tasks, meetings, finance, analytics, users, roles, teams, leads, team_activity, announcements, notifications, notes, messages
from app.websocket import activity_manager
from app.websocket_messages import message_ws_manager
from app.services.activity_service import (
    activity_logged_this_request,
    tasks_updated_this_request,
    meetings_updated_this_request,
    notifications_updated_this_request,
)

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _ws_user_id(websocket: WebSocket) -> UUID | None:
    """Validate the ?token=JWT access token on a WebSocket connection. None = reject."""
    from app.core.security import decode_token, token_version_matches
    from app.database import SessionLocal
    from app.models import User
    token = websocket.query_params.get("token") or ""
    if not token:
        return None
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None
    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        return None
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user or not token_version_matches(payload, user):
            return None
        return user_id
    finally:
        db.close()


@app.websocket("/api/v1/ws/activity")
async def websocket_activity(websocket: WebSocket):
    """Connect with ?token=JWT to receive instant activity updates. Sends { \"type\": \"activity_updated\" } when any user logs activity."""
    if _ws_user_id(websocket) is None:
        await websocket.close(code=4001)
        return
    await activity_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        activity_manager.disconnect(websocket)


@app.websocket("/api/v1/ws/messages")
async def websocket_messages(websocket: WebSocket):
    """Connect with ?token=JWT to receive real-time new-message events. Sends { \"type\": \"new_message\", \"message\": {...} }."""
    user_id = _ws_user_id(websocket)
    if user_id is None:
        await websocket.close(code=4001)
        return
    await message_ws_manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        message_ws_manager.disconnect(websocket, user_id)


class ActivityBroadcastMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        activity_logged_this_request.set(False)
        tasks_updated_this_request.set(False)
        meetings_updated_this_request.set(False)
        notifications_updated_this_request.set(False)
        response = await call_next(request)
        types = []
        if activity_logged_this_request.get():
            types.append("activity_updated")
        if tasks_updated_this_request.get():
            types.append("tasks_updated")
        if meetings_updated_this_request.get():
            types.append("meetings_updated")
        if notifications_updated_this_request.get():
            types.append("notifications_updated")
        if types:
            await activity_manager.broadcast({"types": types})
        activity_logged_this_request.set(False)
        tasks_updated_this_request.set(False)
        meetings_updated_this_request.set(False)
        notifications_updated_this_request.set(False)
        return response


app.add_middleware(ActivityBroadcastMiddleware)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(meetings.router, prefix="/api/v1")
app.include_router(finance.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(roles.router, prefix="/api/v1")
app.include_router(teams.router, prefix="/api/v1")
app.include_router(leads.router, prefix="/api/v1")
app.include_router(team_activity.router, prefix="/api/v1")
app.include_router(announcements.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(notes.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/v1/version")
def version():
    """Public endpoint for frontend to check if a newer app version is available."""
    return {"version": settings.app_version}
