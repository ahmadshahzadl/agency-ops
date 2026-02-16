from pydantic import BaseModel
from typing import Optional
from decimal import Decimal


class AnalyticsOverview(BaseModel):
    total_clients: int
    active_projects: int
    tasks_todo: int
    tasks_in_progress: int
    tasks_done: int
    revenue_total: Optional[Decimal] = None
    outstanding_total: Optional[Decimal] = None


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
    tasks_todo: int
    tasks_in_progress: int
    tasks_done: int
    revenue_total: Optional[Decimal] = None
    outstanding_total: Optional[Decimal] = None
    conversion_rate: Optional[float] = None  # 0..1 for members (their leads)
    conversion_over_time: list[ConversionOverTimePoint] = []
    leads_by_status: list[StatusCount] = []
    tasks_by_status: list[StatusCount] = []  # todo, in_progress, done
