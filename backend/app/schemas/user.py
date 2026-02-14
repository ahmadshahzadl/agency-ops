from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID


class UserCreateAdmin(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    is_active: bool = True
    role_ids: list[UUID] = []
    team_ids: list[UUID] = []


class UserUpdateAdmin(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[list[UUID]] = None
    team_ids: Optional[list[UUID]] = None


class UserListResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    is_active: bool
    role_ids: list[UUID] = []
    team_ids: list[UUID] = []

    class Config:
        from_attributes = True
