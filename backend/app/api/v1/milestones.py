"""Project milestones: phases with due dates, completed manually or tracked
via linked tasks. Visible to anyone who can see the project; managed by
admins and the project's manager."""
from datetime import datetime, date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Milestone as MilestoneModel, Project as ProjectModel, Task as TaskModel
from app.schemas.milestone import MilestoneCreate, MilestoneUpdate, MilestoneResponse
from app.api.deps import require_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids
from app.services.activity_service import log_activity

router = APIRouter(tags=["milestones"])


def milestone_state(m: MilestoneModel) -> str:
    if m.completed_at:
        return "completed"
    if m.due_date and m.due_date < date.today():
        return "overdue"
    return "upcoming"


def _milestone_response(db: Session, m: MilestoneModel) -> MilestoneResponse:
    total = db.query(func.count(TaskModel.id)).filter(TaskModel.milestone_id == m.id).scalar() or 0
    done = db.query(func.count(TaskModel.id)).filter(TaskModel.milestone_id == m.id, TaskModel.status == "done").scalar() or 0
    return MilestoneResponse(
        id=m.id, project_id=m.project_id, name=m.name, description=m.description,
        due_date=m.due_date, position=m.position, completed_at=m.completed_at,
        state=milestone_state(m), task_total=total, task_done=done, created_at=m.created_at,
    )


def _get_viewable_project(db, project_id, user, permissions, team_ids, manager_scope) -> ProjectModel:
    from app.api.v1.projects import _can_access_project
    proj = db.query(ProjectModel).filter(ProjectModel.id == project_id, ProjectModel.deleted_at.is_(None)).first()
    if not proj or not _can_access_project(proj, user.id, team_ids, "admin:all" in permissions, manager_scope, db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return proj


def _require_manager(db, project_id, user, permissions, manager_scope) -> ProjectModel:
    proj = db.query(ProjectModel).filter(ProjectModel.id == project_id, ProjectModel.deleted_at.is_(None)).first()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if "admin:all" in permissions:
        return proj
    if manager_scope is not None and proj.owner_id is not None and proj.owner_id in manager_scope:
        return proj
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins or the project's manager can manage milestones")


@router.get("/projects/{project_id}/milestones", response_model=list[MilestoneResponse])
def list_milestones(
    project_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    _get_viewable_project(db, project_id, user, permissions, team_ids, manager_scope)
    rows = db.query(MilestoneModel).filter(MilestoneModel.project_id == project_id).order_by(
        MilestoneModel.position, MilestoneModel.due_date.nulls_last(), MilestoneModel.created_at
    ).all()
    return [_milestone_response(db, m) for m in rows]


@router.post("/projects/{project_id}/milestones", response_model=MilestoneResponse, status_code=status.HTTP_201_CREATED)
def create_milestone(
    project_id: UUID,
    data: MilestoneCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    proj = _require_manager(db, project_id, user, permissions, manager_scope)
    m = MilestoneModel(
        project_id=project_id, name=data.name.strip(), description=data.description,
        due_date=data.due_date, position=data.position,
    )
    db.add(m)
    db.flush()
    log_activity(db, user.id, "milestone_created", "project", project_id, details=f"Milestone on {proj.name}: {m.name}")
    db.commit()
    db.refresh(m)
    return _milestone_response(db, m)


def _get_managed_milestone(db, milestone_id, user, permissions, manager_scope) -> MilestoneModel:
    m = db.query(MilestoneModel).filter(MilestoneModel.id == milestone_id).first()
    if not m:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")
    _require_manager(db, m.project_id, user, permissions, manager_scope)
    return m


@router.patch("/milestones/{milestone_id}", response_model=MilestoneResponse)
def update_milestone(
    milestone_id: UUID,
    data: MilestoneUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    m = _get_managed_milestone(db, milestone_id, user, permissions, manager_scope)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return _milestone_response(db, m)


@router.post("/milestones/{milestone_id}/complete", response_model=MilestoneResponse)
def complete_milestone(
    milestone_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    m = _get_managed_milestone(db, milestone_id, user, permissions, manager_scope)
    m.completed_at = datetime.utcnow()
    log_activity(db, user.id, "milestone_completed", "project", m.project_id, details=f"Milestone completed: {m.name}")
    db.commit()
    db.refresh(m)
    return _milestone_response(db, m)


@router.post("/milestones/{milestone_id}/reopen", response_model=MilestoneResponse)
def reopen_milestone(
    milestone_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    m = _get_managed_milestone(db, milestone_id, user, permissions, manager_scope)
    m.completed_at = None
    db.commit()
    db.refresh(m)
    return _milestone_response(db, m)


@router.delete("/milestones/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_milestone(
    milestone_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    m = _get_managed_milestone(db, milestone_id, user, permissions, manager_scope)
    log_activity(db, user.id, "milestone_deleted", "project", m.project_id, details=f"Milestone deleted: {m.name}")
    db.delete(m)  # tasks detach via SET NULL
    db.commit()
