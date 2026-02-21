"""Managers can see their reports (team members) and their activity log."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User as UserModel, ActivityLog
from app.schemas.activity import ActivityLogWithUserResponse, ReportSummary
from app.api.deps import get_current_user, require_permission

router = APIRouter(prefix="/team-activity", tags=["team-activity"])


@router.get("/my-reports", response_model=list[ReportSummary])
def list_my_reports(
    db: Session = Depends(get_db),
    user=Depends(require_permission("team_activity:read")),
):
    """List users who report to me (my direct reports)."""
    reports = db.query(UserModel).filter(UserModel.manager_id == user.id, UserModel.is_active == True).all()
    return [ReportSummary(id=u.id, email=u.email, full_name=u.full_name) for u in reports]


@router.get("/activity", response_model=list[ActivityLogWithUserResponse])
def list_team_activity(
    db: Session = Depends(get_db),
    user=Depends(require_permission("team_activity:read")),
    report_id: UUID | None = Query(None, description="Filter by one report's user id"),
    action: str | None = Query(None, description="Filter by action type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List activity logs for my reports (team members). Only managers with team_activity:read see this."""
    report_ids = [u.id for u in user.reports]
    if not report_ids:
        return []
    qry = db.query(ActivityLog).filter(ActivityLog.user_id.in_(report_ids))
    if report_id is not None:
        if report_id not in report_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your report")
        qry = qry.filter(ActivityLog.user_id == report_id)
    if action:
        qry = qry.filter(ActivityLog.action == action)
    qry = qry.order_by(ActivityLog.created_at.desc())
    logs = qry.offset(skip).limit(limit).all()
    # Load user info for each log
    user_map = {u.id: (u.email, u.full_name) for u in user.reports}
    return [
        ActivityLogWithUserResponse(
            id=log.id,
            user_id=log.user_id,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            details=log.details,
            created_at=log.created_at,
            user_email=user_map.get(log.user_id, ("", None))[0],
            user_full_name=user_map.get(log.user_id, ("", None))[1],
        )
        for log in logs
    ]
