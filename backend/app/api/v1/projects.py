from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project as ProjectModel, Client as ClientModel
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.api.deps import get_current_user, require_permission, get_user_permissions, get_user_team_ids

router = APIRouter(prefix="/projects", tags=["projects"])


def _can_access_project(project: ProjectModel, team_ids: set[UUID], is_admin: bool) -> bool:
    if is_admin:
        return True
    if not project.client or project.client.team_id is None:
        return False
    return project.client.team_id in team_ids


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    client_id: UUID | None = None,
    status_filter: str | None = None,
):
    qry = db.query(ProjectModel).join(ClientModel).filter(ProjectModel.deleted_at.is_(None))
    if "admin:all" not in permissions:
        if not team_ids:
            return []
        qry = qry.filter(ClientModel.team_id.in_(team_ids))
    if client_id:
        qry = qry.filter(ProjectModel.client_id == client_id)
    if status_filter:
        qry = qry.filter(ProjectModel.status == status_filter)
    return qry.offset(skip).limit(limit).all()


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
):
    client = db.query(ClientModel).filter(ClientModel.id == data.client_id).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if "admin:all" not in permissions and (not client.team_id or client.team_id not in team_ids):
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
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
):
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id, ProjectModel.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not _can_access_project(project, team_ids, "admin:all" in permissions):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
):
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id, ProjectModel.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not _can_access_project(project, team_ids, "admin:all" in permissions):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    updates = data.model_dump(exclude_unset=True)
    if "assigned_team_id" in updates and updates["assigned_team_id"] and "admin:all" not in permissions:
        if updates["assigned_team_id"] not in team_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign project to this team")
    for k, v in updates.items():
        setattr(project, k, v)
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
):
    from datetime import datetime, timezone
    project = db.query(ProjectModel).filter(ProjectModel.id == project_id, ProjectModel.deleted_at.is_(None)).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not _can_access_project(project, team_ids, "admin:all" in permissions):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    project.deleted_at = datetime.now(timezone.utc)
    db.commit()
