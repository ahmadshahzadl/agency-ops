from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Client as ClientModel
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse
from app.api.deps import get_current_user, require_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids
from app.services.activity_service import log_activity

router = APIRouter(prefix="/clients", tags=["clients"])


def _can_access_client(
    client: ClientModel,
    user_team_ids: set[UUID],
    is_admin: bool,
    manager_scope: set[UUID] | None = None,
) -> bool:
    if is_admin:
        return True
    if manager_scope is not None:
        return client.created_by is not None and client.created_by in manager_scope
    if client.team_id is None:
        return False
    return client.team_id in user_team_ids


@router.get("", response_model=list[ClientResponse])
def list_clients(
    db: Session = Depends(get_db),
    user=Depends(require_permission("clients:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    q: str | None = None,
):
    qry = db.query(ClientModel).filter(ClientModel.deleted_at.is_(None))
    if "admin:all" not in permissions:
        if manager_scope is not None:
            qry = qry.filter(ClientModel.created_by.in_(manager_scope))
        elif not team_ids:
            return []
        else:
            qry = qry.filter(ClientModel.team_id.in_(team_ids))
    if q:
        qry = qry.filter(ClientModel.name.ilike(f"%{q}%"))
    return qry.offset(skip).limit(limit).all()


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    data: ClientCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("clients:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    if "admin:all" not in permissions and data.team_id and data.team_id not in team_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign client to this team")
    client = ClientModel(
        name=data.name,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        address=data.address,
        team_id=data.team_id,
        created_by=user.id,
    )
    db.add(client)
    db.flush()
    log_activity(db, user.id, "client_created", "client", client.id, details=f"Client: {client.name}")
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("clients:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    client = db.query(ClientModel).filter(ClientModel.id == client_id, ClientModel.deleted_at.is_(None)).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if not _can_access_client(client, team_ids, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: UUID,
    data: ClientUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("clients:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    client = db.query(ClientModel).filter(ClientModel.id == client_id, ClientModel.deleted_at.is_(None)).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if not _can_access_client(client, team_ids, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if "admin:all" not in permissions and data.team_id is not None and data.team_id not in team_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign to this team")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(client, k, v)
    db.flush()
    log_activity(db, user.id, "client_updated", "client", client.id, details=f"Client: {client.name}")
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("clients:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    from datetime import datetime, timezone
    client = db.query(ClientModel).filter(ClientModel.id == client_id, ClientModel.deleted_at.is_(None)).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if not _can_access_client(client, team_ids, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    from app.models import Project as ProjectModel
    active_projects = db.query(ProjectModel.id).filter(
        ProjectModel.client_id == client_id, ProjectModel.deleted_at.is_(None)
    ).count()
    if active_projects:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Client has {active_projects} active project(s); delete or finish them first",
        )
    client_name = client.name
    log_activity(db, user.id, "client_deleted", "client", client_id, details=f"Client deleted: {client_name}")
    client.deleted_at = datetime.now(timezone.utc)
    db.commit()
