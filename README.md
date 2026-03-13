# AgencyOps

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Backend: FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688)](https://fastapi.tiangolo.com/)
[![Frontend: React](https://img.shields.io/badge/Frontend-React%20%2B%20TypeScript-61DAFB)](https://react.dev/)
[![Desktop: Electron](https://img.shields.io/badge/Desktop-Electron-47848F)](https://www.electronjs.org/)

**AgencyOps** is a free, open-source agency management software for software houses, marketing agencies, and creative studios. Manage your entire agency from one platform — clients, projects, tasks, leads, meetings, finance, and team collaboration.

> Self-hostable alternative to tools like Monday.com, ClickUp, or HubSpot CRM — built for agencies.

### Key features

- **CRM & Lead management** — pipeline tracking, lead assignment, status workflow
- **Client management** — profiles, contact info, linked projects
- **Project & task management** — assign tasks, set deadlines, track progress
- **Meeting scheduling** — log and track client meetings
- **Finance** — invoices, payments, and expense tracking
- **Team management** — multi-team support with team leads
- **Role-based access control (RBAC)** — Admin, Manager, Sales, Developer, Finance, Viewer roles
- **Announcements & notifications** — broadcast to the team
- **Real-time messaging** — WebSocket-powered chat
- **Analytics & reporting** — cross-module insights
- **REST API** — fully documented, versioned API (`/api/v1`)
- **Desktop app** — Electron shell for Windows, macOS, Linux

### Tech stack

| Layer       | Technology                                |
| ----------- | ----------------------------------------- |
| Backend API | Python, FastAPI, SQLAlchemy, Alembic, JWT |
| Database    | PostgreSQL                                |
| Frontend    | React, TypeScript, Tailwind CSS, Vite     |
| Desktop     | Electron                                  |
| Auth        | JWT + role-based access control           |

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
alembic upgrade head
python scripts/seed_db.py
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Default admin user after seed: **admin@example.com** / **admin123**

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
pip install -r requirements.txt   # includes pytest, httpx
pytest
```

Requires DB migrated and `python scripts/seed_db.py` run first (admin user must exist).

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

## Deployment

To deploy the backend and PostgreSQL on **DigitalOcean** so you can install the app on other devices and connect them to one server, see:

- **[Deployment on DigitalOcean](docs/deployment-digitalocean.md)** — Managed PostgreSQL, App Platform or Droplet, env vars, migrations, and client setup.

## Project structure

- **backend/** — FastAPI app, SQLAlchemy models, Alembic migrations, RBAC, JWT
- **frontend/** — React + Vite + TypeScript + Tailwind, API client, pages
- **docs/** — architecture, database schema, **deployment**
- **agents/** — agent role definitions (architect, backend, frontend, etc.)
- **tasks/** — current-task.md for agent handoffs

## Environment

- **Backend** (`backend/.env`): `DATABASE_URL`, `JWT_SECRET`, `DEBUG`, `CORS_ORIGINS`
- **Frontend** (`frontend/.env`): `VITE_API_URL=http://localhost:8000` (API base URL)

## API base path

All API routes are under `/api/v1`: auth, users, roles, clients, projects, tasks, meetings, finance (invoices, payments, expenses), analytics.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
