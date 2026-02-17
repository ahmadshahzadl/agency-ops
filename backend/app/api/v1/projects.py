from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, exists, case
from app.database import get_db
from app.models import Project as ProjectModel, Client as ClientModel, ProjectMember as ProjectMemberModel, Task as TaskModel
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectNameResponse
from app.api.deps import get_current_user, require_permission, require_any_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids
from app.services.activity_service import log_activity

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/names", response_model=list[ProjectNameResponse])
def list_project_names(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
):
    """Return project id and name only. All authenticated users can call this (for displaying project names in meetings/tasks)."""
    qry = (
        db.query(ProjectModel.id, ProjectModel.name)
        .filter(ProjectModel.deleted_at.is_(None))
        .order_by(ProjectModel.name)
    )
    rows = qry.offset(skip).limit(limit).all()
    return [ProjectNameResponse(id=r.id, name=r.name) for r in rows]


def _can_access_project(
    project: ProjectModel,
    user_id: UUID,
    team_ids: set[UUID],
    is_admin: bool,
    manager_scope: set[UUID] | None = None,
    db: Session | None = None,
) -> bool:
    """User can access if admin, or assigned: owner, or assigned team in user's teams, or user is project member."""
    if is_admin:
        return True
    if project.owner_id == user_id:
        return True
    if project.assigned_team_id and project.assigned_team_id in team_ids:
        return True
    if db is not None:
        is_member = db.query(ProjectMemberModel).filter(
            ProjectMemberModel.project_id == project.id,
            ProjectMemberModel.user_id == user_id,
        ).first() is not None
        if is_member:
            return True
    if manager_scope is not None:
        return project.owner_id is not None and project.owner_id in manager_scope
    return False


def _assigned_project_filter(qry, ProjectModel, user_id: UUID, team_ids: set[UUID], manager_scope: set[UUID] | None):
    """Restrict to projects assigned to the user: owner, assigned team, or project member."""
    member_exists = exists().where(
        ProjectMemberModel.project_id == ProjectModel.id,
        ProjectMemberModel.user_id == user_id,
    )
    if manager_scope is not None:
        qry = qry.filter(
            or_(
                ProjectModel.owner_id.in_(manager_scope),
                (ProjectModel.assigned_team_id.isnot(None) & ProjectModel.assigned_team_id.in_(team_ids)),
                member_exists,
            )
        )
    else:
        qry = qry.filter(
            or_(
                ProjectModel.owner_id == user_id,
                (ProjectModel.assigned_team_id.isnot(None) & ProjectModel.assigned_team_id.in_(team_ids)),
                member_exists,
            )
        )
    return qry


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    user=Depends(require_any_permission("projects:read", "dashboard:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    client_id: UUID | None = None,
    status_filter: str | None = None,
):
    qry = db.query(ProjectModel).join(ClientModel).filter(ProjectModel.deleted_at.is_(None))
    if "admin:all" not in permissions:
        qry = _assigned_project_filter(qry, ProjectModel, user.id, team_ids, manager_scope)
    if client_id:
        qry = qry.filter(ProjectModel.client_id == client_id)
    if status_filter:
        qry = qry.filter(ProjectModel.status == status_filter)
    projects = qry.options(joinedload(ProjectModel.client)).offset(skip).limit(limit).all()
    if not projects:
        return []
    project_ids = [p.id for p in projects]
    task_stats = (
        db.query(
            TaskModel.project_id,
            func.count(TaskModel.id).label("total"),
            func.sum(case((TaskModel.status == "done", 1), else_=0)).label("done"),
        )
        .filter(TaskModel.project_id.in_(project_ids))
        .group_by(TaskModel.project_id)
        .all()
    )
    stats_map = {}
    for row in task_stats:
        stats_map[row.project_id] = (row.total or 0, int(row.done or 0))
    out = []
    for p in projects:
        tc, tdc = stats_map.get(p.id, (0, 0))
        data = {k: getattr(p, k) for k in ("id", "client_id", "name", "description", "status", "pipeline_stage", "assigned_team_id", "start_date", "end_date", "owner_id", "created_at", "updated_at")}
        data["client_name"] = p.client.name if p.client else None
        data["task_count"] = tc
        data["task_done_count"] = tdc
        out.append(ProjectResponse(**data))
    return out


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    client = db.query(ClientModel).filter(ClientModel.id == data.client_id).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if "admin:all" not in permissions:
        if manager_scope is not None:
            if client.created_by not in manager_scope:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create project for this client")
        elif not client.team_id or client.team_id not in team_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create project for this client")
    if getattr(data, "assigned_team_id", None) and "admin:all" not in permissions:
        if data.assigned_team_id not in team_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign project to this team")
    project = ProjectModel(
        client_id=data.client_id,
        name=data.name,
        description=data.description,
        status=data.status,
        pipeline_stage=getattr(data, "pipeline_stage", None) or "lead",
        assigned_team_id=getattr(data, "assigned_team_id", None),
        start_date=data.start_date,
        end_date=data.end_date,
        owner_id=data.owner_id or user.id,
    )
    db.add(project)
    db.flush()
    log_activity(db, user.id, "project_created", "project", project.id, details=f"Project: {project.name}")
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_any_permission("projects:read", "dashboard:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id, ProjectModel.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not _can_access_project(project, user.id, team_ids, "admin:all" in permissions, manager_scope, db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    task_total = db.query(func.count(TaskModel.id)).filter(TaskModel.project_id == project_id).scalar() or 0
    task_done = db.query(func.count(TaskModel.id)).filter(TaskModel.project_id == project_id, TaskModel.status == "done").scalar() or 0
    data = {k: getattr(project, k) for k in ("id", "client_id", "name", "description", "status", "pipeline_stage", "assigned_team_id", "start_date", "end_date", "owner_id", "created_at", "updated_at")}
    data["client_name"] = project.client.name if project.client else None
    data["task_count"] = task_total
    data["task_done_count"] = task_done
    return ProjectResponse(**data)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id, ProjectModel.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not _can_access_project(project, user.id, team_ids, "admin:all" in permissions, manager_scope, db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    updates = data.model_dump(exclude_unset=True)
    if "assigned_team_id" in updates and updates["assigned_team_id"] and "admin:all" not in permissions:
        if updates["assigned_team_id"] not in team_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign project to this team")
    for k, v in updates.items():
        setattr(project, k, v)
    db.flush()
    log_activity(db, user.id, "project_updated", "project", project.id, details=f"Project: {project.name}")
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    from datetime import datetime, timezone
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id, ProjectModel.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not _can_access_project(project, user.id, team_ids, "admin:all" in permissions, manager_scope, db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    project.deleted_at = datetime.now(timezone.utc)
    db.commit()
