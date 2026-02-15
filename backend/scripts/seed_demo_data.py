"""Seed demo data: all team types, users, leads→client→project flow, clients, projects, tasks, meetings, finance.
Run after migrations and seed_db.py."""
import os
import sys
import uuid
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import (
    User,
    Role,
    UserRole,
    Team,
    TeamMember,
    Lead,
    Client,
    Project,
    Task,
    Meeting,
    MeetingAttendee,
    Invoice,
    Payment,
    Expense,
)
from app.core.security import get_password_hash

# All 9 team types from the spec (we create 12 teams: management, product_pm, frontend, backend, fullstack, mobile, design, qa, devops, data_ai, sales_marketing, support)
TEAM_TYPES = [
    ("Management / Leadership", "management", "Oversees company, strategic alignment, goals and roadmap"),
    ("Product / Project Management", "product_pm", "Plan, coordinate, track projects; scope, milestones, timelines"),
    ("Frontend", "frontend", "UI/UX of applications; React, Vue, Angular, Flutter"),
    ("Backend", "backend", "Server-side logic, APIs, databases; Node, Django, Python, Java, Go"),
    ("Full-Stack", "fullstack", "Frontend + backend end-to-end features"),
    ("Mobile Development", "mobile", "Native or cross-platform apps; Flutter, React Native, Swift, Kotlin"),
    ("UI/UX Design", "design", "Wireframes, prototypes, visual branding, usability"),
    ("QA / Testing", "qa", "Manual and automated testing, performance, security"),
    ("DevOps / Infrastructure", "devops", "CI/CD, cloud, monitoring, deployments"),
    ("Data / AI / Analytics", "data_ai", "Data modeling, ML/AI, dashboards, reporting"),
    ("Sales, Marketing & Client Relations", "sales_marketing", "Lead gen, client relationships, marketing"),
    ("Support / Maintenance", "support", "Post-launch support, bugs, customer tickets"),
]


def _get_or_create_user(db, email: str, full_name: str, password: str, role_name: str) -> User:
    u = db.query(User).filter(User.email == email).first()
    if u:
        return u
    role = db.query(Role).filter(Role.name == role_name).first()
    if not role:
        raise RuntimeError(f"Role {role_name} not found. Run seed_db.py first.")
    u = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=get_password_hash(password),
        full_name=full_name,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    db.add(UserRole(user_id=u.id, role_id=role.id))
    db.commit()
    return u


