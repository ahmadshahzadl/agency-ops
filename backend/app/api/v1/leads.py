"""Leads API: CRUD and convert-to-client. Lead managers see team leads; sales members see own only."""
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from app.database import get_db
from app.models import Lead as LeadModel, Client, Project
from app.schemas.lead import LeadCreate, LeadUpdate, LeadResponse, LeadConvertRequest
from app.schemas.client import ClientCreate, ClientResponse
from app.schemas.project import ProjectCreate, ProjectResponse
from app.api.deps import get_current_user, require_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids, get_is_sales_member, get_sales_team_user_ids

router = APIRouter(prefix="/leads", tags=["leads"])

# Stages where only management (manager/admin) can edit or delete the lead; members cannot.
_LOCKED_STAGES_FOR_MEMBERS = frozenset({"converted", "closed"})


def _is_management(permissions: set, manager_scope: set[UUID] | None) -> bool:
    """True if user is admin or has direct reports (manager)."""
    return "admin:all" in permissions or manager_scope is not None


def _can_access_lead(
    lead: LeadModel,
    user_id: UUID,
    user_team_ids: set[UUID],
    is_admin: bool,
    manager_scope: set[UUID] | None,
    sales_team_user_ids: set[UUID],
) -> bool:
    """New leads: visible to all sales team. Once lead leaves 'new': only assignee, manager, admin."""
    if is_admin:
        return True
    if lead.status == "new":
        return user_id in sales_team_user_ids
    # Non-new: assignee or manager (created_by is in manager's scope)
    if lead.assigned_to == user_id:
        return True
    if manager_scope is not None and lead.created_by is not None and lead.created_by in manager_scope:
        return True
    return False


