"""Helpers for notes: entity existence and object-level access checks."""
from uuid import UUID
from sqlalchemy.orm import Session
from app.models import (
    Lead, Client, Project, Task, Meeting, Invoice, Expense, Announcement,
)


def entity_exists(db: Session, entity_type: str, entity_id: UUID) -> bool:
    """Return True if the given entity exists. Used to avoid creating notes for invalid IDs."""
    model_map = {
        "lead": Lead,
        "client": Client,
        "project": Project,
        "task": Task,
        "meeting": Meeting,
        "invoice": Invoice,
        "expense": Expense,
        "announcement": Announcement,
    }
    model = model_map.get(entity_type)
    if not model:
        return False
    if entity_type == "client":
        return db.query(model).filter(model.id == entity_id, model.deleted_at.is_(None)).first() is not None
    if entity_type == "project":
        return db.query(model).filter(model.id == entity_id, model.deleted_at.is_(None)).first() is not None
    return db.query(model).filter(model.id == entity_id).first() is not None


def can_access_entity(
    db: Session,
    entity_type: str,
    entity_id: UUID,
    user,
    permissions: set[str],
    team_ids: set[UUID],
    manager_scope: set[UUID] | None,
) -> bool:
    """Object-level check that the user may see the entity a note is attached to.

    Reuses each entity's own router scoping so notes never grant wider visibility
    than the entity itself (e.g. an employee must not read invoice notes when the
    finance API would deny them the invoice).
    """
    is_admin = "admin:all" in permissions
    if is_admin:
        return True
    # Imported lazily: routers import this service at module load.
    if entity_type == "client":
        from app.api.v1.clients import _can_access_client
        client = db.query(Client).filter(Client.id == entity_id).first()
        return client is not None and _can_access_client(client, team_ids, is_admin, manager_scope)
    if entity_type == "lead":
        from app.api.v1.leads import _can_access_lead
        from app.api.deps import get_sales_team_user_ids
        lead = db.query(Lead).filter(Lead.id == entity_id).first()
        return lead is not None and _can_access_lead(
            lead, user.id, team_ids, is_admin, manager_scope, get_sales_team_user_ids(db)
        )
    if entity_type == "project":
        from app.api.v1.projects import _can_access_project
        project = db.query(Project).filter(Project.id == entity_id).first()
        return project is not None and _can_access_project(project, user.id, team_ids, is_admin, manager_scope, db)
    if entity_type == "task":
        from app.api.v1.tasks import _can_access_task
        task = db.query(Task).filter(Task.id == entity_id).first()
        return task is not None and _can_access_task(task, user.id, is_admin, manager_scope)
    if entity_type == "meeting":
        from app.api.v1.meetings import _can_access_meeting
        meeting = db.query(Meeting).filter(Meeting.id == entity_id).first()
        role_names = [r.name for r in user.roles] if getattr(user, "roles", None) else []
        sales_own_only = "sales" in role_names and manager_scope is None
        return meeting is not None and _can_access_meeting(
            meeting, team_ids, is_admin, manager_scope, sales_own_only, user.id
        )
    if entity_type == "invoice":
        from app.api.v1.finance import _can_access_invoice_client
        invoice = db.query(Invoice).filter(Invoice.id == entity_id).first()
        return invoice is not None and _can_access_invoice_client(invoice.client_id, db, team_ids, is_admin, manager_scope)
    if entity_type == "expense":
        from app.api.v1.finance import _can_access_expense_project
        expense = db.query(Expense).filter(Expense.id == entity_id).first()
        return expense is not None and _can_access_expense_project(expense, team_ids, is_admin, manager_scope)
    if entity_type == "announcement":
        ann = db.query(Announcement).filter(Announcement.id == entity_id).first()
        if ann is None:
            return False
        if ann.target_type == "all" or ann.created_by_id == user.id:
            return True
        return user.id in (ann.target_user_ids or [])
    return False
