"""Seed permissions, roles, and default admin user. Run after migrations."""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import User, Role, Permission, UserRole, RolePermission
from app.core.security import get_password_hash

PERMISSIONS = [
    "admin:all",
    "leads:read", "leads:write",
    "clients:read", "clients:write",
    "projects:read", "projects:write",
    "tasks:read", "tasks:write",
    "meetings:read", "meetings:write",
    "finance:read", "finance:write",
    "analytics:read",
]

# Role name -> list of permission codes (admin gets all via code below)
ROLE_PERMISSIONS = {
    "admin": None,  # all permissions
    "manager": [
        "leads:read", "leads:write",
        "clients:read", "clients:write",
        "projects:read", "projects:write",
        "tasks:read", "tasks:write",
        "meetings:read", "meetings:write",
        "finance:read", "finance:write",
        "analytics:read",
    ],
    "member": [
        "leads:read", "leads:write",
        "clients:read", "clients:write",
        "projects:read", "projects:write",
        "tasks:read", "tasks:write",
        "meetings:read", "meetings:write",
        "finance:read", "finance:write",
        "analytics:read",
    ],
    "viewer": [
        "leads:read",
        "clients:read", "projects:read", "tasks:read",
        "meetings:read", "finance:read", "analytics:read",
    ],
}


def seed():
    db = SessionLocal()
    try:
        # Permissions
        for code in PERMISSIONS:
            if db.query(Permission).filter(Permission.code == code).first():
                continue
            db.add(Permission(id=uuid.uuid4(), code=code, description=code))
        db.commit()

        all_permissions = {p.code: p for p in db.query(Permission).all()}

        # Roles with permissions
        for role_name, perm_codes in ROLE_PERMISSIONS.items():
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                role = Role(
                    id=uuid.uuid4(),
                    name=role_name,
                    description={
                        "admin": "Administrator",
                        "manager": "Manager: full access except admin",
                        "member": "Member: same as manager",
                        "viewer": "Viewer: read-only",
                    }[role_name],
                )
                db.add(role)
                db.commit()
                db.refresh(role)
            # Assign permissions (skip if role already has any)
            if db.query(RolePermission).filter(RolePermission.role_id == role.id).first():
                continue
            codes = perm_codes if perm_codes else list(all_permissions.keys())
            for code in codes:
                perm = all_permissions.get(code)
                if perm:
                    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
            db.commit()

        # Default admin user if not exists
        if db.query(User).filter(User.email == "admin@example.com").first():
            print("Admin user already exists.")
            return
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        admin_user = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            password_hash=get_password_hash("admin123"),
            full_name="Admin",
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        db.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))
        db.commit()
        print("Seeded: permissions, roles (admin, manager, member, viewer), admin@example.com / admin123")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