@router.get("", response_model=list[LeadResponse])
def list_leads(
    db: Session = Depends(get_db),
    user=Depends(require_permission("leads:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    sales_team_user_ids=Depends(get_sales_team_user_ids),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    q: str | None = None,
    status: str | None = None,
):
    qry = db.query(LeadModel).options(joinedload(LeadModel.created_by_user), joinedload(LeadModel.assigned_to_user))
    if "admin:all" not in permissions:
        # New leads: all sales team. Non-new: only assignee or manager (created_by in scope)
        conds = [
            and_(
                LeadModel.status != "new",
                or_(
                    LeadModel.assigned_to == user.id,
                    LeadModel.created_by.in_(manager_scope) if manager_scope else False,
                    LeadModel.assigned_to.in_(manager_scope) if manager_scope else False,
                )
                if manager_scope
                else (LeadModel.assigned_to == user.id),
            )
        ]
        if user.id in sales_team_user_ids:
            conds.insert(0, LeadModel.status == "new")
        qry = qry.filter(or_(*conds))
    if q:
        qry = qry.filter(
            or_(
                LeadModel.company_name.ilike(f"%{q}%"),
                LeadModel.contact_name.ilike(f"%{q}%"),
                LeadModel.contact_email.ilike(f"%{q}%"),
            )
        )
    if status:
        qry = qry.filter(LeadModel.status == status)
    qry = qry.order_by(LeadModel.created_at.desc())
    return qry.offset(skip).limit(limit).all()


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    data: LeadCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("leads:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    sales_own_only=Depends(get_is_sales_member),
):
    if data.assigned_team_id and "admin:all" not in permissions and data.assigned_team_id not in team_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign lead to this team")
    lead = LeadModel(
        company_name=data.company_name,
        contact_name=data.contact_name,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        source=data.source,
        status=data.status or "new",
        notes=data.notes,
        assigned_team_id=data.assigned_team_id,
        assigned_to=data.assigned_to,
        created_by=user.id,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    lead = db.query(LeadModel).options(joinedload(LeadModel.created_by_user), joinedload(LeadModel.assigned_to_user)).get(lead.id)
    return lead


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("leads:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    sales_team_user_ids=Depends(get_sales_team_user_ids),
):
    lead = db.query(LeadModel).options(joinedload(LeadModel.created_by_user), joinedload(LeadModel.assigned_to_user)).filter(LeadModel.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if not _can_access_lead(lead, user.id, team_ids, "admin:all" in permissions, manager_scope, sales_team_user_ids):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return lead


@router.patch("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: UUID,
    data: LeadUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("leads:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    sales_team_user_ids=Depends(get_sales_team_user_ids),
):
    lead = db.query(LeadModel).filter(LeadModel.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if not _can_access_lead(lead, user.id, team_ids, "admin:all" in permissions, manager_scope, sales_team_user_ids):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    # Only management can edit leads that are already in converted or closed stage
    if not _is_management(permissions, manager_scope):
        if lead.status in _LOCKED_STAGES_FOR_MEMBERS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only management can change a lead in converted or closed stage",
            )
    if lead.converted_to_client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead already converted")
    dump = data.model_dump(exclude_unset=True)
    # When lead leaves "new", auto-assign to current user if not yet assigned
    if lead.status == "new" and dump.get("status") and dump["status"] != "new" and lead.assigned_to is None:
        lead.assigned_to = user.id
    for k, v in dump.items():
        if k == "assigned_team_id" and v and "admin:all" not in permissions and v not in team_ids:
            continue  # skip invalid assignment
        if k == "assigned_to" and v and "admin:all" not in permissions and manager_scope is None and v != user.id:
            continue  # only admin/manager can assign to others
        setattr(lead, k, v)
    db.commit()
    lead = db.query(LeadModel).options(joinedload(LeadModel.created_by_user), joinedload(LeadModel.assigned_to_user)).get(lead.id)
    return lead


@router.post("/{lead_id}/convert", response_model=dict)
def convert_lead(
    lead_id: UUID,
    data: LeadConvertRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("leads:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    sales_team_user_ids=Depends(get_sales_team_user_ids),
):
    lead = db.query(LeadModel).filter(LeadModel.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if not _can_access_lead(lead, user.id, team_ids, "admin:all" in permissions, manager_scope, sales_team_user_ids):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    # Only management can create client and project from a lead; members only mark status as converted
    if not _is_management(permissions, manager_scope):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only management can create client and project from a lead",
        )
    if lead.converted_to_client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead already converted")
    if lead.assigned_to is None:
        lead.assigned_to = user.id
    if data.client_team_id and "admin:all" not in permissions and data.client_team_id not in team_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign client to this team")

    try:
        client = Client(
            name=lead.company_name,
            contact_email=lead.contact_email,
            contact_phone=lead.contact_phone,
            address=None,
            team_id=data.client_team_id or lead.assigned_team_id,
            created_by=user.id,
        )
        db.add(client)
        db.flush()

        project = None
        if data.create_project:
            project = Project(
                client_id=client.id,
                name=data.project_name or lead.company_name,
                description=f"Converted from lead: {lead.company_name}",
                status="draft",
                pipeline_stage=data.project_pipeline_stage or "discovery",
                assigned_team_id=data.project_assigned_team_id,
                owner_id=user.id,
            )
            db.add(project)
            db.flush()

        lead.converted_to_client_id = client.id
        lead.converted_at = datetime.now(timezone.utc)
        lead.status = "converted"
        db.commit()
        db.refresh(client)
        if project:
            db.refresh(project)
        return {
            "message": "Lead converted to client",
            "client_id": str(client.id),
            "project_id": str(project.id) if project else None,
        }
    except Exception:
        db.rollback()
        lead = db.query(LeadModel).filter(LeadModel.id == lead_id).first()
        if lead and not lead.converted_to_client_id:
            lead.status = "lost"
            db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Conversion failed; lead has been marked as lost.",
        )


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("leads:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    sales_team_user_ids=Depends(get_sales_team_user_ids),
):
    lead = db.query(LeadModel).filter(LeadModel.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if not _can_access_lead(lead, user.id, team_ids, "admin:all" in permissions, manager_scope, sales_team_user_ids):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    # Only management can delete leads that are in converted or closed stage
    if not _is_management(permissions, manager_scope):
        if lead.status in _LOCKED_STAGES_FOR_MEMBERS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only management can delete a lead in converted or closed stage",
            )
    db.delete(lead)
    db.commit()
