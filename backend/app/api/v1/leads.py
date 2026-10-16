"""Leads API: CRUD and convert-to-client. Lead managers see team leads; sales members see own only."""
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_
from app.database import get_db
from app.models import Lead as LeadModel, LeadInteraction, Client, Project, ActivityLog, Meeting, Quote, User
from app.schemas.lead import (
    LeadCreate, LeadUpdate, LeadResponse, LeadConvertRequest,
    LeadInteractionCreate, LeadInteractionResponse, LeadTimelineItem, INTERACTION_TYPES,
)
from app.schemas.client import ClientCreate, ClientResponse
from app.schemas.project import ProjectCreate, ProjectResponse
from app.api.deps import get_current_user, require_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids, get_is_sales_member, get_sales_team_user_ids
from app.services.permission_service import BOOKINGS_MANAGE
from app.services.cleanup_service import purge_entity_artifacts
from app.services.activity_service import log_activity

router = APIRouter(prefix="/leads", tags=["leads"])

# Stages where only management (manager/admin) can edit or delete the lead; members cannot.
_LOCKED_STAGES_FOR_MEMBERS = frozenset({"converted", "closed"})
LEAD_STATUSES = ("new", "contacted", "qualified", "converted", "lost", "closed", "dead")


INBOUND_SOURCES = ("website", "calendly")


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
    bookings_access: bool = False,
) -> bool:
    """New leads: visible to all sales team. Once lead leaves 'new': only assignee, manager, admin.
    bookings:manage additionally sees every inbound (website/Calendly) lead."""
    if is_admin:
        return True
    if bookings_access and (lead.source or "") in INBOUND_SOURCES:
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
        if BOOKINGS_MANAGE in permissions:
            conds.append(LeadModel.source.in_(list(INBOUND_SOURCES)))
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
    db.flush()
    log_activity(db, user.id, "lead_created", "lead", lead.id, details=f"Lead: {lead.company_name}")
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
    if not _can_access_lead(lead, user.id, team_ids, "admin:all" in permissions, manager_scope, sales_team_user_ids, BOOKINGS_MANAGE in permissions):
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
    if not _can_access_lead(lead, user.id, team_ids, "admin:all" in permissions, manager_scope, sales_team_user_ids, BOOKINGS_MANAGE in permissions):
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
    old_status = lead.status
    # When lead leaves "new", auto-assign to current user if not yet assigned
    if lead.status == "new" and dump.get("status") and dump["status"] != "new" and lead.assigned_to is None:
        lead.assigned_to = user.id
    for k, v in dump.items():
        if k == "assigned_team_id" and v and "admin:all" not in permissions and v not in team_ids:
            continue  # skip invalid assignment
        if k == "assigned_to" and v and "admin:all" not in permissions and manager_scope is None and v != user.id:
            continue  # only admin/manager can assign to others
        setattr(lead, k, v)
    db.flush()
    status_change = f"; status: {old_status} → {lead.status}" if "status" in dump and old_status != lead.status else ""
    log_activity(db, user.id, "lead_updated", "lead", lead.id, details=f"Lead: {lead.company_name}{status_change}")
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
    if not _can_access_lead(lead, user.id, team_ids, "admin:all" in permissions, manager_scope, sales_team_user_ids, BOOKINGS_MANAGE in permissions):
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
        db.flush()
        log_activity(db, user.id, "lead_converted", "lead", lead.id, details=f"Lead '{lead.company_name}' → Client + Project")
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
    if not _can_access_lead(lead, user.id, team_ids, "admin:all" in permissions, manager_scope, sales_team_user_ids, BOOKINGS_MANAGE in permissions):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    # Only management can delete leads that are in converted or closed stage
    if not _is_management(permissions, manager_scope):
        if lead.status in _LOCKED_STAGES_FOR_MEMBERS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only management can delete a lead in converted or closed stage",
            )
    company_name = lead.company_name
    log_activity(db, user.id, "lead_deleted", "lead", None, details=f"Lead deleted: {company_name}")
    purge_entity_artifacts(db, "lead", lead.id)
    db.delete(lead)
    db.commit()


