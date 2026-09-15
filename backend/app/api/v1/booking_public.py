"""Unauthenticated booking endpoints consumed by the public website (fuorix.com /book).

Everything here is deliberately narrow: only active pages, only free slots, and bookings are
managed through an unguessable per-booking token. No internal data is exposed.
"""
from datetime import date, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.core.rate_limit import RequestRateLimiter
from app.database import get_db
from app.models import Meeting as MeetingModel
from app.models.booking import BookingPage
from app.schemas.booking import (
    BookingQuestion,
    PublicBooking,
    PublicBookingPage,
    PublicBookRequest,
    PublicCancelRequest,
    PublicRescheduleRequest,
    PublicSlots,
)
from app.services import booking_service
from app.services.activity_service import meetings_updated_this_request, notifications_updated_this_request

router = APIRouter(prefix="/public/booking", tags=["booking-public"])

# Bookings per client IP; generous for humans, tight enough to stop scripted spam.
book_limiter = RequestRateLimiter(max_requests=5, window_seconds=3600)
manage_limiter = RequestRateLimiter(max_requests=30, window_seconds=3600)


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _page_or_404(db: Session, slug: str) -> BookingPage:
    page = db.query(BookingPage).filter(BookingPage.slug == slug, BookingPage.is_active.is_(True)).first()
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking page not found")
    return page


def _public_page(page: BookingPage) -> PublicBookingPage:
    return PublicBookingPage(
        slug=page.slug,
        name=page.name,
        description=page.description,
        duration_minutes=page.duration_minutes,
        timezone=page.timezone,
        questions=[BookingQuestion(**q) for q in (page.questions or [])],
        location_text=page.location_text,
        host_name=(page.host.full_name if page.host else None),
        min_notice_minutes=page.min_notice_minutes,
        max_days_ahead=page.max_days_ahead,
    )


def _booking(page: BookingPage, m: MeetingModel) -> PublicBooking:
    return PublicBooking(
        manage_token=m.manage_token,
        status=m.status,
        page=_public_page(page),
        # Always UTC on the wire; the DB session may hand back a local offset.
        start=m.start_at.astimezone(timezone.utc),
        end=m.end_at.astimezone(timezone.utc),
        invitee_name=m.invitee_name or "",
        invitee_email=m.invitee_email or "",
        invitee_timezone=m.invitee_timezone,
        location=m.location,
        cancel_reason=m.cancel_reason,
    )


def _meeting_by_token(db: Session, token: str) -> tuple[MeetingModel, BookingPage]:
    if not token or len(token) < 16:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    m = db.query(MeetingModel).filter(MeetingModel.manage_token == token).first()
    if not m or not m.booking_page_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    page = db.query(BookingPage).filter(BookingPage.id == m.booking_page_id).first()
    if not page:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return m, page


@router.get("/{slug}", response_model=PublicBookingPage)
def get_page(slug: str, db: Session = Depends(get_db)):
    return _public_page(_page_or_404(db, slug))


@router.get("/{slug}/slots", response_model=PublicSlots)
def get_slots(
    slug: str,
    start: date = Query(..., description="First day (YYYY-MM-DD, in the page's timezone)"),
    end: date = Query(..., description="Last day inclusive"),
    exclude: str | None = Query(None, description="manage token of a booking being rescheduled"),
    db: Session = Depends(get_db),
):
    page = _page_or_404(db, slug)
    if end < start:
        raise HTTPException(status_code=400, detail="end must be on or after start")
    if (end - start).days + 1 > booking_service.MAX_RANGE_DAYS:
        raise HTTPException(status_code=400, detail=f"Range too large (max {booking_service.MAX_RANGE_DAYS} days)")
    exclude_id = None
    if exclude:
        m = db.query(MeetingModel).filter(MeetingModel.manage_token == exclude, MeetingModel.booking_page_id == page.id).first()
        exclude_id = m.id if m else None
    slots = booking_service.compute_slots(db, page, start, end, exclude_meeting_id=exclude_id)
    return PublicSlots(slug=page.slug, timezone=page.timezone, start=start.isoformat(), end=end.isoformat(), slots=slots)


@router.post("/{slug}/book", response_model=PublicBooking, status_code=status.HTTP_201_CREATED)
def book(slug: str, data: PublicBookRequest, request: Request, db: Session = Depends(get_db)):
    if data.website:
        # Honeypot tripped: pretend success without doing anything.
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid request")
    ip = _client_ip(request)
    if not book_limiter.allow(ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many bookings from this network. Please try again later.")
    page = _page_or_404(db, slug)
    try:
        meeting = booking_service.create_booking(db, page, data.start, data.name, str(data.email), data.timezone, data.answers, data.tracking)
    except booking_service.SlotUnavailable as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    db.commit()
    db.refresh(meeting)
    meetings_updated_this_request.set(True)
    notifications_updated_this_request.set(True)
    return _booking(page, meeting)


@router.get("/manage/{token}", response_model=PublicBooking)
def get_booking(token: str, request: Request, db: Session = Depends(get_db)):
    if not manage_limiter.allow(_client_ip(request)):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
    m, page = _meeting_by_token(db, token)
    return _booking(page, m)


@router.post("/manage/{token}/cancel", response_model=PublicBooking)
def cancel(token: str, data: PublicCancelRequest, request: Request, db: Session = Depends(get_db)):
    if not manage_limiter.allow(_client_ip(request)):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
    m, page = _meeting_by_token(db, token)
    if m.start_at and m.start_at < booking_service.utcnow() - timedelta(hours=1):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This meeting has already taken place.")
    booking_service.cancel_booking(db, m, data.reason, by="invitee")
    db.commit()
    db.refresh(m)
    meetings_updated_this_request.set(True)
    notifications_updated_this_request.set(True)
    return _booking(page, m)


@router.post("/manage/{token}/reschedule", response_model=PublicBooking)
def reschedule(token: str, data: PublicRescheduleRequest, request: Request, db: Session = Depends(get_db)):
    if not manage_limiter.allow(_client_ip(request)):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests")
    m, page = _meeting_by_token(db, token)
    if not page.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This booking page is no longer active.")
    try:
        booking_service.reschedule_booking(db, m, data.start, data.timezone)
    except booking_service.SlotUnavailable as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    db.commit()
    db.refresh(m)
    meetings_updated_this_request.set(True)
    notifications_updated_this_request.set(True)
    return _booking(page, m)
