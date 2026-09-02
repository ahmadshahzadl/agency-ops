# Fuorix

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![Frontend: React](https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-61DAFB)](https://react.dev/)
[![Desktop: Electron](https://img.shields.io/badge/Desktop-Electron-47848F)](https://www.electronjs.org/)

**Fuorix** is a free, open-source agency management software for software houses, marketing agencies, and creative studios. Manage your entire agency from one platform — clients, projects, kanban boards with a QA gate, leads, meetings, finance, client-facing progress pages, and team collaboration.

> Self-hostable alternative to tools like Monday.com, ClickUp, or HubSpot CRM — built for agencies.

### Key features

- **Kanban boards with QA workflow** — multiple boards per project, member-scoped access, and a server-enforced pipeline: `todo → in progress → review → done / QA failed`. Only users with the QA permission can approve or fail a task in review; failing requires notes and notifies the assignee
- **Bug tracking** — tasks can be bugs with severity, steps to reproduce, and environment
- **Client progress pages** — mint revocable share links; clients see a branded, read-only progress page (task titles and status only — no assignees, notes, or internal QA states) without needing an account
- **CRM & lead management** — pipeline tracking, lead assignment, status workflow
- **Client management** — profiles, contact info, linked projects
- **Project & task management** — assign tasks, set deadlines, track progress
- **Meeting scheduling** — log and track client meetings
- **Finance** — invoices, payments, and expense tracking
- **Team management** — multi-team support with manager scoping
- **Role-based access control (RBAC)** — seeded Admin, Manager, Employee, and QA roles backed by a permission table; object-level scoping on every module
- **Announcements & notifications** — broadcast to the whole team or target specific users
- **Real-time messaging** — WebSocket-powered chat, plus live board/task updates
- **Analytics & reporting** — cross-module insights, finance figures permission-gated
- **Hardened auth** — JWT with server-side token revocation (logout everywhere, password change kills stolen tokens), login rate limiting, login audit trail
- **REST API** — versioned API (`/api/v1`) with interactive docs at `/docs`
- **Desktop app** — Electron shell for Windows, macOS, Linux

### Tech stack

| Layer       | Technology                                |
| ----------- | ----------------------------------------- |
| Backend API | Python, FastAPI, SQLAlchemy, Alembic, JWT |
| Database    | PostgreSQL                                |
| Frontend    | React, TypeScript, Tailwind CSS, Vite, dnd-kit |
| Desktop     | Electron                                  |
| Auth        | JWT (revocable) + role-based access control |

## Quick start

### 1. Database

Create a PostgreSQL database and set the connection URL (or use default):

```bash
# Default: postgresql://postgres:postgres@localhost:5432/office_software
# Override with .env in backend/:
# DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit: set JWT_SECRET (or DEBUG=true for local dev)
alembic upgrade head
python scripts/seed_db.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> **The app refuses to start without a real `JWT_SECRET`** unless `DEBUG=true`. Generate one with `openssl rand -hex 32`. It also rejects `CORS_ORIGINS=*` — list explicit origins.

**Admin credentials:** set `ADMIN_EMAIL` / `ADMIN_PASSWORD` env vars before seeding. If `ADMIN_PASSWORD` is unset, the seed generates a random password and prints it once. Change it after first login.

**Demo data (optional):**

```bash
python scripts/seed_demo_data.py
```

Creates sample clients, projects, tasks, meetings, invoices, payments, and expenses for testing.

**Reset database** (drops all tables, re-runs migrations, seeds admin + demo data):

```bash
python scripts/reset_db.py           # reset + seed admin + demo data
python scripts/reset_db.py --no-seed # reset only, no seed
```

**Run tests:**

```bash
cd backend
pytest
```

Requires DB migrated and `python scripts/seed_db.py` run first. Tests log in as the seeded admin — if you seeded with custom credentials, set `TEST_ADMIN_EMAIL` / `TEST_ADMIN_PASSWORD`.

### 3. Frontend (web)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and log in.

### 4. Frontend (Electron desktop)

With backend and `npm run dev` already running in another terminal:

```bash
cd frontend
npm run electron:dev
```

## Roles

Seeded by `scripts/seed_db.py` (customizable in the Roles UI):

| Role       | Access |
| ---------- | ------ |
| `admin`    | Everything, including user/team/role management |
| `manager`  | Team-scoped clients, projects, tasks, meetings, leads; finance read; creates boards and client share links for their projects |
| `employee` | Own tasks, assigned projects/boards, meetings (read), notes |
| `qa`       | Employee access **plus** `tasks:qa_approve` — the only non-admin role that can move a task from review to done, or fail it back with notes |

Board access is per-board: managers/admins add members, and only members see the board and its tasks.

## Deployment

To deploy the backend and PostgreSQL so other devices connect to one server, see:

- **[Deployment on DigitalOcean](docs/deployment-digitalocean.md)** — Managed PostgreSQL, App Platform or Droplet, env vars, migrations, and client setup. The same recipe applies to any Ubuntu server.

Security notes for internet-facing deployments: run a single backend worker (in-memory WebSocket state), terminate TLS at a reverse proxy or tunnel, and don't log query strings (WebSocket auth tokens travel there).

## Project structure

- **backend/** — FastAPI app, SQLAlchemy models, Alembic migrations, RBAC, JWT
- **frontend/** — React + Vite + TypeScript + Tailwind, API client, pages
- **docs/** — architecture, database schema, deployment

## Environment

- **Backend** (`backend/.env`, see `backend/.env.example`): `DATABASE_URL`, `JWT_SECRET` (required in production), `CORS_ORIGINS` (explicit origins), `DEBUG`, `ADMIN_EMAIL`/`ADMIN_PASSWORD` (seed only), `SUPER_ADMIN_EMAIL` (optional, off by default)
- **Frontend** (`frontend/.env`): `VITE_API_URL=http://localhost:8000` (API base URL, baked in at build time), optional `VITE_APP_NAME` / `VITE_APP_LOGO` branding overrides

## API base path

All API routes are under `/api/v1`: auth, users, roles, teams, clients, leads, projects, tasks, boards, meetings, finance (invoices, payments, expenses), analytics, announcements, notifications, notes, messages, team activity, share links — plus the unauthenticated `GET /api/v1/public/status/{token}` for client progress pages. Interactive docs at `/docs`.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
