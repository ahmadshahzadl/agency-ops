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
    "dashboard:read",
    "leads:read", "leads:write",
    "clients:read", "clients:write",
    "projects:read", "projects:write",
    "tasks:read", "tasks:write",
    "meetings:read", "meetings:write",
    "finance:read", "finance:write",
    "expenses:read", "expenses:write",
    "analytics:read",
    "team_activity:read",
    "notes:read", "notes:write",
    "announcements:read", "announcements:write",
]

# Three primary roles per docs/roles-permissions-flow.md: Admin, Manager, Employee
# "member" kept with same as employee for backward compatibility.
ROLE_PERMISSIONS = {
    "admin": None,  # all permissions
    "manager": [
        "dashboard:read",
        "leads:read", "leads:write",
        "clients:read", "clients:write",
        "projects:read", "projects:write",
        "tasks:read", "tasks:write",
        "meetings:read", "meetings:write",
        "finance:read",
        "analytics:read",
        "team_activity:read",
        "notes:read", "notes:write",
        "announcements:read",
    ],
    "employee": [
        "dashboard:read",
        "leads:read",
        "projects:read",
        "tasks:read", "tasks:write",
        "meetings:read",
        "notes:read", "notes:write",
        "announcements:read",
    ],
    "member": [
        "dashboard:read",
        "leads:read",
        "projects:read",
        "tasks:read", "tasks:write",
        "meetings:read",
        "notes:read", "notes:write",
        "announcements:read",
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
                        "admin": "Administrator: full system access",
                        "manager": "Manager: team-scoped access; view team invoices; no expenses, no user/team/role management",
                        "employee": "Employee: assigned tasks/projects/meetings only; no clients, finance, reports, or team activity",
                    "member": "Member: same as Employee (backward compatibility)",
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
        print("Seeded: permissions, roles (admin, manager, employee, member), admin@example.com / admin123")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
