from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID


class UserCreateAdmin(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    is_active: bool = True
    manager_id: Optional[UUID] = None
    client_id: Optional[UUID] = None  # set to create a client-portal user
    role_ids: list[UUID] = []
    team_ids: list[UUID] = []


class UserUpdateAdmin(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    is_active: Optional[bool] = None
    manager_id: Optional[UUID] = None
    client_id: Optional[UUID] = None
    role_ids: Optional[list[UUID]] = None
    team_ids: Optional[list[UUID]] = None


class UserListResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    is_active: bool
    manager_id: Optional[UUID] = None
    client_id: Optional[UUID] = None  # set to create a client-portal user
    role_ids: list[UUID] = []
    team_ids: list[UUID] = []

    class Config:
        from_attributes = True
