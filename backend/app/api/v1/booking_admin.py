"""Admin management of public booking pages (event types)."""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.database import get_db
from app.models import User as UserModel
from app.models.booking import BookingPage
from app.schemas.booking import BookingPageCreate, BookingPageResponse, BookingPageUpdate
from app.services import booking_service
from app.services import google_calendar_service as gcal

router = APIRouter(prefix="/booking-pages", tags=["booking-pages"])


def _resp(p: BookingPage, db: Session | None = None) -> BookingPageResponse:
    connected = bool(db is not None and p.host_user_id and gcal.get_integration(db, p.host_user_id))
    return BookingPageResponse(
        host_google_connected=connected,
        id=p.id,
        slug=p.slug,
        name=p.name,
        description=p.description,
        duration_minutes=p.duration_minutes,
        buffer_before_minutes=p.buffer_before_minutes,
        buffer_after_minutes=p.buffer_after_minutes,
        min_notice_minutes=p.min_notice_minutes,
        max_days_ahead=p.max_days_ahead,
        timezone=p.timezone,
        hours=p.hours or {},
        questions=p.questions or [],
        location_text=p.location_text,
        host_user_id=p.host_user_id,
        is_active=p.is_active,
        host_name=(p.host.full_name or p.host.email) if p.host else None,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _check_host(db: Session, host_user_id: UUID | None) -> None:
    if host_user_id is None:
        return
    u = db.query(UserModel).filter(UserModel.id == host_user_id, UserModel.is_active.is_(True)).first()
    if not u:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Host user not found")
    if u.client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A client user cannot host bookings")


@router.get("", response_model=list[BookingPageResponse])
def list_pages(db: Session = Depends(get_db), user=Depends(require_permission("admin:all"))):
    return [_resp(p, db) for p in db.query(BookingPage).order_by(BookingPage.created_at).all()]


@router.post("", response_model=BookingPageResponse, status_code=status.HTTP_201_CREATED)
def create_page(data: BookingPageCreate, db: Session = Depends(get_db), user=Depends(require_permission("admin:all"))):
    if db.query(BookingPage).filter(BookingPage.slug == data.slug).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
    _check_host(db, data.host_user_id)
    payload = data.model_dump()
    payload["questions"] = [q.model_dump() for q in data.questions]
    page = BookingPage(**payload, created_by=user.id)
    db.add(page)
    db.commit()
    db.refresh(page)
    return _resp(page, db)


@router.get("/{page_id}", response_model=BookingPageResponse)
def get_page(page_id: UUID, db: Session = Depends(get_db), user=Depends(require_permission("admin:all"))):
    page = db.query(BookingPage).filter(BookingPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return _resp(page, db)


@router.patch("/{page_id}", response_model=BookingPageResponse)
def update_page(page_id: UUID, data: BookingPageUpdate, db: Session = Depends(get_db), user=Depends(require_permission("admin:all"))):
    page = db.query(BookingPage).filter(BookingPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    changes = data.model_dump(exclude_unset=True)
    if "questions" in changes and data.questions is not None:
        changes["questions"] = [q.model_dump() for q in data.questions]
    if "slug" in changes and changes["slug"] != page.slug:
        if db.query(BookingPage).filter(BookingPage.slug == changes["slug"]).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")
    if "host_user_id" in changes:
        _check_host(db, changes["host_user_id"])
    for k, v in changes.items():
        setattr(page, k, v)
    db.commit()
    db.refresh(page)
    return _resp(page, db)


@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_page(page_id: UUID, db: Session = Depends(get_db), user=Depends(require_permission("admin:all"))):
    page = db.query(BookingPage).filter(BookingPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(page)  # meetings keep their data; booking_page_id is set NULL by the FK
    db.commit()


@router.get("/{page_id}/slots")
def preview_slots(
    page_id: UUID,
    start: date = Query(...),
    end: date = Query(...),
    db: Session = Depends(get_db),
    user=Depends(require_permission("admin:all")),
):
    """Admin preview of what the public page will offer (ignores is_active)."""
    page = db.query(BookingPage).filter(BookingPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if end < start or (end - start).days + 1 > booking_service.MAX_RANGE_DAYS:
        raise HTTPException(status_code=400, detail="Bad range")
    return {"timezone": page.timezone, "slots": booking_service.compute_slots(db, page, start, end)}
