from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Meeting as MeetingModel, MeetingAttendee, Project as ProjectModel, Client as ClientModel, Notification as NotificationModel, Lead as LeadModel, User as UserModel
from app.schemas.meeting import MeetingCreate, MeetingUpdate, MeetingResponse, MeetingAssignRequest, MeetingOutcomeRequest
from app.services import booking_service
from sqlalchemy import or_, exists
from app.api.deps import get_current_user, require_permission, require_any_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids, get_is_sales_member
from app.services.permission_service import users_with_permission, BOOKINGS_MANAGE
from app.services.cleanup_service import purge_entity_artifacts
from app.services.activity_service import log_activity, meetings_updated_this_request, notifications_updated_this_request

router = APIRouter(prefix="/meetings", tags=["meetings"])


def _notify_meeting_attendees(db: Session, meeting: MeetingModel, attendee_ids: list[UUID]) -> None:
    """Create a notification for each attendee so assigned users get notified about the meeting."""
    if not attendee_ids:
        return
    start_str = meeting.start_at.strftime("%Y-%m-%d %H:%M") if meeting.start_at else ""
    title = f"Meeting: {meeting.title}"
    message = f"Scheduled for {start_str}." + (f" {meeting.location}" if meeting.location else "")
    link = f"/meetings/{meeting.id}"
    for uid in attendee_ids:
        n = NotificationModel(
            user_id=uid,
            title=title,
            message=message,
            link=link,
            type="meeting",
            reference_id=None,
        )
        db.add(n)
    db.flush()


def _can_access_meeting(
    meeting: MeetingModel,
    team_ids: set[UUID],
    is_admin: bool,
    manager_scope: set[UUID] | None = None,
    sales_own_only: bool = False,
    user_id: UUID | None = None,
    bookings_access: bool = False,
) -> bool:
    if is_admin:
        return True
    # bookings:manage (solutions engineers): every booking that came in from outside,
    # plus anything assigned to them.
    if bookings_access and (meeting.source != "manual" or (user_id and meeting.assigned_to == user_id)):
        return True
    if user_id and any(a.user_id == user_id for a in (meeting.attendee_links or [])):
        return True
    if sales_own_only and user_id:
        return meeting.created_by == user_id or any(
            a.user_id == user_id for a in (meeting.attendee_links or [])
        )
    if manager_scope is not None:
        if meeting.created_by is None or meeting.created_by not in manager_scope:
            return False
        if not meeting.project_id:
            return True
        return meeting.project and meeting.project.owner_id in manager_scope
    if not meeting.project_id or not meeting.project or not meeting.project.client:
        return False
    return meeting.project.client.team_id in team_ids


def _meeting_to_response(m: MeetingModel) -> MeetingResponse:
    attendee_ids = [a.user_id for a in m.attendee_links]
    return MeetingResponse(
        id=m.id,
        project_id=m.project_id,
        title=m.title,
        description=m.description,
        start_at=m.start_at,
        end_at=m.end_at,
        location=m.location,
        assigned_to=m.assigned_to,
        assigned_to_name=(m.assignee.full_name or m.assignee.email) if m.assignee else None,
        company_name=m.lead.company_name if m.lead else None,
        lead_status=m.lead.status if m.lead else None,
        host_user_id=m.host_user_id,
        host_name=(m.host.full_name or m.host.email) if m.host else None,
        tracking=m.tracking,
        outcome_note=m.outcome_note,
        reminder_24h_sent_at=m.reminder_24h_sent_at,
        reminder_1h_sent_at=m.reminder_1h_sent_at,
        source=m.source or "manual",
        external_id=m.external_id,
        status=m.status or "scheduled",
        invitee_name=m.invitee_name,
        invitee_email=m.invitee_email,
        cancel_reason=m.cancel_reason,
        lead_id=m.lead_id,
        booking_page_id=m.booking_page_id,
        invitee_timezone=m.invitee_timezone,
        answers=m.answers,
        google_event_id=m.google_event_id,
        created_by=m.created_by,
        created_at=m.created_at,
        updated_at=m.updated_at,
        attendee_ids=attendee_ids,
    )


