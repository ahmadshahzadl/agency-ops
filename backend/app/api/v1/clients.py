from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import or_, exists
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Client as ClientModel, Lead as LeadModel
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse, CLIENT_STATUSES
from app.api.deps import get_current_user, require_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids
from app.services.activity_service import log_activity

router = APIRouter(prefix="/clients", tags=["clients"])


def _can_access_client(
    client: ClientModel,
    user_team_ids: set[UUID],
    is_admin: bool,
    manager_scope: set[UUID] | None = None,
    user_id: UUID | None = None,
) -> bool:
    if is_admin:
        return True
    # The solutions engineer who owned the lead keeps access to the client it became.
    if user_id and client.source_lead is not None and client.source_lead.assigned_to == user_id:
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
    status: str | None = Query(None, description="prospect | active | archived"),
):
    qry = db.query(ClientModel).filter(ClientModel.deleted_at.is_(None))
    if status:
        if status not in CLIENT_STATUSES:
            raise HTTPException(status_code=400, detail=f"status must be one of: {', '.join(CLIENT_STATUSES)}")
        qry = qry.filter(ClientModel.status == status)
    if "admin:all" not in permissions:
        owned_lead = exists().where(LeadModel.converted_to_client_id == ClientModel.id, LeadModel.assigned_to == user.id)
        if manager_scope is not None:
            qry = qry.filter(or_(ClientModel.created_by.in_(manager_scope), owned_lead))
        elif not team_ids:
            qry = qry.filter(owned_lead)
        else:
            qry = qry.filter(or_(ClientModel.team_id.in_(team_ids), owned_lead))
    if q:
        qry = qry.filter(ClientModel.name.ilike(f"%{q}%"))
    return qry.order_by(ClientModel.created_at.desc()).offset(skip).limit(limit).all()


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
    if data.status not in CLIENT_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"status must be one of: {', '.join(CLIENT_STATUSES)}")
    client = ClientModel(
        name=data.name,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        address=data.address,
        team_id=data.team_id,
        status=data.status,
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
    if not _can_access_client(client, team_ids, "admin:all" in permissions, manager_scope, user.id):
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
    if not _can_access_client(client, team_ids, "admin:all" in permissions, manager_scope, user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    if "admin:all" not in permissions and data.team_id is not None and data.team_id not in team_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign to this team")
    if data.status is not None and data.status not in CLIENT_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"status must be one of: {', '.join(CLIENT_STATUSES)}")
    old_status = client.status
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(client, k, v)
    if data.status is not None and data.status != old_status:
        log_activity(db, user.id, "client_status_changed", "client", client.id, details=f"Client {client.name}: {old_status} -> {data.status}")
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
    if not _can_access_client(client, team_ids, "admin:all" in permissions, manager_scope, user.id):
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