# --- Interactions (contact history) and the merged timeline ---------------------------------

def _load_lead_for(
    db: Session, lead_id: UUID, user, permissions, team_ids, manager_scope, sales_team_user_ids
) -> LeadModel:
    lead = db.query(LeadModel).filter(LeadModel.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    if not _can_access_lead(lead, user.id, team_ids, "admin:all" in permissions, manager_scope, sales_team_user_ids, BOOKINGS_MANAGE in permissions):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return lead


def _recompute_lead_contact_fields(db: Session, lead: LeadModel) -> None:
    """Keep the denormalised last_contact_at / next_follow_up_at in step with the interactions."""
    rows = db.query(LeadInteraction.occurred_at, LeadInteraction.next_follow_up_at).filter(LeadInteraction.lead_id == lead.id).all()
    lead.last_contact_at = max((r[0] for r in rows), default=None)
    lead.next_follow_up_at = max((r[1] for r in rows if r[1] is not None), default=None)


def _user_name(u) -> str | None:
    if not u:
        return None
    return u.full_name or u.email


@router.get("/{lead_id}/interactions", response_model=list[LeadInteractionResponse])
def list_lead_interactions(
    lead_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("leads:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    sales_team_user_ids=Depends(get_sales_team_user_ids),
):
    lead = _load_lead_for(db, lead_id, user, permissions, team_ids, manager_scope, sales_team_user_ids)
    rows = (
        db.query(LeadInteraction)
        .options(joinedload(LeadInteraction.created_by_user))
        .filter(LeadInteraction.lead_id == lead.id)
        .order_by(LeadInteraction.occurred_at.desc(), LeadInteraction.created_at.desc())
        .all()
    )
    return rows


@router.post("/{lead_id}/interactions", response_model=LeadInteractionResponse, status_code=status.HTTP_201_CREATED)
def create_lead_interaction(
    lead_id: UUID,
    data: LeadInteractionCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("leads:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    sales_team_user_ids=Depends(get_sales_team_user_ids),
):
    """Log a call, email, meeting or message with the prospect. Optionally moves the lead to a new
    stage in the same step (same rules as PATCH: members cannot touch converted/closed leads)."""
    lead = _load_lead_for(db, lead_id, user, permissions, team_ids, manager_scope, sales_team_user_ids)
    if data.type not in INTERACTION_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="type must be one of: " + ", ".join(INTERACTION_TYPES))
    summary = (data.summary or "").strip()
    if not summary:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="summary is required")
    new_status = data.status if data.status and data.status != lead.status else None
    if new_status:
        if new_status not in LEAD_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status must be one of: " + ", ".join(LEAD_STATUSES))
        if not _is_management(permissions, manager_scope) and lead.status in _LOCKED_STAGES_FOR_MEMBERS:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only management can change a lead in converted or closed stage")
        if lead.converted_to_client_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead already converted")

    row = LeadInteraction(
        lead_id=lead.id,
        type=data.type,
        summary=summary,
        occurred_at=data.occurred_at or datetime.now(timezone.utc),
        next_follow_up_at=data.next_follow_up_at,
        created_by=user.id,
    )
    db.add(row)
    # Someone who logs contact with an unclaimed lead is working it: claim it the way PATCH does.
    if lead.assigned_to is None:
        lead.assigned_to = user.id
    old_status = lead.status
    if new_status:
        lead.status = new_status
    db.flush()
    _recompute_lead_contact_fields(db, lead)
    status_change = f"; status: {old_status} -> {lead.status}" if new_status else ""
    log_activity(
        db, user.id, "lead_interaction_logged", "lead", lead.id,
        details=f"{data.type.capitalize()} with {lead.company_name}: {summary[:160]}{status_change}",
    )
    db.commit()
    row = db.query(LeadInteraction).options(joinedload(LeadInteraction.created_by_user)).get(row.id)
    return row


@router.delete("/{lead_id}/interactions/{interaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead_interaction(
    lead_id: UUID,
    interaction_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("leads:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    sales_team_user_ids=Depends(get_sales_team_user_ids),
):
    lead = _load_lead_for(db, lead_id, user, permissions, team_ids, manager_scope, sales_team_user_ids)
    row = db.query(LeadInteraction).filter(LeadInteraction.id == interaction_id, LeadInteraction.lead_id == lead.id).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interaction not found")
    if row.created_by != user.id and not _is_management(permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the author or management can delete this entry")
    db.delete(row)
    db.flush()
    _recompute_lead_contact_fields(db, lead)
    db.commit()


@router.get("/{lead_id}/timeline", response_model=list[LeadTimelineItem])
def get_lead_timeline(
    lead_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("leads:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    sales_team_user_ids=Depends(get_sales_team_user_ids),
):
    """Everything that happened with this lead, newest first: logged interactions, stage changes and
    other audit entries, meetings booked with the prospect, and quotes sent to them."""
    lead = _load_lead_for(db, lead_id, user, permissions, team_ids, manager_scope, sales_team_user_ids)
    items: list[LeadTimelineItem] = []

    interactions = (
        db.query(LeadInteraction)
        .options(joinedload(LeadInteraction.created_by_user))
        .filter(LeadInteraction.lead_id == lead.id)
        .all()
    )
    for i in interactions:
        items.append(LeadTimelineItem(
            id=f"interaction:{i.id}", kind="interaction", type=i.type, title=i.type.capitalize(),
            details=i.summary, by_name=_user_name(i.created_by_user), occurred_at=i.occurred_at,
            next_follow_up_at=i.next_follow_up_at, reference_id=i.id,
        ))

    logs = (
        db.query(ActivityLog)
        .options(joinedload(ActivityLog.user))
        .filter(ActivityLog.entity_type == "lead", ActivityLog.entity_id == lead.id)
        .all()
    )
    for log in logs:
        if log.action == "lead_interaction_logged":
            continue  # the interaction row above already covers it
        items.append(LeadTimelineItem(
            id=f"activity:{log.id}", kind="activity", type=log.action,
            title=log.action.replace("lead_", "Lead ").replace("_", " ").capitalize(),
            details=log.details, by_name=_user_name(log.user), occurred_at=log.created_at, reference_id=log.id,
        ))

    meetings = (
        db.query(Meeting)
        .options(joinedload(Meeting.host), joinedload(Meeting.assignee), joinedload(Meeting.created_by_user))
        .filter(Meeting.lead_id == lead.id)
        .all()
    )
    for m in meetings:
        who = _user_name(m.host) or _user_name(m.assignee) or _user_name(m.created_by_user)
        details = m.outcome_note or m.description
        if m.status == "canceled" and m.cancel_reason:
            details = f"Canceled: {m.cancel_reason}"
        items.append(LeadTimelineItem(
            id=f"meeting:{m.id}", kind="meeting", type=m.status, title=f"Meeting: {m.title}",
            details=details, by_name=who, occurred_at=m.start_at, reference_id=m.id,
        ))

    quotes = db.query(Quote).filter(Quote.lead_id == lead.id).all()
    author_ids = [q.created_by for q in quotes if q.created_by]
    quote_authors = {u.id: u for u in db.query(User).filter(User.id.in_(author_ids)).all()} if author_ids else {}
    for q in quotes:
        items.append(LeadTimelineItem(
            id=f"quote:{q.id}", kind="quote", type=q.status, title=f"Quote {q.number}: {q.title}",
            details=f"{q.currency} {q.total:,.2f} ({q.status})", by_name=_user_name(quote_authors.get(q.created_by)),
            occurred_at=q.created_at, reference_id=q.id,
        ))

    items.sort(key=lambda x: x.occurred_at, reverse=True)
    return items
