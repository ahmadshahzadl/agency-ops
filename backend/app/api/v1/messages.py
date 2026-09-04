"""Messages API: direct messages between users. Creates notification for recipient; real-time via WebSocket."""
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func, and_
from app.database import get_db
from app.models import Message as MessageModel, User, Notification as NotificationModel
from app.schemas.message import MessageCreate, MessageResponse, ConversationSummary
from app.api.deps import get_current_user, require_staff
from app.websocket_messages import message_ws_manager
from app.services.activity_service import notifications_updated_this_request

router = APIRouter(prefix="/messages", tags=["messages"])


from pydantic import BaseModel as _BaseModel
from typing import Optional as _Optional


class DirectoryUser(_BaseModel):
    id: UUID
    full_name: _Optional[str] = None
    email: str
    job_title: _Optional[str] = None
    team_names: list[str] = []


@router.get("/directory", response_model=list[DirectoryUser])
def directory(
    db: Session = Depends(get_db),
    user=Depends(require_staff),
):
    """All active staff for the new-message picker (portal users excluded both ways)."""
    from app.models import User as UserModel
    rows = db.query(UserModel).filter(
        UserModel.is_active == True, UserModel.client_id.is_(None)
    ).order_by(UserModel.full_name).all()
    return [
        DirectoryUser(
            id=u.id, full_name=u.full_name, email=u.email, job_title=u.job_title,
            team_names=[t.name for t in u.teams],
        )
        for u in rows
    ]


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    db: Session = Depends(get_db),
    user=Depends(require_staff),
):
    """List users the current user has chatted with, with last message and unread count."""
    sent = db.query(MessageModel.recipient_id).filter(MessageModel.sender_id == user.id).distinct().all()
    received = db.query(MessageModel.sender_id).filter(MessageModel.recipient_id == user.id).distinct().all()
    other_ids = {r.recipient_id for r in sent} | {r.sender_id for r in received}
    last_at_map = {}
    for other_id in other_ids:
        last = (
            db.query(func.max(MessageModel.created_at))
            .filter(
                or_(
                    and_(MessageModel.sender_id == user.id, MessageModel.recipient_id == other_id),
                    and_(MessageModel.sender_id == other_id, MessageModel.recipient_id == user.id),
                )
            )
            .scalar()
        )
        if last:
            last_at_map[other_id] = last

    if not other_ids:
        return []

    users_map = {u.id: u for u in db.query(User).filter(User.id.in_(other_ids), User.is_active == True).all()}
    unread = (
        db.query(MessageModel.sender_id, func.count(MessageModel.id).label("c"))
        .filter(MessageModel.recipient_id == user.id, MessageModel.read_at.is_(None))
        .group_by(MessageModel.sender_id)
        .all()
    )
    unread_map = {r.sender_id: r.c for r in unread}

    last_msg = {}
    for other_id in other_ids:
        last = (
            db.query(MessageModel)
            .filter(
                or_(
                    and_(MessageModel.sender_id == user.id, MessageModel.recipient_id == other_id),
                    and_(MessageModel.sender_id == other_id, MessageModel.recipient_id == user.id),
                )
            )
            .order_by(MessageModel.created_at.desc())
            .first()
        )
        if last:
            last_msg[other_id] = (last.created_at, (last.content or "")[:80])

    out = []
    for other_id in sorted(other_ids, key=lambda x: last_at_map.get(x) or datetime.min.replace(tzinfo=timezone.utc), reverse=True):
        u = users_map.get(other_id)
        if not u:
            continue
        last_at, preview = last_msg.get(other_id, (None, None)) or (None, None)
        out.append(ConversationSummary(
            other_user_id=other_id,
            other_user_name=u.full_name or u.email or str(other_id),
            last_message_at=last_at,
            last_message_preview=preview,
            unread_count=unread_map.get(other_id, 0),
        ))
    return out


@router.get("", response_model=list[MessageResponse])
def list_messages(
    with_user_id: UUID = Query(..., description="Other user ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user=Depends(require_staff),
):
    """Get messages between current user and with_user_id, ordered by created_at desc."""
    qry = (
        db.query(MessageModel)
        .options(joinedload(MessageModel.sender))
        .filter(
            or_(
                and_(MessageModel.sender_id == user.id, MessageModel.recipient_id == with_user_id),
                and_(MessageModel.sender_id == with_user_id, MessageModel.recipient_id == user.id),
            )
        )
        .order_by(MessageModel.created_at.desc())
    )
    messages = qry.offset(skip).limit(limit).all()
    return [
        MessageResponse(
            id=m.id,
            sender_id=m.sender_id,
            recipient_id=m.recipient_id,
            content=m.content,
            read_at=m.read_at,
            created_at=m.created_at,
            sender_name=m.sender.full_name or m.sender.email if m.sender else None,
        )
        for m in reversed(messages)
    ]


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    data: MessageCreate,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
):
    if data.recipient_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot message yourself")
    recipient = db.query(User).filter(User.id == data.recipient_id, User.is_active == True).first()
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient not found")
    message = MessageModel(
        sender_id=user.id,
        recipient_id=data.recipient_id,
        content=data.content.strip() or "(empty)",
    )
    db.add(message)
    db.flush()

    notif = NotificationModel(
        user_id=data.recipient_id,
        title="New message",
        message=data.content.strip()[:200] or "New message",
        link=f"/messages?with={user.id}",
        type="message",
        message_id=message.id,
    )
    db.add(notif)
    notifications_updated_this_request.set(True)
    db.commit()
    db.refresh(message)
    message = db.query(MessageModel).options(joinedload(MessageModel.sender)).filter(MessageModel.id == message.id).first()

    def _iso_utc(dt):
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.isoformat() + "Z"
        return dt.isoformat()

    payload = {
        "type": "new_message",
        "message": {
            "id": str(message.id),
            "sender_id": str(message.sender_id),
            "recipient_id": str(message.recipient_id),
            "content": message.content,
            "read_at": _iso_utc(message.read_at),
            "created_at": _iso_utc(message.created_at),
            "sender_name": message.sender.full_name or message.sender.email if message.sender else None,
        },
    }
    await message_ws_manager.send_to_user(data.recipient_id, payload)

    return MessageResponse(
        id=message.id,
        sender_id=message.sender_id,
        recipient_id=message.recipient_id,
        content=message.content,
        read_at=message.read_at,
        created_at=message.created_at,
        sender_name=message.sender.full_name or message.sender.email if message.sender else None,
    )


@router.post("/{message_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_message_read(
    message_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_staff),
):
    msg = db.query(MessageModel).filter(MessageModel.id == message_id, MessageModel.recipient_id == user.id).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    if msg.read_at is None:
        msg.read_at = datetime.now(timezone.utc)
        db.query(NotificationModel).filter(
            NotificationModel.message_id == message_id,
            NotificationModel.user_id == user.id,
        ).update({NotificationModel.read_at: datetime.now(timezone.utc)}, synchronize_session=False)
        notifications_updated_this_request.set(True)
        db.commit()
