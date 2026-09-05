from pydantic import BaseModel
from typing import Optional
from decimal import Decimal


class AnalyticsOverview(BaseModel):
    total_clients: int
    active_projects: int
    total_users: int
    tasks_todo: int
    tasks_in_progress: int
    tasks_review: int = 0
    tasks_qa_failed: int = 0
    tasks_done: int
    revenue_total: Optional[Decimal] = None
    outstanding_total: Optional[Decimal] = None
    revenue_this_month: Optional[Decimal] = None
    expenses_this_month: Optional[Decimal] = None
    expenses_by_currency: Optional[dict[str, Decimal]] = None  # e.g. {"PKR": 150000, "USD": 200}
    hours_this_month: Decimal = Decimal("0")
    billable_hours_this_month: Decimal = Decimal("0")
    unbilled_value: Optional[Decimal] = None  # finance-gated
    # Role-focused: populated for QA-capable users / when relevant
    qa_review_queue: Optional[int] = None
    qa_failed_awaiting: Optional[int] = None
    client_reported_open: Optional[int] = None
    quote_pipeline_value: Optional[Decimal] = None  # draft + sent quote totals (quotes-gated)
    quote_win_rate: Optional[float] = None  # accepted / (accepted + rejected)
    quotes_open: int = 0


class ConversionOverTimePoint(BaseModel):
    month: str  # "YYYY-MM"
    converted_count: int


class StatusCount(BaseModel):
    status: str
    count: int


class DashboardResponse(BaseModel):
    """Dashboard data: overview + chart data. Member-scoped when user is not admin/manager."""
    total_clients: int
    active_projects: int
    total_users: int
    tasks_todo: int
    tasks_in_progress: int
    tasks_review: int = 0
    tasks_qa_failed: int = 0
    tasks_done: int
    revenue_total: Optional[Decimal] = None
    outstanding_total: Optional[Decimal] = None
    revenue_this_month: Optional[Decimal] = None
    expenses_this_month: Optional[Decimal] = None
    expenses_by_currency: Optional[dict[str, Decimal]] = None  # e.g. {"PKR": 150000, "USD": 200}
    hours_this_month: Decimal = Decimal("0")
    billable_hours_this_month: Decimal = Decimal("0")
    unbilled_value: Optional[Decimal] = None
    # Role-focused: populated for QA-capable users / when relevant
    qa_review_queue: Optional[int] = None
    qa_failed_awaiting: Optional[int] = None
    client_reported_open: Optional[int] = None
    quote_pipeline_value: Optional[Decimal] = None
    quote_win_rate: Optional[float] = None
    quotes_open: int = 0
    leads_today: int = 0
    leads_this_week: int = 0
    leads_this_month: int = 0
    conversion_rate: Optional[float] = None  # 0..1 for members (their leads)
    conversion_over_time: list[ConversionOverTimePoint] = []
    leads_by_status: list[StatusCount] = []
    tasks_by_status: list[StatusCount] = []  # todo, in_progress, done
    projects_by_stage: list[StatusCount] = []  # pipeline_stage counts; only for admin/manager
