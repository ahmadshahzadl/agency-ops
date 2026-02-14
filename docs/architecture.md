# Software House Management System — System Architecture

## 1. Overview

The system is a **Software House Management System** used to manage clients, projects, tasks, meetings, finance, and analytics. It consists of a desktop frontend (React + Electron), a REST API backend (FastAPI), and a PostgreSQL database. Authentication is JWT-based with role-based access control (RBAC).

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Electron Shell (Desktop)                      │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              React App (TypeScript + Tailwind)               │ │
│  │  • Pages / Dashboards  • Role-based navigation  • Charts     │ │
│  └──────────────────────────────┬──────────────────────────────┘ │
│                                 │                                 │
│  ┌──────────────────────────────▼──────────────────────────────┐ │
│  │              Integration Layer (API Client)                  │ │
│  │  • Typed requests/responses  • Auth tokens  • Error handling  │ │
│  └──────────────────────────────┬──────────────────────────────┘ │
└──────────────────────────────────┼────────────────────────────────┘
                                   │ HTTPS / REST
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌────────────┐ │
│  │   Auth      │ │   Clients   │ │   Projects  │ │   Tasks    │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └────────────┘ │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                 │
│  │   Meetings  │ │   Finance   │ │  Analytics  │                 │
│  └─────────────┘ └─────────────┘ └─────────────┘                 │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Middleware: JWT validation, RBAC, CORS, logging             │ │
│  └─────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────┬────────────────────────────────┘
                                   │ SQLAlchemy ORM
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PostgreSQL                                    │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Component Responsibilities

| Layer | Stack | Responsibility |
|-------|--------|----------------|
| **Frontend** | React, Electron, TypeScript, Tailwind | UI, dashboards, role-based navigation, charts |
| **Integration** | API client, types | Typed API calls, token handling, errors, caching |
| **Backend** | Python, FastAPI | REST API, business logic, RBAC, validation |
| **Data** | PostgreSQL, SQLAlchemy | Persistence, migrations |

## 4. API Structure

- **Base path**: `/api/v1`
- **Auth**: `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout`
- **Resources** (CRUD where applicable):
  - `/api/v1/users` — user management (admin)
  - `/api/v1/roles` — roles and permissions
  - `/api/v1/clients` — client management
  - `/api/v1/projects` — projects (linked to clients)
  - `/api/v1/tasks` — tasks (linked to projects)
  - `/api/v1/meetings` — meetings
  - `/api/v1/finance` — invoices, payments, expenses
  - `/api/v1/analytics` — dashboard aggregates (read-only)

All protected routes require `Authorization: Bearer <access_token>`. RBAC is enforced per endpoint using permission codes.

## 5. Folder Structure

### Backend (recommended)

```
backend/
├── app/
│   ├── main.py              # FastAPI app, middleware
│   ├── config.py            # Settings (env, no hardcoding)
│   ├── database.py          # Engine, session, base
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic request/response
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── roles.py
│   │   │   ├── clients.py
│   │   │   ├── projects.py
│   │   │   ├── tasks.py
│   │   │   ├── meetings.py
│   │   │   ├── finance.py
│   │   │   └── analytics.py
│   │   └── deps.py          # Deps: get_db, get_current_user, require_permission
│   ├── services/            # Business logic (modular)
│   ├── core/                # Security, RBAC, JWT
│   └── jobs/                # Automation (e.g. scheduled)
├── alembic/                 # Migrations
├── tests/
└── requirements.txt
```

### Frontend (recommended)

```
frontend/
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── api/                 # API client, types, auth
│   ├── components/
│   ├── pages/
│   ├── layouts/
│   ├── hooks/
│   ├── store/               # State (e.g. auth, theme)
│   ├── routes/              # Role-based routes
│   └── utils/
├── electron/                # Main process, preload
├── package.json
└── tailwind.config.js
```

### Shared / Docs

```
docs/
├── architecture.md          # This file
├── database-schema.md
├── api-spec.md
└── roadmap.md
tasks/
└── current-task.md          # Task for backend/frontend/integration agents
```

## 6. Security

- **Authentication**: JWT access tokens (short-lived) + refresh tokens (stored securely; rotation optional).
- **Authorization**: RBAC — each role has a set of permissions; endpoints check permission codes (e.g. `clients:write`, `projects:read`).
- **No hardcoded secrets**: All config (DB URL, JWT secret, etc.) from environment variables.
- **CORS**: Configured for the Electron app origin in development and production.

## 7. Scalability and Conventions

- **Modular services**: Business logic in `services/`, not in route handlers.
- **Validations**: Pydantic on input; DB constraints on persistence.
- **Migrations**: Alembic for all schema changes.
- **API versioning**: `/api/v1` to allow future v2 without breaking clients.

---

*Generated by Architect Agent. Implementation tasks are assigned via `/tasks/current-task.md` to backend, frontend, and integration agents.*
