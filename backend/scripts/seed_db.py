"""Seed permissions, roles, and default admin user. Run after migrations.

Admin credentials come from ADMIN_EMAIL / ADMIN_PASSWORD env vars. If
ADMIN_PASSWORD is unset, a random password is generated and printed once.
"""
import os
import secrets
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
    "tasks:read", "tasks:write", "tasks:qa_approve",
    "meetings:read", "meetings:write",
    "finance:read", "finance:write",
    "expenses:read", "expenses:write",
    "analytics:read",
    "team_activity:read",
    "notes:read", "notes:write",
    "announcements:read", "announcements:write",
    "attachments:read", "attachments:write",
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
        "attachments:read", "attachments:write",
        "announcements:read",
    ],
    "employee": [
        "dashboard:read",
        "leads:read",
        "projects:read",
        "tasks:read", "tasks:write",
        "meetings:read",
        "notes:read", "notes:write",
        "attachments:read", "attachments:write",
        "announcements:read",
    ],
    "member": [
        "dashboard:read",
        "leads:read",
        "projects:read",
        "tasks:read", "tasks:write",
        "meetings:read",
        "notes:read", "notes:write",
        "attachments:read", "attachments:write",
        "announcements:read",
    ],
    "qa": [
        "dashboard:read",
        "projects:read",
        "tasks:read", "tasks:write", "tasks:qa_approve",
        "meetings:read",
        "notes:read", "notes:write",
        "attachments:read", "attachments:write",
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
                        "qa": "QA: employee access plus approving/failing tasks in review",
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
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@example.com").strip().lower()
        if db.query(User).filter(User.email == admin_email).first():
            print(f"Admin user {admin_email} already exists. Permissions and roles are up to date.")
            return
        admin_password = os.environ.get("ADMIN_PASSWORD")
        generated = False
        if not admin_password:
            admin_password = secrets.token_urlsafe(12)
            generated = True
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        admin_user = User(
            id=uuid.uuid4(),
            email=admin_email,
            password_hash=get_password_hash(admin_password),
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
        print(f"Seeded: permissions, roles (admin, manager, employee, member), admin user {admin_email}")
        if generated:
            print(f"Generated admin password (save it now, it will not be shown again): {admin_password}")
        print("Change the admin password after first login.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
