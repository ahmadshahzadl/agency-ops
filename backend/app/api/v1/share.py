"""Client-facing project progress: managers/admins mint revocable share links;
the public status endpoint returns a sanitized snapshot (no assignees, no
descriptions, no QA notes, no internal identifiers) for anyone with the token."""
import secrets
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import ProjectShareLink, Project as ProjectModel, Task as TaskModel, Milestone as MilestoneModel
from app.api.deps import require_permission, get_user_permissions, get_manager_scope_user_ids
from app.services.activity_service import log_activity
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

router = APIRouter(tags=["share"])


class ShareLinkCreate(BaseModel):
    label: Optional[str] = None


class ShareLinkResponse(BaseModel):
    id: UUID
    project_id: UUID
    token: str
    label: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PublicTask(BaseModel):
    title: str
    status: str
    item_type: str
    due_date: Optional[str] = None


class PublicMilestone(BaseModel):
    name: str
    due_date: Optional[str] = None
    completed: bool
    task_total: int = 0
    task_done: int = 0


class PublicStatusResponse(BaseModel):
    project_name: str
    project_status: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_tasks: int
    counts: dict[str, int]
    percent_done: int
    tasks: list[PublicTask]
    milestones: list[PublicMilestone] = []
    generated_at: datetime


def _require_project_manager(db: Session, project_id: UUID, user, permissions, manager_scope) -> ProjectModel:
    proj = db.query(ProjectModel).filter(ProjectModel.id == project_id, ProjectModel.deleted_at.is_(None)).first()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if "admin:all" in permissions:
        return proj
    if manager_scope is not None and proj.owner_id is not None and proj.owner_id in manager_scope:
        return proj
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins or the project's manager can manage share links")


@router.post("/projects/{project_id}/share-links", response_model=ShareLinkResponse, status_code=status.HTTP_201_CREATED)
def create_share_link(
    project_id: UUID,
    data: ShareLinkCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    proj = _require_project_manager(db, project_id, user, permissions, manager_scope)
    link = ProjectShareLink(
        project_id=project_id,
        token=secrets.token_urlsafe(24),
        label=(data.label or "").strip() or None,
        created_by=user.id,
    )
    db.add(link)
    db.flush()
    log_activity(db, user.id, "share_link_created", "project", project_id, details=f"Share link created for: {proj.name}")
    db.commit()
    db.refresh(link)
    return link


@router.get("/projects/{project_id}/share-links", response_model=list[ShareLinkResponse])
def list_share_links(
    project_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    _require_project_manager(db, project_id, user, permissions, manager_scope)
    return db.query(ProjectShareLink).filter(ProjectShareLink.project_id == project_id).order_by(ProjectShareLink.created_at.desc()).all()


@router.delete("/share-links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_share_link(
    link_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    link = db.query(ProjectShareLink).filter(ProjectShareLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
    proj = _require_project_manager(db, link.project_id, user, permissions, manager_scope)
    db.delete(link)
    db.flush()
    log_activity(db, user.id, "share_link_revoked", "project", link.project_id, details=f"Share link revoked for: {proj.name}")
    db.commit()


@router.get("/public/status/{token}", response_model=PublicStatusResponse)
def public_status(token: str, db: Session = Depends(get_db)):
    """Public, unauthenticated, sanitized project snapshot for clients holding a share link."""
    link = db.query(ProjectShareLink).filter(ProjectShareLink.token == token).first()
    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    proj = db.query(ProjectModel).filter(ProjectModel.id == link.project_id, ProjectModel.deleted_at.is_(None)).first()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    rows = db.query(TaskModel.status, func.count(TaskModel.id)).filter(TaskModel.project_id == proj.id).group_by(TaskModel.status).all()
    counts = {s: c for s, c in rows}
    total = sum(counts.values())
    done = counts.get("done", 0)
    tasks = (
        db.query(TaskModel)
        .filter(TaskModel.project_id == proj.id)
        .order_by(TaskModel.status, TaskModel.order_index, TaskModel.created_at)
        .limit(200)
        .all()
    )
    milestones = db.query(MilestoneModel).filter(MilestoneModel.project_id == proj.id).order_by(
        MilestoneModel.position, MilestoneModel.due_date.nulls_last()
    ).all()
    public_milestones = []
    for m in milestones:
        mt = db.query(func.count(TaskModel.id)).filter(TaskModel.milestone_id == m.id).scalar() or 0
        md = db.query(func.count(TaskModel.id)).filter(TaskModel.milestone_id == m.id, TaskModel.status == "done").scalar() or 0
        public_milestones.append(PublicMilestone(
            name=m.name, due_date=str(m.due_date) if m.due_date else None,
            completed=m.completed_at is not None, task_total=mt, task_done=md,
        ))
    return PublicStatusResponse(
        project_name=proj.name,
        project_status=proj.status or "active",
        start_date=str(proj.start_date) if proj.start_date else None,
        end_date=str(proj.end_date) if proj.end_date else None,
        total_tasks=total,
        counts=counts,
        percent_done=round(done * 100 / total) if total else 0,
        milestones=public_milestones,
        tasks=[
            PublicTask(
                title=t.title,
                # Clients see a simplified pipeline: internal QA states read as "in review"
                status="review" if t.status in ("review", "qa_failed") else t.status,
                item_type=t.item_type or "task",
                due_date=str(t.due_date) if t.due_date else None,
            )
            for t in tasks
        ],
        generated_at=datetime.utcnow(),
    )
