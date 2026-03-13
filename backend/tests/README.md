# Backend API tests

Pytest tests for the AgencyOps API, including **roles, permissions, and the updated flow** (Admin, Manager, Employee).

## Setup (required before running tests)

1. **Migrations**
   ```bash
   cd backend && alembic upgrade head
   ```

2. **Seed database** (creates admin user and roles: admin, manager, employee, member)
   ```bash
   cd backend && python scripts/seed_db.py
   ```
   This creates:
   - **admin@example.com** / **admin123** (admin role)
   - Roles: **admin**, **manager**, **employee**, **member** with seeded RBAC permissions

3. **Run tests**
   ```bash
   cd backend && .venv\Scripts\python -m pytest tests/ -v
   ```
   Or from repo root:
   ```bash
   python scripts/test_backend.py
   ```

If login returns 401, the DB is likely not seeded — run `python scripts/seed_db.py` from the `backend` directory.

---

## Test modules and what they cover

| Module | Coverage |
|--------|----------|
| **test_auth.py** | Login, /me, refresh token; admin permissions in response. |
| **test_health.py** | GET /health. |
| **test_clients.py** | List/create/update/delete clients (admin); **employee gets 403** on list (no clients:read). |
| **test_finance.py** | Invoices: admin create/list; manager can list (finance:read); **employee 403** on list. **Expenses: admin only** — list/create/update/delete with admin; **manager and employee get 403** on expenses (no expenses:read/write). |
| **test_announcements.py** | **New.** List/get: admin, manager, employee (announcements:read). Create/update/delete: **admin only**; manager and employee get 403. |
| **test_analytics.py** | Overview: admin 200; **employee 403** (no analytics:read). **Dashboard: all authenticated** — admin and employee both 200; response shape differs by role. |
| **test_projects.py** | Projects CRUD (admin). |
| **test_tasks.py** | Tasks CRUD (admin). |
| **test_meetings.py** | Meetings CRUD (admin). |

## Fixtures (conftest.py)

- **client** — TestClient for the FastAPI app.
- **auth_headers** — Bearer token for **admin@example.com** (requires seed).
- **manager_headers** — Bearer token for a user with **manager** role (created by admin if missing; email **manager@test.com** / **test123**).
- **employee_headers** — Bearer token for a user with **employee** role (created by admin if missing; email **employee@test.com** / **test123**).

Manager and employee users are created on first use; if roles are missing, tests that need them are skipped.
