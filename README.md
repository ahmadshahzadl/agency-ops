# Fuorix

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![Frontend: React](https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-61DAFB)](https://react.dev/)
[![Desktop: Electron](https://img.shields.io/badge/Desktop-Electron-47848F)](https://www.electronjs.org/)

**Fuorix** is a free, open-source agency management platform for software houses, marketing agencies, and creative studios. It covers the entire agency loop in one self-hosted app: **lead → quote → project → kanban board with a QA gate → logged hours → invoice PDF → payment — with a client portal on top.**

> Self-hostable alternative to tools like Monday.com, ClickUp, or HubSpot CRM — built for agencies.

### Key features

**Delivery**
- **Kanban boards with QA workflow** — multiple boards per project, member-scoped access, server-enforced pipeline: `todo → in progress → review → done / QA failed`. Only QA-permission holders approve or fail reviews; failing requires notes and notifies the assignee
- **Bug tracking** — tasks as bugs with severity, steps to reproduce, environment, and file attachments (screenshots, logs)
- **Milestones** — project phases with due dates and auto-progress from linked tasks; overdue detection
- **Time tracking** — per-project/task hours with billable flags, manager timesheets, rate handling

**Sales & money**
- **Quotes/proposals** — line-item quotes against leads or clients with a full lifecycle (draft → sent → accepted/rejected, auto-expiry), PDF + email delivery, one-click conversion to project (budget carried over) and fixed-price invoice
- **Invoices** — line items or generated from unbilled hours / accepted quotes; branded PDFs with your logo, bank/payment details, and optional currency-equivalent display (e.g. USD total with PKR conversion); emailed to clients with the PDF attached
- **Payment reconciliation** — payments auto-settle invoices (partial → balance tracking, full → paid), overpayment guards, paid invoices become immutable, automatic overdue detection
- **CRM & leads** — pipeline tracking, new-lead visibility for the sales role, conversion flow

**Clients**
- **Client portal** — real client logins locked to a dedicated API namespace: project progress with milestone timelines, invoices with PDFs, proposals with one-click accept/decline, and issue reporting that lands as bug tasks in your QA intake. Zero access to anything internal — enforced by construction and tests
- **Share links** — no-account alternative: revocable tokenized progress pages, sanitized (no assignees, notes, or internal QA states)

**Platform**
- **RBAC** — seeded Admin / Manager / Employee / QA / Client roles over a permission table, with object-level and row-level scoping on every module; role-focused dashboards (QA sees their review queue, sales sees their pipeline, finance figures admin-gated)
- **Email** — SMTP-based password resets (single-use hashed tokens, session revocation), task/QA/quote/announcement notification emails, document delivery
- **Hardened auth** — revocable JWTs (logout-everywhere, password change kills stolen sessions), login rate limiting, no-enumeration password reset, login audit trail, fail-hard startup on insecure config
- **Real-time** — WebSocket-powered messaging and live board/task updates
- **REST API** — versioned `/api/v1` with interactive docs at `/docs`; 149-test backend suite
- **Desktop app** — Electron shell for Windows, macOS, Linux

### Tech stack

| Layer       | Technology                                |
| ----------- | ----------------------------------------- |
| Backend API | Python, FastAPI, SQLAlchemy, Alembic, JWT |
| Database    | PostgreSQL                                |
| Frontend    | React, TypeScript, Tailwind CSS, Vite, dnd-kit |
| PDFs        | fpdf2 (pure Python, no system deps)       |
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

**Admin credentials:** set `ADMIN_EMAIL` / `ADMIN_PASSWORD` (env vars or in `backend/.env`) before seeding. If unset, the seed generates a random password and prints it once. Change it after first login.

**Demo data (optional):**

```bash
python scripts/seed_demo_data.py
```

Creates sample clients, projects, a kanban board with the full QA pipeline, time entries, quotes, invoices, and payments for testing.

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
| `admin`    | Everything, including finance, expenses, and user/team/role management |
| `manager`  | Team-scoped clients, projects, tasks, meetings, leads, quotes, and timesheets; **no finance or expenses**; creates boards, milestones, and client share links for their projects |
| `employee` | Own tasks, assigned projects/boards, own timesheet, meetings (read), notes, attachments |
| `qa`       | Employee access **plus** `tasks:qa_approve` — the only non-admin role that can approve a review to done or fail it back with notes; their dashboard surfaces the review queue |
| `client`   | Portal-only external users (set the user's client link): project progress, invoices, proposals, issue reporting — zero internal access |

Two conventions worth knowing:
- **Manager scope comes from reports, not the role name**: whoever is set as a user's *Manager* gains team visibility over them (tasks, time, boards). A manager-role user with no reports behaves like a member for scoping.
- **A role literally named `sales`** (create it with no permissions) makes all *new* leads visible to its holders — give it to your BD person alongside `manager`.

Board access is per-board: managers/admins add members, and only members see the board and its tasks — this is also how QA gets their review queue.

## Deployment

- **[Droplet / VPS runbook](docs/deployment-droplet.md)** — the battle-tested path: single Ubuntu server (works alongside an existing site), local PostgreSQL, systemd + nginx + Let's Encrypt, backups, update procedure, and server-migration recipe
- **[DigitalOcean App Platform / Managed DB](docs/deployment-digitalocean.md)** — alternative managed setup

Security notes for internet-facing deployments: run a **single backend worker** (in-memory WebSocket state), terminate TLS at a reverse proxy or tunnel, and don't log query strings (WebSocket auth tokens travel there).

**Email on a VPS:** most cloud providers block outbound SMTP ports (25/465/587) by default — request an unblock via support, or use a relay on an alternate port (Brevo `smtp-relay.brevo.com:2525`, Resend `smtp.resend.com:2587`). See the commented examples in `backend/.env.example`.

## Project structure

- **backend/** — FastAPI app, SQLAlchemy models, 23 Alembic migrations, RBAC, JWT, PDF generation, email service
- **frontend/** — React + Vite + TypeScript + Tailwind: internal app, client portal, public status pages
- **docs/** — architecture, database schema, deployment runbooks

## Environment

- **Backend** (`backend/.env`, see `backend/.env.example`): `DATABASE_URL`, `JWT_SECRET` (required in production), `CORS_ORIGINS` (explicit origins), `FRONTEND_URL` (links in emails), `UPLOAD_DIR` (attachment storage), `SMTP_*` (email — password resets and notifications are inert without it), `COMPANY_DETAILS` (PDF footer), `ADMIN_EMAIL`/`ADMIN_PASSWORD` (seed only), `SUPER_ADMIN_EMAIL` (optional, off by default)
- **Frontend** (`frontend/.env`): `VITE_API_URL` (API base URL, **baked in at build time**), optional `VITE_APP_NAME` / `VITE_APP_LOGO` branding overrides

## API base path

All API routes are under `/api/v1`: auth (incl. password reset), users, roles, teams, clients, leads, quotes, projects, milestones, tasks, boards, meetings, finance (invoices with line items, payments, expenses), time entries, attachments, analytics, announcements, notifications, notes, messages, team activity, share links, and the client-scoped `/portal/*` namespace — plus the unauthenticated `GET /api/v1/public/status/{token}` for share-link progress pages. Interactive docs at `/docs`.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
