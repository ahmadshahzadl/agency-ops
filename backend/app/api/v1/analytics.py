from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.database import get_db
from app.models import Client, Project, Task, Invoice, Payment, Expense, Lead, User, Quote, TimeEntry
from app.schemas.analytics import (
    AnalyticsOverview,
    DashboardResponse,
    ConversionOverTimePoint,
    StatusCount,
)
from sqlalchemy import or_
from app.api.deps import get_current_user, require_staff, require_any_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids

router = APIRouter(prefix="/analytics", tags=["analytics"])

TASK_STATUSES = ("todo", "in_progress", "review", "qa_failed", "done")


def _task_status_counts(db: Session, filters: list, join_project: bool = False) -> dict[str, int]:
    """Counts for every pipeline status (review/qa_failed included) under the given scope filters."""
    q = db.query(Task.status, func.count(Task.id))
    if join_project:
        q = q.join(Project)
    rows = q.filter(*filters).group_by(Task.status).all()
    counts = {s: 0 for s in TASK_STATUSES}
    for s, c in rows:
        if s in counts:
            counts[s] = c
    return counts


def _tasks_by_status_chart(counts: dict[str, int]) -> list[StatusCount]:
    return [StatusCount(status=s, count=counts[s]) for s in TASK_STATUSES]


def _quote_metrics(db: Session, permissions: set, manager_scope, user):
    """(pipeline_value, win_rate, open_count) scoped like the quotes list. None-gated on quotes:read."""
    if "admin:all" not in permissions and "quotes:read" not in permissions:
        return None, None, 0
    q = db.query(Quote.status, func.count(Quote.id), func.coalesce(func.sum(Quote.total), 0))
    if "admin:all" not in permissions:
        if manager_scope is not None:
            q = q.filter(Quote.created_by.in_(manager_scope))
        else:
            q = q.filter(Quote.created_by == user.id)
    by = {s: (c, Decimal(str(t or 0))) for s, c, t in q.group_by(Quote.status).all()}
    open_count = by.get("draft", (0, None))[0] + by.get("sent", (0, None))[0]
    pipeline = by.get("draft", (0, Decimal("0")))[1] + by.get("sent", (0, Decimal("0")))[1]
    accepted = by.get("accepted", (0, None))[0]
    rejected = by.get("rejected", (0, None))[0]
    win_rate = (accepted / (accepted + rejected)) if (accepted + rejected) else None
    return pipeline, win_rate, open_count


