# Fuorix — Database Schema

## 1. Conventions

- **Primary keys**: `id` (UUID or bigserial), consistent across tables.
- **Timestamps**: `created_at`, `updated_at` (UTC) on main entities.
- **Soft delete**: Optional `deleted_at` where business requires (e.g. clients, projects).
- **Naming**: snake_case; tables plural where it reads well (e.g. `users`, `roles`, `clients`).

## 2. Entity Relationship Overview

```
users ──┬──< user_roles >── roles ──< role_permissions >── permissions
        │
        ├──< clients (created_by)
        ├──< projects (owner_id / team)
        └──< tasks (assignee_id)

clients ──< projects ──< tasks
                │
                └──< meetings (project_id or standalone)

finance: invoices, payments, expenses (link to clients/projects as needed)
```

## 3. Core Tables

### 3.1 Authentication & RBAC

**users**
| Column | Type | Constraints |
|-------------|--------------|-------------|
| id | UUID / bigint| PK |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| password_hash | VARCHAR(255) | NOT NULL |
| full_name | VARCHAR(255) | |
| is_active | BOOLEAN | DEFAULT true |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**roles**
| Column | Type | Constraints |
|-------------|--------------|-------------|
| id | UUID / bigint| PK |
| name | VARCHAR(64) | UNIQUE, NOT NULL (e.g. admin, manager, developer) |
| description | TEXT | |
| created_at | TIMESTAMPTZ | |

**permissions**
| Column | Type | Constraints |
|-------------|--------------|-------------|
| id | UUID / bigint| PK |
| code | VARCHAR(64) | UNIQUE, NOT NULL (e.g. clients:read, projects:write) |
| description | TEXT | |

**user_roles** (many-to-many: users ↔ roles)
| Column | Type | Constraints |
|----------|--------|--------------------|
| user_id | FK | → users.id, NOT NULL |
| role_id | FK | → roles.id, NOT NULL |
| (PK) | (user_id, role_id) | |

**role_permissions** (many-to-many: roles ↔ permissions)
| Column | Type | Constraints |
|---------------|------|------------------------|
| role_id | FK | → roles.id, NOT NULL |
| permission_id | FK | → permissions.id, NOT NULL |
| (PK) | (role_id, permission_id) | |

---

### 3.2 Clients & Projects

**clients**
| Column | Type | Constraints |
|------------|--------------|-------------|
| id | UUID / bigint| PK |
| name | VARCHAR(255) | NOT NULL |
| contact_email | VARCHAR(255) | |
| contact_phone | VARCHAR(64) | |
| address | TEXT | |
| created_by | FK | → users.id |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |
| deleted_at | TIMESTAMPTZ | NULLABLE (soft delete) |

**projects**
| Column | Type | Constraints |
|-------------|--------------|-------------|
| id | UUID / bigint| PK |
| client_id | FK | → clients.id, NOT NULL |
| name | VARCHAR(255) | NOT NULL |
| description | TEXT | |
| status | VARCHAR(32) | e.g. draft, active, on_hold, completed |
| start_date | DATE | |
| end_date | DATE | |
| owner_id | FK | → users.id |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |
| deleted_at | TIMESTAMPTZ | NULLABLE |

**project_members** (optional: many-to-many projects ↔ users)
| Column | Type | Constraints |
|-----------|------|----------------|
| project_id| FK | → projects.id |
| user_id | FK | → users.id |
| role | VARCHAR(32) | e.g. lead, member |
| (PK) | (project_id, user_id) | |

---

### 3.3 Tasks

**tasks**
| Column | Type | Constraints |
|-------------|--------------|-------------|
| id | UUID / bigint| PK |
| project_id | FK | → projects.id, NOT NULL |
| title | VARCHAR(255) | NOT NULL |
| description | TEXT | |
| status | VARCHAR(32) | e.g. todo, in_progress, review, done |
| priority | VARCHAR(16) | e.g. low, medium, high |
| assignee_id | FK | → users.id, NULLABLE |
| due_date | DATE | |
| order_index | INT | for ordering in UI |
| created_by | FK | → users.id |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

---

### 3.4 Meetings

**meetings**
| Column | Type | Constraints |
|-------------|--------------|-------------|
| id | UUID / bigint| PK |
| project_id | FK | → projects.id, NULLABLE (can be general) |
| title | VARCHAR(255) | NOT NULL |
| description | TEXT | |
| start_at | TIMESTAMPTZ | NOT NULL |
| end_at | TIMESTAMPTZ | NOT NULL |
| location | VARCHAR(255) | or link for remote |
| created_by | FK | → users.id |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**meeting_attendees**
| Column | Type | Constraints |
|-----------|------|----------------|
| meeting_id| FK | → meetings.id |
| user_id | FK | → users.id |
| (PK) | (meeting_id, user_id) | |

---

### 3.5 Finance

**invoices**
| Column | Type | Constraints |
|-------------|--------------|-------------|
| id | UUID / bigint| PK |
| client_id | FK | → clients.id, NOT NULL |
| project_id | FK | → projects.id, NULLABLE |
| number | VARCHAR(64) | UNIQUE, NOT NULL |
| amount | DECIMAL(14,2)| NOT NULL |
| currency | CHAR(3) | DEFAULT e.g. USD |
| status | VARCHAR(32) | e.g. draft, sent, paid, overdue |
| due_date | DATE | |
| issued_at | DATE | |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | |

**payments**
| Column | Type | Constraints |
|-------------|--------------|-------------|
| id | UUID / bigint| PK |
| invoice_id | FK | → invoices.id, NOT NULL |
| amount | DECIMAL(14,2)| NOT NULL |
| paid_at | DATE | NOT NULL |
| reference | VARCHAR(255) | |
| created_at | TIMESTAMPTZ | |

**expenses**
| Column | Type | Constraints |
|-------------|--------------|-------------|
| id | UUID / bigint| PK |
| project_id | FK | → projects.id, NULLABLE |
| description | VARCHAR(255) | NOT NULL |
| amount | DECIMAL(14,2)| NOT NULL |
| currency | CHAR(3) | |
| expense_date| DATE | |
| created_by | FK | → users.id |
| created_at | TIMESTAMPTZ | |

---

## 4. Indexes (Recommendations)

- `users`: index on `email`.
- `clients`: index on `created_by`, `deleted_at`.
- `projects`: index on `client_id`, `status`, `owner_id`, `deleted_at`.
- `tasks`: index on `project_id`, `assignee_id`, `status`, `due_date`.
- `meetings`: index on `project_id`, `start_at`.
- `invoices`: index on `client_id`, `status`, `due_date`.
- **Refresh tokens** (if stored in DB): table with `user_id`, `token_hash`, `expires_at`; index on `token_hash`, `expires_at`.

## 5. Migrations

- Use **Alembic** for all schema changes.
- One logical change per migration (e.g. “add meetings table”, “add role_permissions”).
- No direct DDL in application code.

---

_Generated by Architect Agent. Backend agent implements models and migrations per this schema._
