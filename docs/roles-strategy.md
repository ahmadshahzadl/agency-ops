# Roles & Permissions Strategy

This document describes the permission model and role strategy for the office software (software house / agency use case).

**Primary reference:** [Roles, Permissions, and Page Access Flow](./roles-permissions-flow.md) — defines the three primary roles (Admin, Manager, Employee), page access matrix, team-based visibility, and financial rules.

---

## 1. Permission model (what exists)

Permissions follow `resource:action`. The backend and UI use these codes.

| Permission | Controls |
|------------|----------|
| **admin:all** | Full access: Users, Teams, Roles, Announcements; no scope limits; required for bulk actions on most pages. |
| **dashboard:read** | (Legacy) Dashboard/Overview is now visible to all; this can still be used to show e.g. Projects link to users who don’t have projects:read. |
| **leads:read** / **leads:write** | Leads list, create, edit, delete, convert. |
| **clients:read** / **clients:write** | Clients list and CRUD. |
| **projects:read** / **projects:write** | Projects list and CRUD. |
| **tasks:read** / **tasks:write** | Tasks list and CRUD. |
| **meetings:read** / **meetings:write** | Meetings list and CRUD. |
| **finance:read** / **finance:write** | Invoices (Manager can view team invoices with finance:read only). |
| **expenses:read** / **expenses:write** | Expenses (Admin only; Manager and Employee have no access). |
| **analytics:read** | Reports (Analytics) page. |
| **team_activity:read** | Team activity feed (managers see their reports’ activity). |
| **notes:read** / **notes:write** | Notes on entities (clients, projects, etc.). |
| **announcements:read** / **announcements:write** | View announcements (Manager, Employee); create/edit/delete (Admin). |

**Special behavior (no extra permission):**

- **Manager** role + user has “reports” (direct reports) → can manage tasks/leads for their team; team activity is scoped to reports.
- **Sales** role → sidebar hides Invoices, Expenses, Analytics; “sales only” also hides Clients and Team activity (see `Layout.tsx`).
- **Super admin** (one email in config) → gets full access and is excluded from activity logs.

---

## 2. Recommended role strategy

Use **few roles, clear names, and consistent permission bundles** so that:

- Onboarding is simple (“give them the Member role”).
- Auditing is easy (“only Admin and Manager have team_activity:read”).
- You can add more roles later by reusing the same permissions.

### 2.1 Core roles (keep these)

| Role | Purpose | Strategy |
|------|---------|----------|
| **Admin** | Full system control: users, teams, roles, announcements, all data, bulk actions. | Single role with `admin:all`. No second “super admin” role needed if you use the config-based super admin for one ghost account. |
| **Manager** | Run operations and people: same data access as Member, plus team activity and ability to assign/oversee tasks and leads for their reports. | All module permissions except `admin:all`; include `team_activity:read`. Assign to users who have direct reports. |
| **Member** | Default for staff who do client/project/task work. | Same as Manager but without `team_activity:read`. Full read/write on leads, clients, projects, tasks, meetings, finance, analytics, notes. |
| **Viewer** | Read-only: contractors, auditors, or temporary observers. | Only `*:read` (and notes:read). No write permissions. |
| **Sales** | Focus on leads and meetings; optional tasks. | Leads + meetings (read/write), projects (read), tasks (read/write), notes (read/write). No clients, finance, or analytics. Layout already hides Invoices/Expenses/Analytics (and for “sales only”, Clients and Team activity). |

These five cover: full admin, people managers, standard staff, read-only, and sales.

### 2.2 Optional roles (add if you need them)

Add only if you have a real need; otherwise stick to the five above.

| Role | Permissions (in addition to dashboard) | Use case |
|------|----------------------------------------|----------|
| **Accountant** | finance:read, finance:write, clients:read, projects:read, analytics:read, notes:read | Finance-only users who need invoices/expenses and context (clients, projects) but not leads/tasks/meetings management. |
| **Project lead** | projects:read, projects:write, tasks:read, tasks:write, clients:read, meetings:read, meetings:write, notes:read, notes:write | Delivery leads who run projects and tasks but don’t need leads or finance. |
| **Support** | clients:read, projects:read, tasks:read, notes:read, notes:write | Support staff who view context and add notes only. |

If you add these, create them in the **Roles** UI (or extend `backend/scripts/seed_db.py`) and assign the same permission codes the backend already uses.

---

## 3. Best practices

1. **Prefer one primary role per user**  
   The app supports multiple roles per user; for clarity, assign one main role (e.g. Member or Manager) and use a second role only for exceptions (e.g. Viewer + a custom “Accountant” role).

2. **Use Manager only for people with reports**  
   `team_activity:read` and “can manage tasks/leads for team” are meaningful when the user has direct reports. Avoid giving Manager to everyone.

3. **Keep Viewer strictly read-only**  
   Give only `*:read` and `notes:read` so Viewers cannot change data.

4. **Sales = minimal CRM + meetings**  
   Sales role is already tailored (leads, meetings, tasks, projects read, notes). Use it for sales staff who shouldn’t see clients list or finance.

5. **Admin and super admin**  
   - **Admin** = normal admin role with `admin:all`; actions are logged.  
   - **Super admin** = single email in env; full access and excluded from activity logs. Use for a single “god mode” account only.

6. **Add new roles via permissions**  
   Don’t hardcode new permission checks in the backend. Create a new role in the Roles UI, assign existing permissions (e.g. `finance:read`, `finance:write`), and the current API will already enforce them.

---

## 4. Quick reference: role → permissions (seed-style)

```text
admin:        admin:all (all permissions)
manager:      dashboard:read, leads, clients, projects, tasks, meetings,
              finance, analytics, team_activity:read, notes
member:       same as manager but no team_activity:read
viewer:       dashboard:read, leads:read, clients:read, projects:read,
              tasks:read, meetings:read, finance:read, analytics:read, notes:read
sales:        dashboard:read, leads (r/w), projects:read, meetings (r/w),
              tasks (r/w), notes (r/w)
```

Optional (if you add them):

```text
accountant:   dashboard:read, finance (r/w), clients:read, projects:read,
              analytics:read, notes:read
project_lead: dashboard:read, projects (r/w), tasks (r/w), clients:read,
              meetings (r/w), notes (r/w)
support:      dashboard:read, clients:read, projects:read, tasks:read,
              notes (r/w)
```

---

## 5. Where roles are configured

- **Backend:** Permissions are enforced in `app/api/deps.py` and in each API module (`require_permission`, `require_any_permission`, `require_admin`). Role–permission mapping is in the database (Roles UI or seed).
- **Seed script:** `backend/scripts/seed_db.py` defines `PERMISSIONS` and `ROLE_PERMISSIONS` for the five core roles. Run after migrations to create/update permissions and role–permission links.
- **Frontend:** Sidebar visibility and feature flags use the same permission codes (e.g. `hasPermission("admin:all")`, `hasPermission("finance:read")`). No separate role list is required in the frontend; permissions are enough.

This strategy keeps roles few and clear, uses the existing permission set, and scales by adding new roles with existing permissions rather than new code.