def _hours_metrics(db: Session, permissions: set, manager_scope, user, month_start, month_end):
    """(hours_this_month, billable_hours_this_month, unbilled_value) scoped like the timesheet.
    unbilled_value is finance-gated (None without finance:read)."""
    base = db.query(TimeEntry).options(joinedload(TimeEntry.project)).join(
        Project, TimeEntry.project_id == Project.id
    ).filter(Project.deleted_at.is_(None))
    if "admin:all" not in permissions:
        if manager_scope is not None:
            base = base.filter(TimeEntry.user_id.in_(manager_scope))
        else:
            base = base.filter(TimeEntry.user_id == user.id)
    month_entries = base.filter(TimeEntry.work_date >= month_start, TimeEntry.work_date <= month_end).all()
    hours = sum((e.hours for e in month_entries), Decimal("0"))
    billable = sum((e.hours for e in month_entries if e.billable), Decimal("0"))
    if "admin:all" not in permissions and "finance:read" not in permissions:
        return hours, billable, None
    unbilled_value = Decimal("0")
    for e in base.filter(TimeEntry.billable == True, TimeEntry.invoice_id.is_(None)).all():
        rate = e.hourly_rate if e.hourly_rate is not None else (e.project.hourly_rate if e.project else None)
        if rate is not None:
            unbilled_value += e.hours * rate
    return hours, billable, unbilled_value


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
        task_counts = _task_status_counts(db, [])
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
        task_counts = _task_status_counts(db, [
            Project.owner_id.in_(manager_scope),
            or_(Task.created_by.in_(manager_scope), Task.assignee_id.in_(manager_scope)),
        ], join_project=True)
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
        task_counts = _task_status_counts(db, [Task.assignee_id == user.id])
        revenue_total = Decimal("0")
        outstanding_total = Decimal("0")
        revenue_this_month = Decimal("0")
        expenses_this_month = Decimal("0")
    # Finance figures require finance:read, not just having direct reports
    if "admin:all" not in permissions and "finance:read" not in permissions:
        revenue_total = Decimal("0")
        outstanding_total = Decimal("0")
        revenue_this_month = Decimal("0")
        expenses_this_month = Decimal("0")
    # Expenses are stricter: expenses:read only (managers have finance:read but not expenses)
    if "admin:all" not in permissions and "expenses:read" not in permissions:
        expenses_this_month = None
    quote_pipeline, quote_win_rate, quotes_open = _quote_metrics(db, permissions, manager_scope, user)
    hours_month, billable_month, unbilled_value = _hours_metrics(db, permissions, manager_scope, user, month_start, month_end)
    return AnalyticsOverview(
        total_clients=total_clients,
        active_projects=active_projects,
        total_users=total_users,
        tasks_todo=task_counts["todo"],
        tasks_in_progress=task_counts["in_progress"],
        tasks_review=task_counts["review"],
        tasks_qa_failed=task_counts["qa_failed"],
        tasks_done=task_counts["done"],
        revenue_total=revenue_total,
        outstanding_total=outstanding_total,
        revenue_this_month=revenue_this_month,
        expenses_this_month=expenses_this_month,
        hours_this_month=hours_month,
        billable_hours_this_month=billable_month,
        unbilled_value=unbilled_value,
        quote_pipeline_value=quote_pipeline,
        quote_win_rate=quote_win_rate,
        quotes_open=quotes_open,
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

    # Tasks by status (assigned to member), all pipeline states included
    tasks_by_status = _tasks_by_status_chart(_task_status_counts(db, [Task.assignee_id == user_id]))

    return {
        "conversion_rate": conversion_rate,
        "conversion_over_time": conversion_over_time,
        "leads_by_status": leads_by_status,
        "tasks_by_status": tasks_by_status,
    }


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(
    db: Session = Depends(get_db),
    user=Depends(require_staff),
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
        task_counts = _task_status_counts(db, [])
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
        chart_data = {"conversion_rate": None, "conversion_over_time": [], "leads_by_status": [],
                      "tasks_by_status": _tasks_by_status_chart(task_counts), "projects_by_stage": projects_by_stage}
    elif manager_scope is not None:
        total_clients = db.query(func.count(Client.id)).filter(
            Client.deleted_at.is_(None), Client.created_by.in_(manager_scope),
        ).scalar() or 0
        active_projects = db.query(func.count(Project.id)).filter(
            Project.deleted_at.is_(None), Project.status == "active", Project.owner_id.in_(manager_scope),
        ).scalar() or 0
        total_users = db.query(func.count(User.id)).filter(User.is_active.is_(True)).scalar() or 0
        task_counts = _task_status_counts(db, [
            or_(Task.created_by.in_(manager_scope), Task.assignee_id.in_(manager_scope)),
        ])
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
        week_start = today - timedelta(days=6)
        leads_today = db.query(func.count(Lead.id)).filter(
            Lead.assigned_to.in_(manager_scope), func.date(Lead.created_at) == today,
        ).scalar() or 0
        leads_this_week = db.query(func.count(Lead.id)).filter(
            Lead.assigned_to.in_(manager_scope),
            func.date(Lead.created_at) >= week_start,
            func.date(Lead.created_at) <= today,
        ).scalar() or 0
        leads_this_month = db.query(func.count(Lead.id)).filter(
            Lead.assigned_to.in_(manager_scope),
            func.date(Lead.created_at) >= month_start,
            func.date(Lead.created_at) <= month_end,
        ).scalar() or 0
        chart_data = {"conversion_rate": None, "conversion_over_time": [], "leads_by_status": [],
                      "tasks_by_status": _tasks_by_status_chart(task_counts), "projects_by_stage": projects_by_stage}
    else:
        total_clients = 0
        active_projects = 0
        total_users = 0
        revenue_this_month = Decimal("0")
        expenses_this_month = Decimal("0")
        leads_today = 0
        leads_this_week = 0
        leads_this_month = 0
        task_counts = _task_status_counts(db, [Task.assignee_id == user.id])
        revenue_total = Decimal("0")
        outstanding_total = Decimal("0")
        chart_data = _member_dashboard_charts(db, user.id)

    # Finance figures require finance:read, not just having direct reports
    if "admin:all" not in permissions and "finance:read" not in permissions:
        revenue_total = Decimal("0")
        outstanding_total = Decimal("0")
        revenue_this_month = Decimal("0")
        expenses_this_month = Decimal("0")
    # Expenses are stricter: expenses:read only (managers have finance:read but not expenses)
    if "admin:all" not in permissions and "expenses:read" not in permissions:
        expenses_this_month = None
    quote_pipeline, quote_win_rate, quotes_open = _quote_metrics(db, permissions, manager_scope, user)
    hours_month, billable_month, unbilled_value = _hours_metrics(db, permissions, manager_scope, user, month_start, month_end)
    return DashboardResponse(
        total_clients=total_clients,
        active_projects=active_projects,
        total_users=total_users,
        tasks_todo=task_counts["todo"],
        tasks_in_progress=task_counts["in_progress"],
        tasks_review=task_counts["review"],
        tasks_qa_failed=task_counts["qa_failed"],
        tasks_done=task_counts["done"],
        revenue_total=revenue_total,
        outstanding_total=outstanding_total,
        revenue_this_month=revenue_this_month,
        expenses_this_month=expenses_this_month,
        hours_this_month=hours_month,
        billable_hours_this_month=billable_month,
        unbilled_value=unbilled_value,
        quote_pipeline_value=quote_pipeline,
        quote_win_rate=quote_win_rate,
        quotes_open=quotes_open,
        leads_today=leads_today,
        leads_this_week=leads_this_week,
        leads_this_month=leads_this_month,
        conversion_rate=chart_data["conversion_rate"],
        conversion_over_time=chart_data["conversion_over_time"],
        leads_by_status=chart_data["leads_by_status"],
        tasks_by_status=chart_data["tasks_by_status"],
        projects_by_stage=chart_data.get("projects_by_stage", []),
    )