@router.get("", response_model=list[MeetingResponse])
def list_meetings(
    db: Session = Depends(get_db),
    user=Depends(require_permission("meetings:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    sales_own_only=Depends(get_is_sales_member),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    project_id: UUID | None = None,
    source: str | None = Query(None, description="manual | website | calendly | external (= not manual)"),
    assigned: str | None = Query(None, description="me | unassigned | <user id>"),
):
    qry = db.query(MeetingModel)
    if "admin:all" not in permissions:
        # Attendees always see their own meetings (this is how webhook-created bookings,
        # which have no creator, reach the people hosting them).
        attendee_exists = exists().where(
            MeetingAttendee.meeting_id == MeetingModel.id,
            MeetingAttendee.user_id == user.id,
        )
        if sales_own_only:
            scope = or_(MeetingModel.created_by == user.id, attendee_exists)
        elif manager_scope is not None:
            qry = qry.outerjoin(ProjectModel, MeetingModel.project_id == ProjectModel.id)
            scope = or_(
                attendee_exists,
                MeetingModel.created_by.in_(manager_scope)
                & ((ProjectModel.id.is_(None)) | (ProjectModel.owner_id.in_(manager_scope))),
            )
        elif not team_ids:
            scope = attendee_exists
        else:
            qry = qry.outerjoin(ProjectModel, MeetingModel.project_id == ProjectModel.id).outerjoin(
                ClientModel, ProjectModel.client_id == ClientModel.id
            )
            scope = or_(attendee_exists, ClientModel.team_id.in_(team_ids))
        if BOOKINGS_MANAGE in permissions:
            # Solutions engineers see every inbound booking and whatever is assigned to them.
            scope = or_(scope, MeetingModel.source != "manual", MeetingModel.assigned_to == user.id)
        qry = qry.filter(scope)
    if project_id:
        qry = qry.filter(MeetingModel.project_id == project_id)
    if source == "external":
        qry = qry.filter(MeetingModel.source != "manual")
    elif source:
        qry = qry.filter(MeetingModel.source == source)
    if assigned == "me":
        qry = qry.filter(MeetingModel.assigned_to == user.id)
    elif assigned == "unassigned":
        qry = qry.filter(MeetingModel.assigned_to.is_(None))
    elif assigned:
        try:
            qry = qry.filter(MeetingModel.assigned_to == UUID(assigned))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="assigned must be me, unassigned or a user id")
    # Tiebreaker keeps pagination stable when many meetings share a start time.
    qry = qry.order_by(MeetingModel.start_at.desc(), MeetingModel.id.desc())
    meetings = qry.offset(skip).limit(limit).all()
    return [_meeting_to_response(m) for m in meetings]


@router.post("", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
def create_meeting(
    data: MeetingCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("meetings:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    if data.project_id and "admin:all" not in permissions:
        from app.models import Project as P, Client as C
        proj = db.query(P).filter(P.id == data.project_id).first()
        if proj:
            if manager_scope is not None:
                if proj.owner_id not in manager_scope:
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create meeting for this project")
            elif not proj.client or proj.client.team_id not in team_ids:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create meeting for this project")
    meeting = MeetingModel(
        project_id=data.project_id,
        title=data.title,
        description=data.description,
        start_at=data.start_at,
        end_at=data.end_at,
        location=data.location,
        created_by=user.id,
    )
    db.add(meeting)
    db.flush()
    log_activity(db, user.id, "meeting_created", "meeting", meeting.id, details=f"Meeting: {meeting.title}")
    attendee_ids = list(data.attendee_ids or [])
    for uid in attendee_ids:
        db.add(MeetingAttendee(meeting_id=meeting.id, user_id=uid))
    db.flush()
    _notify_meeting_attendees(db, meeting, attendee_ids)
    db.commit()
    db.refresh(meeting)
    return _meeting_to_response(meeting)


@router.get("/booking-assignees")
def list_booking_assignees(
    db: Session = Depends(get_db),
    user=Depends(require_permission("meetings:read")),
):
    """Users a booking can be assigned to: everyone with bookings:manage or admin."""
    users = users_with_permission(db, BOOKINGS_MANAGE, include_admins=True)
    return [{"id": u.id, "full_name": u.full_name, "email": u.email} for u in sorted(users, key=lambda u: (u.full_name or u.email).lower())]


@router.patch("/{meeting_id}/assign", response_model=MeetingResponse)
def assign_meeting(
    meeting_id: UUID,
    data: MeetingAssignRequest,
    db: Session = Depends(get_db),
    user=Depends(require_any_permission("admin:all", BOOKINGS_MANAGE)),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    sales_own_only=Depends(get_is_sales_member),
):
    """Assign (or unassign) the solutions engineer who owns this prospect. Mirrors onto the lead."""
    meeting = db.query(MeetingModel).filter(MeetingModel.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    if not _can_access_meeting(meeting, team_ids, "admin:all" in permissions, manager_scope, sales_own_only, user.id, BOOKINGS_MANAGE in permissions):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    assignee = None
    if data.assigned_to:
        assignee = db.query(UserModel).filter(UserModel.id == data.assigned_to, UserModel.is_active.is_(True)).first()
        if not assignee or assignee.client_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignee must be an active staff user")
    previous = meeting.assigned_to
    meeting.assigned_to = assignee.id if assignee else None
    lead = db.query(LeadModel).filter(LeadModel.id == meeting.lead_id).first() if meeting.lead_id else None
    if lead is not None and not lead.converted_to_client_id:
        lead.assigned_to = meeting.assigned_to
        if assignee and lead.status == "new":
            lead.status = "contacted"
    db.flush()
    who = (assignee.full_name or assignee.email) if assignee else "nobody"
    log_activity(db, user.id, "meeting_assigned", "meeting", meeting.id, details=f"{meeting.title} -> {who}")
    if assignee and assignee.id != user.id and assignee.id != previous:
        db.add(NotificationModel(
            user_id=assignee.id,
            title=f"Prospect assigned to you: {meeting.invitee_name or meeting.title}",
            message=f"{meeting.title} on {meeting.start_at.strftime('%Y-%m-%d %H:%M') if meeting.start_at else ''}" + (f" · {lead.company_name}" if lead else ""),
            link=f"/meetings/{meeting.id}",
            type="meeting",
        ))
        notifications_updated_this_request.set(True)
    meetings_updated_this_request.set(True)
    db.commit()
    db.refresh(meeting)
    return _meeting_to_response(meeting)


@router.patch("/{meeting_id}/outcome", response_model=MeetingResponse)
def set_meeting_outcome(
    meeting_id: UUID,
    data: MeetingOutcomeRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("meetings:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    sales_own_only=Depends(get_is_sales_member),
):
    """Record what happened: completed / no_show (or back to scheduled), a note, and optionally the lead's new stage.
    Allowed for admins, bookings:manage, the host, the assignee and attendees."""
    meeting = db.query(MeetingModel).filter(MeetingModel.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    if not _can_access_meeting(meeting, team_ids, "admin:all" in permissions, manager_scope, sales_own_only, user.id, BOOKINGS_MANAGE in permissions):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    involved = (
        "admin:all" in permissions
        or BOOKINGS_MANAGE in permissions
        or meeting.host_user_id == user.id
        or meeting.assigned_to == user.id
        or any(a.user_id == user.id for a in meeting.attendee_links)
    )
    if not involved:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only people on this meeting can record its outcome")
    try:
        booking_service.set_outcome(db, meeting, data.status, data.note, data.lead_status)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    log_activity(db, user.id, "meeting_outcome", "meeting", meeting.id, details=f"{meeting.title}: {data.status}" + (f" / lead {data.lead_status}" if data.lead_status else ""))
    meetings_updated_this_request.set(True)
    db.commit()
    db.refresh(meeting)
    return _meeting_to_response(meeting)


@router.get("/{meeting_id}", response_model=MeetingResponse)
def get_meeting(
    meeting_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("meetings:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    sales_own_only=Depends(get_is_sales_member),
):
    meeting = db.query(MeetingModel).filter(MeetingModel.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    if not _can_access_meeting(meeting, team_ids, "admin:all" in permissions, manager_scope, sales_own_only, user.id, BOOKINGS_MANAGE in permissions):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    return _meeting_to_response(meeting)


@router.patch("/{meeting_id}", response_model=MeetingResponse)
def update_meeting(
    meeting_id: UUID,
    data: MeetingUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("meetings:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    sales_own_only=Depends(get_is_sales_member),
):
    meeting = db.query(MeetingModel).filter(MeetingModel.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    if not _can_access_meeting(meeting, team_ids, "admin:all" in permissions, manager_scope, sales_own_only, user.id, BOOKINGS_MANAGE in permissions):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    inbound = (meeting.source or "manual") != "manual" and meeting.booking_page_id is not None
    time_changed = inbound and (
        (data.start_at is not None and data.start_at != meeting.start_at)
        or (data.end_at is not None and data.end_at != meeting.end_at)
    )
    for k in ["title", "description", "start_at", "end_at", "location"]:
        v = getattr(data, k, None)
        if v is not None and not (time_changed and k in ("start_at", "end_at")):
            setattr(meeting, k, v)
    if time_changed:
        # Host-side move: push to Google Calendar and tell the invitee (no availability check).
        try:
            booking_service.reschedule_booking(
                db, meeting, data.start_at or meeting.start_at, by_host=True, new_end=data.end_at
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        notifications_updated_this_request.set(True)
    if data.attendee_ids is not None:
        for link in meeting.attendee_links:
            db.delete(link)
        attendee_ids = list(data.attendee_ids)
        for uid in attendee_ids:
            db.add(MeetingAttendee(meeting_id=meeting.id, user_id=uid))
        db.flush()
        _notify_meeting_attendees(db, meeting, attendee_ids)
        notifications_updated_this_request.set(True)
    db.flush()
    log_activity(db, user.id, "meeting_updated", "meeting", meeting.id, details=f"Meeting: {meeting.title}")
    meetings_updated_this_request.set(True)
    db.commit()
    db.refresh(meeting)
    return _meeting_to_response(meeting)


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(
    meeting_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("meetings:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    sales_own_only=Depends(get_is_sales_member),
):
    meeting = db.query(MeetingModel).filter(MeetingModel.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    if not _can_access_meeting(meeting, team_ids, "admin:all" in permissions, manager_scope, sales_own_only, user.id, BOOKINGS_MANAGE in permissions):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    meeting_title = meeting.title
    if (meeting.source or "manual") != "manual" and meeting.status not in ("canceled",):
        # Removing an inbound booking cancels it for real: Google event deleted, invitee told.
        booking_service.cancel_booking(db, meeting, "Removed by our team", by="host")
        notifications_updated_this_request.set(True)
    log_activity(db, user.id, "meeting_deleted", "meeting", meeting_id, details=f"Meeting deleted: {meeting_title}")
    purge_entity_artifacts(db, "meeting", meeting.id)
    db.delete(meeting)
    meetings_updated_this_request.set(True)
    db.commit()
