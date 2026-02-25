from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Meeting as MeetingModel, MeetingAttendee, Project as ProjectModel, Client as ClientModel, Notification as NotificationModel
from app.schemas.meeting import MeetingCreate, MeetingUpdate, MeetingResponse
from sqlalchemy import or_, exists
from app.api.deps import get_current_user, require_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids, get_is_sales_member
from app.services.activity_service import log_activity

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
) -> bool:
    if is_admin:
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
):
    qry = db.query(MeetingModel)
    if "admin:all" not in permissions:
        if sales_own_only:
            attendee_exists = exists().where(
                MeetingAttendee.meeting_id == MeetingModel.id,
                MeetingAttendee.user_id == user.id,
            )
            qry = qry.filter(
                or_(MeetingModel.created_by == user.id, attendee_exists)
            )
        elif manager_scope is not None:
            qry = qry.outerjoin(ProjectModel, MeetingModel.project_id == ProjectModel.id).filter(
                MeetingModel.created_by.in_(manager_scope),
                (ProjectModel.id.is_(None)) | (ProjectModel.owner_id.in_(manager_scope)),
            )
        elif not team_ids:
            return []
        else:
            qry = qry.join(ProjectModel).join(ClientModel).filter(ClientModel.team_id.in_(team_ids))
    if project_id:
        qry = qry.filter(MeetingModel.project_id == project_id)
    qry = qry.order_by(MeetingModel.start_at.desc())
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
    if not _can_access_meeting(meeting, team_ids, "admin:all" in permissions, manager_scope, sales_own_only, user.id):
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
    if not _can_access_meeting(meeting, team_ids, "admin:all" in permissions, manager_scope, sales_own_only, user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    for k in ["title", "description", "start_at", "end_at", "location"]:
        v = getattr(data, k, None)
        if v is not None:
            setattr(meeting, k, v)
    if data.attendee_ids is not None:
        for link in meeting.attendee_links:
            db.delete(link)
        attendee_ids = list(data.attendee_ids)
        for uid in attendee_ids:
            db.add(MeetingAttendee(meeting_id=meeting.id, user_id=uid))
        db.flush()
        _notify_meeting_attendees(db, meeting, attendee_ids)
    db.flush()
    log_activity(db, user.id, "meeting_updated", "meeting", meeting.id, details=f"Meeting: {meeting.title}")
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
    if not _can_access_meeting(meeting, team_ids, "admin:all" in permissions, manager_scope, sales_own_only, user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    db.delete(meeting)
    db.commit()
