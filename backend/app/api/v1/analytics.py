from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Client, Project, Task, Invoice
from app.schemas.analytics import AnalyticsOverview
from app.api.deps import get_current_user, require_permission, get_user_permissions, get_user_team_ids

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def overview(
    db: Session = Depends(get_db),
    user=Depends(require_permission("analytics:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
):
    from decimal import Decimal
    if "admin:all" in permissions:
        total_clients = db.query(func.count(Client.id)).filter(Client.deleted_at.is_(None)).scalar() or 0
        active_projects = db.query(func.count(Project.id)).filter(
            Project.deleted_at.is_(None), Project.status == "active",
        ).scalar() or 0
        tasks_todo = db.query(func.count(Task.id)).filter(Task.status == "todo").scalar() or 0
        tasks_in_progress = db.query(func.count(Task.id)).filter(Task.status == "in_progress").scalar() or 0
        tasks_done = db.query(func.count(Task.id)).filter(Task.status == "done").scalar() or 0
        revenue_total = db.query(func.coalesce(func.sum(Invoice.amount), 0)).filter(Invoice.status == "paid").scalar()
        revenue_total = Decimal(str(revenue_total or 0))
        outstanding_total = db.query(func.coalesce(func.sum(Invoice.amount), 0)).filter(
            Invoice.status.in_(["sent", "overdue"])
        ).scalar()
        outstanding_total = Decimal(str(outstanding_total or 0))
    else:
        if not team_ids:
            return AnalyticsOverview(
                total_clients=0, active_projects=0, tasks_todo=0, tasks_in_progress=0, tasks_done=0,
                revenue_total=Decimal("0"), outstanding_total=Decimal("0"),
            )
        total_clients = db.query(func.count(Client.id)).filter(
            Client.deleted_at.is_(None), Client.team_id.in_(team_ids),
        ).scalar() or 0
        active_projects = db.query(func.count(Project.id)).join(Client).filter(
            Project.deleted_at.is_(None), Project.status == "active", Client.team_id.in_(team_ids),
        ).scalar() or 0
        tasks_todo = db.query(func.count(Task.id)).join(Project).join(Client).filter(
            Task.status == "todo", Client.team_id.in_(team_ids),
        ).scalar() or 0
        tasks_in_progress = db.query(func.count(Task.id)).join(Project).join(Client).filter(
            Task.status == "in_progress", Client.team_id.in_(team_ids),
        ).scalar() or 0
        tasks_done = db.query(func.count(Task.id)).join(Project).join(Client).filter(
            Task.status == "done", Client.team_id.in_(team_ids),
        ).scalar() or 0
        revenue_total = db.query(func.coalesce(func.sum(Invoice.amount), 0)).join(Client).filter(
            Invoice.status == "paid", Client.team_id.in_(team_ids),
        ).scalar()
        revenue_total = Decimal(str(revenue_total or 0))
        outstanding_total = db.query(func.coalesce(func.sum(Invoice.amount), 0)).join(Client).filter(
            Invoice.status.in_(["sent", "overdue"]), Client.team_id.in_(team_ids),
        ).scalar()
        outstanding_total = Decimal(str(outstanding_total or 0))
    return AnalyticsOverview(
        total_clients=total_clients,
        active_projects=active_projects,
        tasks_todo=tasks_todo,
        tasks_in_progress=tasks_in_progress,
        tasks_done=tasks_done,
        revenue_total=revenue_total,
        outstanding_total=outstanding_total,
    )