def seed_demo():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@example.com").first()
        if not admin:
            print("Run seed_db.py first to create admin user.")
            return

        # Skip if demo data already present
        if db.query(Client).first():
            print("Demo data already exists. Skipping.")
            return

        # --- All team types (1–9 from spec) ---
        teams_by_type = {}
        for name, team_type, desc in TEAM_TYPES:
            t = Team(name=name, description=desc, team_type=team_type)
            db.add(t)
            db.flush()
            teams_by_type[team_type] = t
        db.commit()
        for t in teams_by_type.values():
            db.refresh(t)

        team_pm = teams_by_type["product_pm"]
        team_sales = teams_by_type["sales_marketing"]
        team_frontend = teams_by_type["frontend"]
        team_backend = teams_by_type["backend"]
        team_design = teams_by_type["design"]
        team_qa = teams_by_type["qa"]
        team_devops = teams_by_type["devops"]
        team_fullstack = teams_by_type["fullstack"]
        team_management = teams_by_type["management"]

        # --- Users and team members (admin→management; manager→product_pm + sales; member→frontend; viewer→qa) ---
        manager_user = _get_or_create_user(db, "manager@example.com", "Demo Manager", "demo123", "manager")
        member_user = _get_or_create_user(db, "member@example.com", "Demo Member", "demo123", "member")
        viewer_user = _get_or_create_user(db, "viewer@example.com", "Demo Viewer", "demo123", "viewer")

        db.add(TeamMember(team_id=team_management.id, user_id=admin.id))
        db.add_all([
            TeamMember(team_id=team_pm.id, user_id=admin.id),
            TeamMember(team_id=team_pm.id, user_id=manager_user.id),
            TeamMember(team_id=team_sales.id, user_id=manager_user.id),
            TeamMember(team_id=team_frontend.id, user_id=member_user.id),
            TeamMember(team_id=team_qa.id, user_id=viewer_user.id),
        ])
        db.commit()

        # --- Leads (Sales team generates leads) ---
        lead1 = Lead(
            company_name="Future Tech Inc",
            contact_name="Jane Doe",
            contact_email="jane@futuretech.example",
            contact_phone="+1-555-1000",
            source="website",
            status="qualified",
            notes="Interested in custom dashboard.",
            assigned_team_id=team_sales.id,
            created_by=manager_user.id,
        )
        lead2 = Lead(
            company_name="Startup Alpha",
            contact_name="John Smith",
            contact_email="john@startupalpha.example",
            source="referral",
            status="contacted",
            assigned_team_id=team_sales.id,
            created_by=manager_user.id,
        )
        db.add_all([lead1, lead2])
        db.commit()
        db.refresh(lead1)
        db.refresh(lead2)

        # --- Clients: 3 under Product/PM (delivery), 1 from Sales, 1 from converted lead ---
        c1 = Client(
            name="Acme Corp",
            contact_email="contact@acme.example",
            contact_phone="+1-555-0100",
            address="123 Main St, City",
            team_id=team_pm.id,
            created_by=admin.id,
        )
        c2 = Client(
            name="Beta Industries",
            contact_email="hello@beta.example",
            contact_phone="+1-555-0200",
            team_id=team_pm.id,
            created_by=admin.id,
        )
        c3 = Client(
            name="Gamma LLC",
            contact_email="info@gamma.example",
            team_id=team_pm.id,
            created_by=admin.id,
        )
        c4 = Client(
            name="Sales Lead Co",
            contact_email="sales@sl.example",
            contact_phone="+1-555-0300",
            team_id=team_sales.id,
            created_by=admin.id,
        )
        db.add_all([c1, c2, c3, c4])
        db.commit()
        for c in [c1, c2, c3, c4]:
            db.refresh(c)

        # Convert lead1 → client c5 + project p4 (flow: Sales lead → Client → Project assigned to PM)
        c5 = Client(
            name=lead1.company_name,
            contact_email=lead1.contact_email,
            contact_phone=lead1.contact_phone,
            team_id=team_sales.id,
            created_by=manager_user.id,
        )
        db.add(c5)
        db.commit()
        db.refresh(c5)
        lead1.converted_to_client_id = c5.id
        lead1.converted_at = datetime.now(timezone.utc)
        lead1.status = "converted"
        db.commit()

        # --- Projects (with pipeline_stage and assigned_team_id for flow) ---
        today = date.today()
        p1 = Project(
            client_id=c1.id,
            name="Website Redesign",
            description="Full website overhaul",
            status="active",
            pipeline_stage="development",
            assigned_team_id=team_frontend.id,
            start_date=today - timedelta(days=60),
            end_date=today + timedelta(days=30),
            owner_id=admin.id,
        )
        p2 = Project(
            client_id=c1.id,
            name="Mobile App",
            description="iOS and Android app",
            status="active",
            pipeline_stage="development",
            assigned_team_id=team_backend.id,
            start_date=today - timedelta(days=30),
            owner_id=admin.id,
        )
        p3 = Project(
            client_id=c2.id,
            name="API Integration",
            status="draft",
            pipeline_stage="scoping",
            assigned_team_id=team_pm.id,
            owner_id=admin.id,
        )
        p4 = Project(
            client_id=c4.id,
            name="Sales Portal",
            description="Customer-facing sales portal",
            status="active",
            pipeline_stage="discovery",
            assigned_team_id=team_pm.id,
            start_date=today - timedelta(days=14),
            owner_id=manager_user.id,
        )
        p5 = Project(
            client_id=c5.id,
            name="Custom Dashboard",
            description="Converted from lead: Future Tech Inc",
            status="draft",
            pipeline_stage="discovery",
            assigned_team_id=team_pm.id,
            start_date=today,
            owner_id=manager_user.id,
        )
        db.add_all([p1, p2, p3, p4, p5])
        db.commit()
        for p in [p1, p2, p3, p4, p5]:
            db.refresh(p)

        # --- Tasks ---
        tasks_data = [
            (p1.id, "Design homepage", "todo", "high", 0, admin.id),
            (p1.id, "Implement backend", "in_progress", "high", 1, admin.id),
            (p1.id, "Code review", "todo", "medium", 2, admin.id),
            (p2.id, "Setup project", "done", "medium", 0, admin.id),
            (p2.id, "Auth flow", "in_progress", "high", 1, admin.id),
            (p3.id, "Requirements doc", "todo", "low", 0, admin.id),
            (p4.id, "Discovery call", "done", "high", 0, manager_user.id),
            (p4.id, "Proposal draft", "in_progress", "medium", 1, manager_user.id),
            (p5.id, "Kickoff meeting", "todo", "high", 0, manager_user.id),
            (p5.id, "Requirements gathering", "todo", "medium", 1, manager_user.id),
        ]
        for project_id, title, status, priority, order_index, created_by in tasks_data:
            db.add(Task(
                project_id=project_id,
                title=title,
                status=status,
                priority=priority,
                order_index=order_index,
                due_date=today + timedelta(days=14),
                created_by=created_by,
            ))
        db.commit()

        # --- Meetings ---
        start = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
        end = start + timedelta(hours=1)
        m1 = Meeting(
            project_id=p1.id,
            title="Sprint planning",
            description="Q2 sprint planning",
            start_at=start,
            end_at=end,
            location="Conference room A",
            created_by=admin.id,
        )
        m2 = Meeting(
            project_id=None,
            title="Team standup",
            start_at=start + timedelta(days=1),
            end_at=end + timedelta(days=1),
            created_by=admin.id,
        )
        m3 = Meeting(
            project_id=p4.id,
            title="Sales kickoff",
            start_at=start + timedelta(days=2),
            end_at=end + timedelta(days=2),
            created_by=manager_user.id,
        )
        m4 = Meeting(
            project_id=p5.id,
            title="Discovery sync",
            description="Requirements for Custom Dashboard",
            start_at=start + timedelta(days=3),
            end_at=end + timedelta(days=3),
            created_by=manager_user.id,
        )
        db.add_all([m1, m2, m3, m4])
        db.flush()
        db.add(MeetingAttendee(meeting_id=m1.id, user_id=admin.id))
        db.add(MeetingAttendee(meeting_id=m2.id, user_id=admin.id))
        db.add(MeetingAttendee(meeting_id=m3.id, user_id=manager_user.id))
        db.add(MeetingAttendee(meeting_id=m4.id, user_id=admin.id))
        db.commit()

        # --- Invoices and payments ---
        inv1 = Invoice(
            client_id=c1.id,
            project_id=p1.id,
            number="INV-2024-001",
            amount=Decimal("5000.00"),
            currency="USD",
            status="paid",
            due_date=today + timedelta(days=30),
            issued_at=today - timedelta(days=5),
        )
        inv2 = Invoice(
            client_id=c1.id,
            project_id=p1.id,
            number="INV-2024-002",
            amount=Decimal("2500.00"),
            currency="USD",
            status="sent",
            due_date=today + timedelta(days=14),
            issued_at=today,
        )
        inv3 = Invoice(
            client_id=c4.id,
            project_id=p4.id,
            number="INV-2024-003",
            amount=Decimal("3000.00"),
            currency="USD",
            status="draft",
            due_date=today + timedelta(days=30),
            issued_at=today,
        )
        inv4 = Invoice(
            client_id=c5.id,
            project_id=p5.id,
            number="INV-2024-004",
            amount=Decimal("4000.00"),
            currency="USD",
            status="sent",
            due_date=today + timedelta(days=21),
            issued_at=today - timedelta(days=3),
        )
        db.add_all([inv1, inv2, inv3, inv4])
        db.commit()
        db.refresh(inv1)
        pay1 = Payment(
            invoice_id=inv1.id,
            amount=Decimal("5000.00"),
            paid_at=today - timedelta(days=2),
            reference="BANK-REF-001",
        )
        db.add(pay1)
        db.commit()

        # --- Expenses ---
        e1 = Expense(
            project_id=p1.id,
            description="Design assets",
            amount=Decimal("150.00"),
            currency="USD",
            expense_date=today - timedelta(days=10),
            created_by=admin.id,
        )
        e2 = Expense(
            project_id=p2.id,
            description="Cloud hosting",
            amount=Decimal("99.00"),
            currency="USD",
            expense_date=today,
            created_by=admin.id,
        )
        e3 = Expense(
            project_id=p4.id,
            description="Travel",
            amount=Decimal("200.00"),
            currency="USD",
            expense_date=today - timedelta(days=5),
            created_by=manager_user.id,
        )
        e4 = Expense(
            project_id=p5.id,
            description="Licenses",
            amount=Decimal("50.00"),
            currency="USD",
            expense_date=today,
            created_by=admin.id,
        )
        db.add_all([e1, e2, e3, e4])
        db.commit()

        print(
            "Demo data seeded:\n"
            "  Users: admin@example.com, manager@example.com, member@example.com, viewer@example.com (admin123 / demo123)\n"
            "  Roles: admin, manager, member, viewer (from seed_db)\n"
            "  Teams (12): Management, Product/PM, Frontend, Backend, Full-Stack, Mobile, Design, QA, DevOps, Data/AI, Sales & Marketing, Support\n"
            "  Leads: 2 (Sales); 1 converted → Client (Future Tech Inc) + Project (Custom Dashboard) → assigned to Product/PM\n"
            "  Clients: 5 | Projects: 5 (with pipeline_stage + assigned_team) | Tasks: 10 | Meetings: 4 | Invoices: 4 | Payments: 1 | Expenses: 4"
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()
