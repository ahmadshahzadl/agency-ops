"""Admin-only: list roles, create role with permissions."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Role as RoleModel, RolePermission, Permission
from app.schemas.role import RoleCreate, RoleUpdate, RoleResponse, PermissionResponse
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/roles", tags=["roles"])


def _role_to_response(role: RoleModel) -> RoleResponse:
    permission_ids = [p.id for p in role.permissions]
    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        permission_ids=permission_ids,
    )


@router.get("/permissions", response_model=list[PermissionResponse])
def list_permissions(
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    return db.query(Permission).order_by(Permission.code).all()


@router.get("", response_model=list[RoleResponse])
def list_roles(
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    return [_role_to_response(r) for r in db.query(RoleModel).all()]


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(
    data: RoleCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    if db.query(RoleModel).filter(RoleModel.name == data.name).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role name already exists")
    role = RoleModel(name=data.name, description=data.description)
    db.add(role)
    db.flush()
    for perm_id in data.permission_ids or []:
        db.add(RolePermission(role_id=role.id, permission_id=perm_id))
    db.commit()
    db.refresh(role)
    return _role_to_response(role)


@router.get("/{role_id}", response_model=RoleResponse)
def get_role(
    role_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    return _role_to_response(role)


@router.patch("/{role_id}", response_model=RoleResponse)
def update_role(
    role_id: UUID,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if data.name is not None:
        role.name = data.name
    if data.description is not None:
        role.description = data.description
    if data.permission_ids is not None:
        db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
        for perm_id in data.permission_ids:
            db.add(RolePermission(role_id=role.id, permission_id=perm_id))
    db.commit()
    db.refresh(role)
    return _role_to_response(role)
