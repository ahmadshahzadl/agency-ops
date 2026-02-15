from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class TeamBase(BaseModel):
    name: str
    description: Optional[str] = None
    team_type: Optional[str] = None  # management, product_pm, frontend, backend, design, qa, devops, sales_marketing, support, etc.


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    team_type: Optional[str] = None


class TeamResponse(TeamBase):
    id: UUID

    class Config:
        from_attributes = True


class TeamWithMembersResponse(TeamResponse):
    team_type: Optional[str] = None
    user_ids: list[UUID] = []
