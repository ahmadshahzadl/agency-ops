# Software House Management System

Desktop application for managing clients, projects, tasks, meetings, finance, and analytics. Built with **FastAPI** (backend), **React + TypeScript + Tailwind** (frontend), and **Electron** (desktop shell). **PostgreSQL** with **SQLAlchemy** and **JWT + RBAC** for auth.

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

## Project structure

- **backend/** — FastAPI app, SQLAlchemy models, Alembic migrations, RBAC, JWT
- **frontend/** — React + Vite + TypeScript + Tailwind, API client, pages
- **docs/** — architecture, database schema, API, roadmap
- **agents/** — agent role definitions (architect, backend, frontend, etc.)
- **tasks/** — current-task.md for agent handoffs

## Environment

- **Backend** (`backend/.env`): `DATABASE_URL`, `JWT_SECRET`, `DEBUG`, `CORS_ORIGINS`
- **Frontend** (`frontend/.env`): `VITE_API_URL=http://localhost:8000` (API base URL)

## API base path

All API routes are under `/api/v1`: auth, users, roles, clients, projects, tasks, meetings, finance (invoices, payments, expenses), analytics.
