from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    permission_ids: list[UUID] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permission_ids: Optional[list[UUID]] = None


class RoleResponse(RoleBase):
    id: UUID
    permission_ids: list[UUID] = []

    class Config:
        from_attributes = True


class PermissionResponse(BaseModel):
    id: UUID
    code: str
    description: Optional[str] = None

    class Config:
        from_attributes = True
