from pydantic import BaseModel
from typing import Optional
from decimal import Decimal


class AnalyticsOverview(BaseModel):
    total_clients: int
    active_projects: int
    total_users: int
    tasks_todo: int
    tasks_in_progress: int
    tasks_done: int
    revenue_total: Optional[Decimal] = None
    outstanding_total: Optional[Decimal] = None
    revenue_this_month: Optional[Decimal] = None
    expenses_this_month: Optional[Decimal] = None


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
    tasks_done: int
    revenue_total: Optional[Decimal] = None
    outstanding_total: Optional[Decimal] = None
    revenue_this_month: Optional[Decimal] = None
    expenses_this_month: Optional[Decimal] = None
    leads_today: int = 0
    leads_this_week: int = 0
    leads_this_month: int = 0
    conversion_rate: Optional[float] = None  # 0..1 for members (their leads)
    conversion_over_time: list[ConversionOverTimePoint] = []
    leads_by_status: list[StatusCount] = []
    tasks_by_status: list[StatusCount] = []  # todo, in_progress, done
    projects_by_stage: list[StatusCount] = []  # pipeline_stage counts; only for admin/manager
