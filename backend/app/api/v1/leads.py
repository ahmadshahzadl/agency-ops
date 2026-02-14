"""Leads API: CRUD and convert-to-client. Scoped by assigned_team for non-admin."""
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Lead as LeadModel, Client, Project
from app.schemas.lead import LeadCreate, LeadUpdate, LeadResponse, LeadConvertRequest
from app.schemas.client import ClientCreate, ClientResponse
from app.schemas.project import ProjectCreate, ProjectResponse
from app.api.deps import get_current_user, require_permission, get_user_permissions, get_user_team_ids

router = APIRouter(prefix="/leads", tags=["leads"])


def _can_access_lead(lead: LeadModel, user_team_ids: set[UUID], is_admin: bool) -> bool:
    if is_admin:
        return True
    if lead.assigned_team_id is None:
        return True  # unassigned visible to any leads:read
    return lead.assigned_team_id in user_team_ids


@router.get("", response_model=list[LeadResponse])
def list_leads(
    db: Session = Depends(get_db),
    user=Depends(require_permission("leads:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    q: str | None = None,
    status: str | None = None,
):
    qry = db.query(LeadModel)
    if "admin:all" not in permissions:
        # show leads assigned to user's teams or unassigned
        from sqlalchemy import or_
        qry = qry.filter(or_(LeadModel.assigned_team_id.is_(None), LeadModel.assigned_team_id.in_(team_ids)))
    if q:
        from sqlalchemy import or_
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
        created_by=user.id,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("leads:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
):
    lead = db.query(LeadModel).filter(LeadModel.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if not _can_access_lead(lead, team_ids, "admin:all" in permissions):
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
):
    lead = db.query(LeadModel).filter(LeadModel.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if not _can_access_lead(lead, team_ids, "admin:all" in permissions):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if lead.converted_to_client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead already converted")
    for k, v in data.model_dump(exclude_unset=True).items():
        if k == "assigned_team_id" and v and "admin:all" not in permissions and v not in team_ids:
            continue  # skip invalid assignment
        setattr(lead, k, v)
    db.commit()
    db.refresh(lead)
    return lead


@router.post("/{lead_id}/convert", response_model=dict)
def convert_lead(
    lead_id: UUID,
    data: LeadConvertRequest,
    db: Session = Depends(get_db),
    user=Depends(require_permission("leads:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
):
    lead = db.query(LeadModel).filter(LeadModel.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if not _can_access_lead(lead, team_ids, "admin:all" in permissions):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if lead.converted_to_client_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead already converted")
    if data.client_team_id and "admin:all" not in permissions and data.client_team_id not in team_ids:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot assign client to this team")

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


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("leads:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
):
    lead = db.query(LeadModel).filter(LeadModel.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if not _can_access_lead(lead, team_ids, "admin:all" in permissions):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    db.delete(lead)
    db.commit()
