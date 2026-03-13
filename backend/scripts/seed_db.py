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
    "dashboard:read",  # dashboard page (overview); sales team has this but not analytics:read
    "leads:read", "leads:write",
    "clients:read", "clients:write",
    "projects:read", "projects:write",
    "tasks:read", "tasks:write",
    "meetings:read", "meetings:write",
    "finance:read", "finance:write",
    "analytics:read",
    "team_activity:read",  # managers see their reports' activity and progress
    "notes:read", "notes:write",
]

# Role name -> list of permission codes (admin gets all via code below)
ROLE_PERMISSIONS = {
    "admin": None,  # all permissions
    "manager": [
        "dashboard:read",
        "leads:read", "leads:write",
        "clients:read", "clients:write",
        "projects:read", "projects:write",
        "tasks:read", "tasks:write",
        "meetings:read", "meetings:write",
        "finance:read", "finance:write",
        "analytics:read",
        "team_activity:read",
        "notes:read", "notes:write",
    ],
    "member": [
        "dashboard:read",
        "leads:read", "leads:write",
        "clients:read", "clients:write",
        "projects:read", "projects:write",
        "tasks:read", "tasks:write",
        "meetings:read", "meetings:write",
        "finance:read", "finance:write",
        "analytics:read",
        "notes:read", "notes:write",
    ],
    "viewer": [
        "dashboard:read",
        "leads:read",
        "clients:read", "projects:read", "tasks:read",
        "meetings:read", "finance:read", "analytics:read",
        "notes:read",
    ],
    "sales": [
        "dashboard:read",
        "leads:read", "leads:write",
        "projects:read",
        "meetings:read", "meetings:write",
        "tasks:read", "tasks:write",
        "notes:read", "notes:write",
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

        # Roles with permissions (add any missing permissions to existing roles)
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
                        "sales": "Sales: leads, meetings, tasks only; own data for members, team for lead managers",
                    }.get(role_name, role_name),
                )
                db.add(role)
                db.commit()
                db.refresh(role)
            codes = perm_codes if perm_codes else list(all_permissions.keys())
            existing = {rp.permission_id for rp in db.query(RolePermission).filter(RolePermission.role_id == role.id).all()}
            for code in codes:
                perm = all_permissions.get(code)
                if perm and perm.id not in existing:
                    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
                    existing.add(perm.id)
            db.commit()

        # Default admin user if not exists
        if db.query(User).filter(User.email == "admin@example.com").first():
            print("Admin user already exists. Permissions and roles are up to date.")
            return
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        admin_user = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            password_hash=get_password_hash("admin123"),
            full_name="Admin",
            phone="+1-555-0000",
            job_title="Administrator",
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        db.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))
        db.commit()
        print("Seeded: permissions, roles (admin, manager, member, viewer, sales), admin@example.com / admin123")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
