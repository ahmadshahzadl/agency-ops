from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID


class LoginRequest(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: int
    type: str


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    is_active: bool
    permissions: list[str] = []
    roles: list[str] = []  # role names e.g. ["sales"], ["manager", "sales"]
    can_manage_tasks: bool = False  # true if admin or has direct reports (can create/assign/delete tasks)
    can_manage_leads: bool = False  # true if admin or manager (can create client/project from lead, edit converted/closed)

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None
