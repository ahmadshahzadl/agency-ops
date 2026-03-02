from datetime import datetime, timezone, timedelta, date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Client, Project, Task, Invoice, Payment, Expense, Lead, User
from app.schemas.analytics import (
    AnalyticsOverview,
    DashboardResponse,
    ConversionOverTimePoint,
    StatusCount,
)
from sqlalchemy import or_
from app.api.deps import get_current_user, require_any_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def overview(
    db: Session = Depends(get_db),
    user=Depends(require_any_permission("analytics:read", "dashboard:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    from decimal import Decimal
    today = date.today()
    month_start = today.replace(day=1)
    month_end = (month_start + timedelta(days=31)).replace(day=1) - timedelta(days=1)
    if "admin:all" in permissions:
        total_clients = db.query(func.count(Client.id)).filter(Client.deleted_at.is_(None)).scalar() or 0
        active_projects = db.query(func.count(Project.id)).filter(
            Project.deleted_at.is_(None), Project.status == "active",
        ).scalar() or 0
        total_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
        tasks_todo = db.query(func.count(Task.id)).filter(Task.status == "todo").scalar() or 0
        tasks_in_progress = db.query(func.count(Task.id)).filter(Task.status == "in_progress").scalar() or 0
        tasks_done = db.query(func.count(Task.id)).filter(Task.status == "done").scalar() or 0
        revenue_total = db.query(func.coalesce(func.sum(Invoice.amount), 0)).filter(Invoice.status == "paid").scalar()
        revenue_total = Decimal(str(revenue_total or 0))
        outstanding_total = db.query(func.coalesce(func.sum(Invoice.amount), 0)).filter(
            Invoice.status.in_(["sent", "overdue"])
        ).scalar()
        outstanding_total = Decimal(str(outstanding_total or 0))
        revenue_this_month = Decimal(str(db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
            Payment.paid_at >= month_start, Payment.paid_at <= month_end,
        ).scalar() or 0))
        expenses_this_month = Decimal(str(db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
            Expense.expense_date.isnot(None),
            Expense.expense_date >= month_start,
            Expense.expense_date <= month_end,
        ).scalar() or 0))
    elif manager_scope is not None:
        total_clients = db.query(func.count(Client.id)).filter(
            Client.deleted_at.is_(None), Client.created_by.in_(manager_scope),
        ).scalar() or 0
        active_projects = db.query(func.count(Project.id)).filter(
            Project.deleted_at.is_(None), Project.status == "active", Project.owner_id.in_(manager_scope),
        ).scalar() or 0
        total_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
        tasks_todo = db.query(func.count(Task.id)).join(Project).filter(
            Task.status == "todo",
            Project.owner_id.in_(manager_scope),
            or_(Task.created_by.in_(manager_scope), Task.assignee_id.in_(manager_scope)),
        ).scalar() or 0
        tasks_in_progress = db.query(func.count(Task.id)).join(Project).filter(
            Task.status == "in_progress",
            Project.owner_id.in_(manager_scope),
            or_(Task.created_by.in_(manager_scope), Task.assignee_id.in_(manager_scope)),
        ).scalar() or 0
        tasks_done = db.query(func.count(Task.id)).join(Project).filter(
            Task.status == "done",
            Project.owner_id.in_(manager_scope),
            or_(Task.created_by.in_(manager_scope), Task.assignee_id.in_(manager_scope)),
        ).scalar() or 0
        revenue_total = db.query(func.coalesce(func.sum(Invoice.amount), 0)).join(Client).filter(
            Invoice.status == "paid", Client.created_by.in_(manager_scope),
        ).scalar()
        revenue_total = Decimal(str(revenue_total or 0))
        outstanding_total = db.query(func.coalesce(func.sum(Invoice.amount), 0)).join(Client).filter(
            Invoice.status.in_(["sent", "overdue"]), Client.created_by.in_(manager_scope),
        ).scalar()
        outstanding_total = Decimal(str(outstanding_total or 0))
        revenue_this_month = Decimal(str(db.query(func.coalesce(func.sum(Payment.amount), 0)).join(Invoice).join(Client).filter(
            Payment.paid_at >= month_start, Payment.paid_at <= month_end, Client.created_by.in_(manager_scope),
        ).scalar() or 0))
        expenses_this_month = Decimal(str(db.query(func.coalesce(func.sum(Expense.amount), 0)).join(Project).join(Client).filter(
            Expense.expense_date.isnot(None),
            Expense.expense_date >= month_start,
            Expense.expense_date <= month_end,
            Client.created_by.in_(manager_scope),
        ).scalar() or 0))
    else:
        # No reports (members): only tasks assigned to them, same as task list
        total_clients = 0
        active_projects = 0
        total_users = 0
        tasks_todo = db.query(func.count(Task.id)).filter(Task.status == "todo", Task.assignee_id == user.id).scalar() or 0
        tasks_in_progress = db.query(func.count(Task.id)).filter(Task.status == "in_progress", Task.assignee_id == user.id).scalar() or 0
        tasks_done = db.query(func.count(Task.id)).filter(Task.status == "done", Task.assignee_id == user.id).scalar() or 0
        revenue_total = Decimal("0")
        outstanding_total = Decimal("0")
        revenue_this_month = Decimal("0")
        expenses_this_month = Decimal("0")
    return AnalyticsOverview(
        total_clients=total_clients,
        active_projects=active_projects,
        total_users=total_users,
        tasks_todo=tasks_todo,
        tasks_in_progress=tasks_in_progress,
        tasks_done=tasks_done,
        revenue_total=revenue_total,
        outstanding_total=outstanding_total,
        revenue_this_month=revenue_this_month,
        expenses_this_month=expenses_this_month,
    )


def _member_dashboard_charts(db: Session, user_id):
    """Charts data for members: their leads (assigned_to=user_id) and task counts."""
    from decimal import Decimal

    # Leads assigned to this member: by status
    lead_status_rows = (
        db.query(Lead.status, func.count(Lead.id))
        .filter(Lead.assigned_to == user_id)
        .group_by(Lead.status)
        .all()
    )
    leads_by_status = [StatusCount(status=s or "unknown", count=c) for s, c in lead_status_rows]

    # Conversion rate: converted / (converted + lost + closed + dead)
    finished_statuses = ("converted", "lost", "closed", "dead")
    finished = (
        db.query(func.count(Lead.id))
        .filter(Lead.assigned_to == user_id, Lead.status.in_(finished_statuses))
        .scalar()
        or 0
    )
    converted = (
        db.query(func.count(Lead.id))
        .filter(Lead.assigned_to == user_id, Lead.status == "converted")
        .scalar()
        or 0
    )
    conversion_rate = (converted / finished) if finished else None

    # Conversion over time: last 12 months, count converted leads by month(converted_at)
    now = datetime.now(timezone.utc)
    # Start of current month, then go back 11 more for 12 months
    year, month = now.year, now.month
    month_counts = {}
    month_col = func.date_trunc("month", Lead.converted_at)
    conv_over_time_rows = (
        db.query(month_col, func.count(Lead.id))
        .filter(
            Lead.assigned_to == user_id,
            Lead.status == "converted",
            Lead.converted_at.isnot(None),
        )
        .group_by(month_col)
        .all()
    )
    for row in conv_over_time_rows:
        if row[0]:
            month_counts[row[0].strftime("%Y-%m")] = row[1]
    conversion_over_time = []
    for i in range(12):
        m = month - i
        y = year
        while m < 1:
            m += 12
            y -= 1
        month_str = f"{y}-{m:02d}"
        conversion_over_time.append(
            ConversionOverTimePoint(month=month_str, converted_count=month_counts.get(month_str, 0))
        )
    conversion_over_time.reverse()  # oldest first

    # Tasks by status (assigned to member)
    tasks_todo = db.query(func.count(Task.id)).filter(Task.assignee_id == user_id, Task.status == "todo").scalar() or 0
    tasks_ip = db.query(func.count(Task.id)).filter(Task.assignee_id == user_id, Task.status == "in_progress").scalar() or 0
    tasks_done = db.query(func.count(Task.id)).filter(Task.assignee_id == user_id, Task.status == "done").scalar() or 0
    tasks_by_status = [
        StatusCount(status="todo", count=tasks_todo),
        StatusCount(status="in_progress", count=tasks_ip),
        StatusCount(status="done", count=tasks_done),
    ]

    return {
        "conversion_rate": conversion_rate,
        "conversion_over_time": conversion_over_time,
        "leads_by_status": leads_by_status,
        "tasks_by_status": tasks_by_status,
    }


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    db: Session = Depends(get_db),
    user=Depends(require_any_permission("analytics:read", "dashboard:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    from decimal import Decimal

    today = date.today()
    month_start = today.replace(day=1)
    month_end = (month_start + timedelta(days=31)).replace(day=1) - timedelta(days=1)

    if "admin:all" in permissions:
        total_clients = db.query(func.count(Client.id)).filter(Client.deleted_at.is_(None)).scalar() or 0
        active_projects = db.query(func.count(Project.id)).filter(
            Project.deleted_at.is_(None), Project.status == "active",
        ).scalar() or 0
        total_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
        tasks_todo = db.query(func.count(Task.id)).filter(Task.status == "todo").scalar() or 0
        tasks_in_progress = db.query(func.count(Task.id)).filter(Task.status == "in_progress").scalar() or 0
        tasks_done = db.query(func.count(Task.id)).filter(Task.status == "done").scalar() or 0
        revenue_total = db.query(func.coalesce(func.sum(Invoice.amount), 0)).filter(Invoice.status == "paid").scalar()
        revenue_total = Decimal(str(revenue_total or 0))
        outstanding_total = db.query(func.coalesce(func.sum(Invoice.amount), 0)).filter(
            Invoice.status.in_(["sent", "overdue"])
        ).scalar()
        outstanding_total = Decimal(str(outstanding_total or 0))
        revenue_this_month = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
            Payment.paid_at >= month_start, Payment.paid_at <= month_end
        ).scalar()
        revenue_this_month = Decimal(str(revenue_this_month or 0))
        expenses_this_month = db.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
            Expense.expense_date.isnot(None),
            Expense.expense_date >= month_start,
            Expense.expense_date <= month_end,
        ).scalar()
        expenses_this_month = Decimal(str(expenses_this_month or 0))
        week_start = today - timedelta(days=6)
        leads_today = db.query(func.count(Lead.id)).filter(func.date(Lead.created_at) == today).scalar() or 0
        leads_this_week = db.query(func.count(Lead.id)).filter(
            func.date(Lead.created_at) >= week_start,
            func.date(Lead.created_at) <= today,
        ).scalar() or 0
        leads_this_month = db.query(func.count(Lead.id)).filter(
            func.date(Lead.created_at) >= month_start,
            func.date(Lead.created_at) <= month_end,
        ).scalar() or 0
        projects_by_stage_rows = (
            db.query(Project.pipeline_stage, func.count(Project.id))
            .filter(Project.deleted_at.is_(None))
            .group_by(Project.pipeline_stage)
            .all()
        )
        projects_by_stage = [StatusCount(status=s or "unknown", count=c) for s, c in projects_by_stage_rows]
        chart_data = {"conversion_rate": None, "conversion_over_time": [], "leads_by_status": [], "tasks_by_status": [
            StatusCount(status="todo", count=tasks_todo),
            StatusCount(status="in_progress", count=tasks_in_progress),
            StatusCount(status="done", count=tasks_done),
        ], "projects_by_stage": projects_by_stage}
    elif manager_scope is not None:
        total_clients = db.query(func.count(Client.id)).filter(
            Client.deleted_at.is_(None), Client.created_by.in_(manager_scope),
        ).scalar() or 0
        active_projects = db.query(func.count(Project.id)).filter(
            Project.deleted_at.is_(None), Project.status == "active", Project.owner_id.in_(manager_scope),
        ).scalar() or 0
        total_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
        tasks_todo = db.query(func.count(Task.id)).filter(
            Task.status == "todo",
            or_(Task.created_by.in_(manager_scope), Task.assignee_id.in_(manager_scope)),
        ).scalar() or 0
        tasks_in_progress = db.query(func.count(Task.id)).filter(
            Task.status == "in_progress",
            or_(Task.created_by.in_(manager_scope), Task.assignee_id.in_(manager_scope)),
        ).scalar() or 0
        tasks_done = db.query(func.count(Task.id)).filter(
            Task.status == "done",
            or_(Task.created_by.in_(manager_scope), Task.assignee_id.in_(manager_scope)),
        ).scalar() or 0
        revenue_total = db.query(func.coalesce(func.sum(Invoice.amount), 0)).join(Client).filter(
            Invoice.status == "paid", Client.created_by.in_(manager_scope),
        ).scalar()
        revenue_total = Decimal(str(revenue_total or 0))
        outstanding_total = db.query(func.coalesce(func.sum(Invoice.amount), 0)).join(Client).filter(
            Invoice.status.in_(["sent", "overdue"]), Client.created_by.in_(manager_scope),
        ).scalar()
        outstanding_total = Decimal(str(outstanding_total or 0))
        revenue_this_month = db.query(func.coalesce(func.sum(Payment.amount), 0)).join(Invoice).join(Client).filter(
            Payment.paid_at >= month_start, Payment.paid_at <= month_end, Client.created_by.in_(manager_scope),
        ).scalar()
        revenue_this_month = Decimal(str(revenue_this_month or 0))
        expenses_this_month = db.query(func.coalesce(func.sum(Expense.amount), 0)).join(Project).join(Client).filter(
            Expense.expense_date.isnot(None),
            Expense.expense_date >= month_start,
            Expense.expense_date <= month_end,
            Client.created_by.in_(manager_scope),
        ).scalar()
        expenses_this_month = Decimal(str(expenses_this_month or 0))
        projects_by_stage_rows = (
            db.query(Project.pipeline_stage, func.count(Project.id))
            .filter(Project.deleted_at.is_(None), Project.owner_id.in_(manager_scope))
            .group_by(Project.pipeline_stage)
            .all()
        )
        projects_by_stage = [StatusCount(status=s or "unknown", count=c) for s, c in projects_by_stage_rows]
        chart_data = {"conversion_rate": None, "conversion_over_time": [], "leads_by_status": [], "tasks_by_status": [
            StatusCount(status="todo", count=tasks_todo),
            StatusCount(status="in_progress", count=tasks_in_progress),
            StatusCount(status="done", count=tasks_done),
        ], "projects_by_stage": projects_by_stage}
    else:
        total_clients = 0
        active_projects = 0
        total_users = 0
        revenue_this_month = Decimal("0")
        expenses_this_month = Decimal("0")
        leads_today = 0
        leads_this_week = 0
        leads_this_month = 0
        tasks_todo = db.query(func.count(Task.id)).filter(Task.status == "todo", Task.assignee_id == user.id).scalar() or 0
        tasks_in_progress = db.query(func.count(Task.id)).filter(Task.status == "in_progress", Task.assignee_id == user.id).scalar() or 0
        tasks_done = db.query(func.count(Task.id)).filter(Task.status == "done", Task.assignee_id == user.id).scalar() or 0
        revenue_total = Decimal("0")
        outstanding_total = Decimal("0")
        chart_data = _member_dashboard_charts(db, user.id)

    return DashboardResponse(
        total_clients=total_clients,
        active_projects=active_projects,
        total_users=total_users,
        tasks_todo=tasks_todo,
        tasks_in_progress=tasks_in_progress,
        tasks_done=tasks_done,
        revenue_total=revenue_total,
        outstanding_total=outstanding_total,
        revenue_this_month=revenue_this_month,
        expenses_this_month=expenses_this_month,
        leads_today=leads_today,
        leads_this_week=leads_this_week,
        leads_this_month=leads_this_month,
        conversion_rate=chart_data["conversion_rate"],
        conversion_over_time=chart_data["conversion_over_time"],
        leads_by_status=chart_data["leads_by_status"],
        tasks_by_status=chart_data["tasks_by_status"],
        projects_by_stage=chart_data.get("projects_by_stage", []),
    )
