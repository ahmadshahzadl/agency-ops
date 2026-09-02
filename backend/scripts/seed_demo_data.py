"""Seed demo data: all team types, user types (admin, manager, member, employee) per roles-permissions-flow.
Run after migrations and seed_db.py. Uses roles: admin, manager, employee, member only."""
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
    Board,
    BoardMember,
    TimeEntry,
    Quote,
    QuoteItem,
)
from app.core.security import get_password_hash

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

DEMO_PASSWORD = "demo123"


def _get_or_create_user(
    db,
    email: str,
    full_name: str,
    password: str,
    role_name: str,
    phone: str | None = None,
    job_title: str | None = None,
) -> User:
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
        phone=phone,
        job_title=job_title,
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

        if db.query(Client).first():
            print("Demo data already exists. Skipping.")
            return

        # --- All 12 teams ---
        teams_by_type = {}
        for name, team_type, desc in TEAM_TYPES:
            t = Team(name=name, description=desc, team_type=team_type)
            db.add(t)
            db.flush()
            teams_by_type[team_type] = t
        db.commit()
        for t in teams_by_type.values():
            db.refresh(t)

        # --- Per-team users: one manager, one employee, one member per team (each employee/member reports to that team's manager) ---
        team_managers = {}
        team_employees = {}
        team_members = {}
        for display_name, team_type, _ in TEAM_TYPES:
            safe = team_type.replace("-", "_")
            team_managers[team_type] = _get_or_create_user(
                db, f"manager_{safe}@example.com", f"Manager {display_name}", DEMO_PASSWORD, "manager",
                phone=None, job_title=f"Manager ({display_name})",
            )
            team_employees[team_type] = _get_or_create_user(
                db, f"employee_{safe}@example.com", f"Employee {display_name}", DEMO_PASSWORD, "employee",
                phone=None, job_title=f"Staff ({display_name})",
            )
            team_members[team_type] = _get_or_create_user(
                db, f"member_{safe}@example.com", f"Member {display_name}", DEMO_PASSWORD, "member",
                phone=None, job_title=f"Member ({display_name})",
            )
        db.commit()
        for u in list(team_managers.values()) + list(team_employees.values()) + list(team_members.values()):
            db.refresh(u)

        # --- Team membership: admin in ALL teams; each team has its manager, employee, and member ---
        all_teams = list(teams_by_type.values())
        team_memberships = []
        for t in all_teams:
            team_memberships.append(TeamMember(team_id=t.id, user_id=admin.id))
        for team_type, t in teams_by_type.items():
            team_memberships.append(TeamMember(team_id=t.id, user_id=team_managers[team_type].id))
            team_memberships.append(TeamMember(team_id=t.id, user_id=team_employees[team_type].id))
            team_memberships.append(TeamMember(team_id=t.id, user_id=team_members[team_type].id))
        db.add_all(team_memberships)

        # --- Manager hierarchy: each team's employee and member report to that team's manager ---
        for team_type in teams_by_type:
            team_employees[team_type].manager_id = team_managers[team_type].id
            team_members[team_type].manager_id = team_managers[team_type].id
        db.commit()
        for team_type in teams_by_type:
            db.refresh(team_employees[team_type])
            db.refresh(team_members[team_type])

        # Aliases for demo data below (use product_pm and sales_marketing teams for leads/projects/etc.)
        team_pm = teams_by_type["product_pm"]
        team_sales = teams_by_type["sales_marketing"]
        team_frontend = teams_by_type["frontend"]
        team_backend = teams_by_type["backend"]
        team_qa = teams_by_type["qa"]
        team_design = teams_by_type["design"]
        team_management = teams_by_type["management"]
        team_fullstack = teams_by_type["fullstack"]
        team_devops = teams_by_type["devops"]
        manager_user = team_managers["product_pm"]
        member_user = team_members["frontend"]
        employee_user = team_employees["qa"]
        sales_user = team_managers["sales_marketing"]
        sales_member_user = team_employees["sales_marketing"]

        # --- Leads: by manager (team leads), by sales lead manager, by sales member (own leads) ---
        leads = [
            Lead(
                company_name="Future Tech Inc",
                contact_name="Jane Doe",
                contact_email="jane@futuretech.example",
                contact_phone="+1-555-1000",
                source="website",
                status="qualified",
                notes="Interested in custom dashboard.",
                assigned_team_id=team_sales.id,
                created_by=manager_user.id,
            ),
            Lead(
                company_name="Startup Alpha",
                contact_name="John Smith",
                contact_email="john@startupalpha.example",
                source="referral",
                status="contacted",
                assigned_team_id=team_sales.id,
                created_by=manager_user.id,
            ),
            Lead(
                company_name="Enterprise Beta",
                contact_name="Alice Lee",
                contact_email="alice@enterprise.example",
                source="cold_outreach",
                status="new",
                assigned_team_id=team_sales.id,
                created_by=sales_user.id,
            ),
            Lead(
                company_name="Local Biz Co",
                contact_name="Bob Wilson",
                contact_email="bob@localbiz.example",
                status="qualified",
                assigned_team_id=team_sales.id,
                created_by=sales_member_user.id,
            ),
        ]
        db.add_all(leads)
        db.commit()
        for lead in leads:
            db.refresh(lead)

        # --- Clients: created_by admin, manager, sales (for manager/sales scope) ---
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
            created_by=manager_user.id,
        )
        c4 = Client(
            name="Sales Lead Co",
            contact_email="sales@sl.example",
            contact_phone="+1-555-0300",
            team_id=team_sales.id,
            created_by=manager_user.id,
        )
        c5 = Client(
            name="Enterprise Client",
            contact_email="enterprise@example.com",
            team_id=team_sales.id,
            created_by=sales_user.id,
        )
        db.add_all([c1, c2, c3, c4, c5])
        db.commit()
        for c in [c1, c2, c3, c4, c5]:
            db.refresh(c)

        # Convert first lead → client c6 + project later
        c6 = Client(
            name=leads[0].company_name,
            contact_email=leads[0].contact_email,
            contact_phone=leads[0].contact_phone,
            team_id=team_sales.id,
            created_by=manager_user.id,
        )
        db.add(c6)
        db.commit()
        db.refresh(c6)
        leads[0].converted_to_client_id = c6.id
        leads[0].converted_at = datetime.now(timezone.utc)
        leads[0].status = "converted"
        db.commit()

        # --- Projects: owner_id admin or manager (managers can assign; members see only assigned tasks) ---
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
            client_id=c6.id,
            name="Custom Dashboard",
            description="Converted from lead: Future Tech Inc",
            status="draft",
            pipeline_stage="discovery",
            assigned_team_id=team_pm.id,
            start_date=today,
            owner_id=manager_user.id,
        )
        p6 = Project(
            client_id=c5.id,
            name="Enterprise Platform",
            description="Large-scale platform",
            status="active",
            pipeline_stage="development",
            assigned_team_id=team_backend.id,
            start_date=today - timedelta(days=7),
            owner_id=sales_user.id,
        )
        db.add_all([p1, p2, p3, p4, p5, p6])
        db.commit()
        for p in [p1, p2, p3, p4, p5, p6]:
            db.refresh(p)

        # --- Tasks: assignee_id set so member/viewer/sales_member see "my tasks"; created_by admin/manager ---
        tasks_data = [
            (p1.id, "Design homepage", "todo", "high", 0, admin.id, member_user.id),
            (p1.id, "Implement backend", "in_progress", "high", 1, admin.id, member_user.id),
            (p1.id, "Code review", "todo", "medium", 2, admin.id, employee_user.id),
            (p2.id, "Setup project", "done", "medium", 0, admin.id, admin.id),
            (p2.id, "Auth flow", "in_progress", "high", 1, admin.id, member_user.id),
            (p3.id, "Requirements doc", "todo", "low", 0, admin.id, None),
            (p4.id, "Discovery call", "done", "high", 0, manager_user.id, manager_user.id),
            (p4.id, "Proposal draft", "in_progress", "medium", 1, manager_user.id, member_user.id),
            (p5.id, "Kickoff meeting", "todo", "high", 0, manager_user.id, None),
            (p5.id, "Requirements gathering", "todo", "medium", 1, manager_user.id, employee_user.id),
            (p6.id, "Sales follow-up", "todo", "high", 0, sales_user.id, sales_member_user.id),
            (p6.id, "Demo prep", "in_progress", "medium", 1, sales_user.id, sales_member_user.id),
        ]
        for project_id, title, status, priority, order_index, created_by, assignee_id in tasks_data:
            db.add(Task(
                project_id=project_id,
                title=title,
                status=status,
                priority=priority,
                order_index=order_index,
                due_date=today + timedelta(days=14),
                created_by=created_by,
                assignee_id=assignee_id,
            ))
        db.commit()

        # --- Meetings: created_by and attendees for visibility (member/viewer see where they attend) ---
        start = datetime.now(timezone.utc).replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
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
        m5 = Meeting(
            project_id=p6.id,
            title="Enterprise demo",
            start_at=start + timedelta(days=4),
            end_at=end + timedelta(days=4),
            created_by=sales_member_user.id,
        )
        db.add_all([m1, m2, m3, m4, m5])
        db.flush()
        db.add(MeetingAttendee(meeting_id=m1.id, user_id=admin.id))
        db.add(MeetingAttendee(meeting_id=m1.id, user_id=member_user.id))
        db.add(MeetingAttendee(meeting_id=m2.id, user_id=admin.id))
        db.add(MeetingAttendee(meeting_id=m2.id, user_id=member_user.id))
        db.add(MeetingAttendee(meeting_id=m2.id, user_id=employee_user.id))
        db.add(MeetingAttendee(meeting_id=m3.id, user_id=manager_user.id))
        db.add(MeetingAttendee(meeting_id=m4.id, user_id=admin.id))
        db.add(MeetingAttendee(meeting_id=m5.id, user_id=sales_user.id))
        db.add(MeetingAttendee(meeting_id=m5.id, user_id=sales_member_user.id))
        db.commit()

        # --- Invoices (clients created_by in scope for manager/sales) ---
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
            client_id=c6.id,
            project_id=p5.id,
            number="INV-2024-004",
            amount=Decimal("4000.00"),
            currency="USD",
            status="sent",
            due_date=today + timedelta(days=21),
            issued_at=today - timedelta(days=3),
        )
        inv5 = Invoice(
            client_id=c5.id,
            project_id=p6.id,
            number="INV-2024-005",
            amount=Decimal("10000.00"),
            currency="USD",
            status="paid",
            due_date=today + timedelta(days=30),
            issued_at=today - timedelta(days=10),
        )
        db.add_all([inv1, inv2, inv3, inv4, inv5])
        db.commit()
        db.refresh(inv1)
        pay1 = Payment(
            invoice_id=inv1.id,
            amount=Decimal("5000.00"),
            paid_at=today - timedelta(days=2),
            reference="BANK-REF-001",
        )
        pay2 = Payment(
            invoice_id=inv5.id,
            amount=Decimal("10000.00"),
            paid_at=today - timedelta(days=5),
            reference="BANK-REF-002",
        )
        db.add_all([pay1, pay2])
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
            project_id=p6.id,
            description="Licenses",
            amount=Decimal("50.00"),
            currency="USD",
            expense_date=today,
            created_by=sales_user.id,
        )
        db.add_all([e1, e2, e3, e4])
        db.commit()

        # --- Boards + QA pipeline tasks (p1) ---
        p1.hourly_rate = Decimal("75.00")
        board = Board(project_id=p1.id, name="Sprint 1", created_by=admin.id)
        db.add(board)
        db.flush()
        for uid in {admin.id, manager_user.id, employee_user.id}:
            db.add(BoardMember(board_id=board.id, user_id=uid))
        board_tasks = [
            ("Design landing page", "done", "task", None),
            ("Implement auth flow", "in_progress", "task", None),
            ("Checkout crashes on mobile", "review", "bug", "high"),
            ("Broken layout on Safari", "qa_failed", "bug", "medium"),
            ("Payment webhook retries", "todo", "task", None),
        ]
        for i, (title, status_val, item_type, severity) in enumerate(board_tasks):
            db.add(Task(
                project_id=p1.id, board_id=board.id, title=title, status=status_val,
                item_type=item_type, severity=severity,
                steps_to_reproduce="1. Open checkout 2. Pay on mobile" if item_type == "bug" else None,
                qa_notes="Crashes on iOS 17 — see attached log" if status_val == "qa_failed" else None,
                assignee_id=employee_user.id, created_by=manager_user.id, column_order=i,
            ))
        db.commit()

        # --- Time entries on p1 ---
        for days_ago, hours, desc, billable in [
            (1, "6.0", "Auth flow implementation", True),
            (2, "4.5", "Bug triage and fixes", True),
            (3, "2.0", "Internal sync", False),
            (5, "7.5", "Landing page build", True),
        ]:
            db.add(TimeEntry(
                user_id=employee_user.id, project_id=p1.id,
                work_date=today - timedelta(days=days_ago),
                hours=Decimal(hours), description=desc, billable=billable,
            ))
        db.commit()

        # --- Quotes ---
        q1 = Quote(number="QUO-DEMO-0001", title="Website Redesign", client_id=c1.id,
                   status="sent", currency="USD", valid_until=today + timedelta(days=14),
                   terms="50% upfront, 50% on delivery.", created_by=sales_user.id)
        q2 = Quote(number="QUO-DEMO-0002", title="Mobile App MVP", client_id=c2.id,
                   status="accepted", currency="USD", accepted_at=datetime.now(timezone.utc),
                   created_by=sales_user.id)
        db.add_all([q1, q2])
        db.flush()
        for q, items in ((q1, [("Design", 1, 1500), ("Development", 40, 60)]),
                         (q2, [("Discovery", 1, 800), ("MVP build", 60, 55)])):
            total = Decimal("0")
            for pos, (desc, qty, price) in enumerate(items):
                db.add(QuoteItem(quote_id=q.id, description=desc, quantity=Decimal(qty),
                                 unit_price=Decimal(price), position=pos))
                total += Decimal(qty) * Decimal(price)
            q.total = total
        db.commit()

        print(
            "Demo data seeded.\n"
            "  Users (password: admin123 for admin, demo123 for others):\n"
            "    admin@example.com (admin) – in all 12 teams, full access\n"
            "    Per team (one manager + one employee + one member per team, employee/member report to manager):\n"
            "      manager_<team>@example.com (manager), employee_<team>@example.com (employee), member_<team>@example.com (member)\n"
            "      e.g. manager_frontend@example.com, employee_frontend@example.com, member_frontend@example.com\n"
            "  Teams: 12 (management, product_pm, frontend, backend, fullstack, mobile, design, qa, devops, data_ai, sales_marketing, support)\n"
            "  Data: 4 leads (1 converted), 6 clients, 6 projects, 12+ tasks, 5 meetings, 5 invoices, 2 payments, 4 expenses,\n"
            "        1 board (Sprint 1, QA pipeline incl. bugs), 4 time entries, 2 quotes (1 sent, 1 accepted)"
        )
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()
