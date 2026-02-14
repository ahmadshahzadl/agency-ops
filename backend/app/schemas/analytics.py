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
