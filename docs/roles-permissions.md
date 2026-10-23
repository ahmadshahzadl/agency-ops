# Roles and permissions

What a super admin can assign, and what each grant actually unlocks.

Sources of truth:

- Permission codes and the seeded roles: `backend/scripts/seed_db.py` (`PERMISSIONS`, `ROLE_PERMISSIONS`)
- Enforcement: `require_permission(...)` / `require_any_permission(...)` / `require_admin` in `backend/app/api/v1/*.py`, defined in `backend/app/api/deps.py`
- Sidebar visibility: `navItems` in `frontend/src/layouts/Layout.tsx`
- Human labels shown in the Roles screen: `frontend/src/lib/permissionCatalog.ts`

## How access is decided

1. **Super admin (god mode).** The account whose email matches `SUPER_ADMIN_EMAIL` in config gets `admin:all` synthetically and is never written to the activity log. It does not need a role.
2. **Roles → permissions.** Everyone else gets the union of the permission codes of every role they hold. Multiple roles per user are supported and additive.
3. **`admin:all` is a wildcard.** Every check passes if the user holds it. Users, Teams, Roles and Booking pages have no finer-grained code, so `admin:all` is the only way in.
4. **Row-level scoping is separate from permissions.** Even with `leads:read`, what a user sees is narrowed by: manager (sees own + direct reports), team membership, the `sales` role (own records only), or portal link.
5. **Portal accounts** are users with a `client_id`. They are locked out of the internal app regardless of permissions.

## Roles seeded by `seed_db.py`

| Role | Description | Permissions |
|---|---|---|
| `admin` | Full system access | all 38 |
| `manager` | Team-scoped access; no finance, no expenses, no user/team/role management | 27 |
| `employee` | Assigned tasks/projects/meetings only | 13 |
| `member` | Same as `employee`, kept for backward compatibility | 13 |
| `qa` | Employee access plus approving/failing tasks in review | 13 |
| `solutions_engineer` | Sees and claims website bookings and leads, manages assigned prospects | 17 |
| `client` | External client-portal user, portal access only | 0 |

Roles are plain database rows: a super admin can create any additional role (e.g. `designer`, `accountant`) on the Roles screen and pick the codes by hand. A role cannot be deleted while a user still holds it.

### `sales` is special-cased in code but not seeded

`backend/app/api/deps.py` (`get_is_sales_member`, `get_sales_team_user_ids`) and `frontend/src/layouts/Layout.tsx` (`SALES_HIDDEN_NAV`, `SALES_ONLY_HIDDEN_NAV`) both branch on a role literally named `sales`:

- a user with role `sales` and no direct reports is restricted to their own leads, tasks and meetings, plus unassigned new leads;
- Invoices, Expenses, Payroll and Reports are hidden from the sidebar for anyone with role `sales`;
- Clients and Team activity are additionally hidden when `sales` is their only non-manager role.

No role named `sales` is created by `seed_db.py`, so this behaviour only applies once someone creates that role by hand with exactly that name.

## Role → permission matrix

`•` = granted.

| Permission | admin | manager | employee / member | qa | solutions_engineer | client |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| `admin:all` | • | | | | | |
| `dashboard:read` | • | • | • | • | • | |
| `leads:read` | • | • | • | | • | |
| `leads:write` | • | • | | | • | |
| `clients:read` | • | • | | | • | |
| `clients:write` | • | • | | | | |
| `projects:read` | • | • | • | • | • | |
| `projects:write` | • | • | | | | |
| `tasks:read` | • | • | • | • | • | |
| `tasks:write` | • | • | • | • | | |
| `tasks:qa_approve` | • | | | • | | |
| `meetings:read` | • | • | • | • | • | |
| `meetings:write` | • | • | | | • | |
| `quotes:read` | • | • | | | • | |
| `quotes:write` | • | • | | | | |
| `agreements:read` | • | • | | | | |
| `agreements:write` | • | • | | | | |
| `letters:read` | • | • | | | | |
| `letters:write` | • | • | | | | |
| `finance:read` | • | | | | | |
| `finance:write` | • | | | | | |
| `expenses:read` | • | | | | | |
| `expenses:write` | • | | | | | |
| `analytics:read` | • | • | | | | |
| `team_activity:read` | • | • | | | | |
| `time:read` | • | • | • | • | • | |
| `time:write` | • | • | • | • | • | |
| `notes:read` | • | • | • | • | • | |
| `notes:write` | • | • | • | • | • | |
| `attachments:read` | • | • | • | • | • | |
| `attachments:write` | • | • | • | • | • | |
| `announcements:read` | • | • | • | • | • | |
| `announcements:write` | • | | | | | |
| `credentials:read` | • | | | | | |
| `credentials:write` | • | | | | | |
| `bookings:manage` | • | | | | • | |
| `content:manage` | • | • | | | | |
| `attendance:manage` | • | | | | | |

## Page-wise permissions

The permission in **Opens the page** is what the sidebar link checks. Everything else is enforced inside the page or by its API calls.

| Page | Route | Opens the page | Also used on this page |
|---|---|---|---|
| Overview | `/dashboard` | always visible | `dashboard:read` fills it |
| Leads | `/leads` | `leads:read` | `leads:write`, `notes:*`, `attachments:*` |
| Quotes | `/quotes` | `quotes:read` | `quotes:write`; **`finance:write`** to convert a quote to an invoice |
| Agreements | `/agreements` | `agreements:read` | `agreements:write` |
| Letters | `/letters` | `letters:read` | `letters:write` |
| Customers | `/clients` | `clients:read` | `clients:write`, `notes:*`, `attachments:*` |
| Projects | `/projects`, `/projects/:id` | `projects:read` **or** `dashboard:read` | `projects:write` (incl. milestones, share links), `credentials:*`, `notes:*`, `attachments:*` |
| Tasks | `/tasks` | `tasks:read` | `tasks:write`, `tasks:qa_approve` |
| Boards | `/boards` | `tasks:read` | `tasks:write` to move cards, **`projects:write`** to manage columns, `tasks:qa_approve` |
| Timesheet | `/timesheet` | `time:read` | `time:write`; `finance:read`/`finance:write` to see and invoice logged time |
| Attendance | `/attendance` | always visible (own check-in/out) | `attendance:manage` for the team board, summary and corrections |
| Meetings | `/meetings` | `meetings:read` | `meetings:write`; `bookings:manage` (or `admin:all`) for inbound website bookings |
| Booking pages | `/booking` | `admin:all` | — |
| Website content | `/content` | `content:manage` | — |
| Messages | `/messages` | always visible (internal users only) | — |
| Invoices | `/invoices` | `finance:read` | `finance:write` |
| Expenses | `/expenses` | `expenses:read` | `expenses:write`; `admin:all` to run recurring-bill reminders |
| Payroll | `/payroll` | `expenses:read` | `expenses:write` |
| Reports | `/analytics` | `analytics:read` | endpoint also accepts `dashboard:read`; QA tiles need `tasks:qa_approve` |
| Team activity | `/team-activity` | `team_activity:read` | — |
| Announcements | `/announcements` | `announcements:read` | posting/editing/deleting requires `admin:all` |
| Users | `/users` | `admin:all` | `tasks:write` or `meetings:write` can read the assignable-user list (names only) |
| Teams | `/teams` | `admin:all` | — |
| Roles | `/roles` | `admin:all` | — |
| Settings | `/profile` | always visible | — |
| Client portal | `/portal` | account linked to a client | not permission-driven |

### Sidebar each seeded role gets

- **admin** — everything.
- **manager** — Overview, Leads, Quotes, Agreements, Letters, Customers, Projects, Tasks, Boards, Timesheet, Attendance, Meetings, Website content, Messages, Reports, Team activity, Announcements. *No* Invoices, Expenses, Payroll, Booking pages, Users, Teams, Roles.
- **employee / member** — Overview, Leads, Projects, Tasks, Boards, Timesheet, Attendance, Meetings, Messages, Announcements.
- **qa** — same as employee minus Leads, plus the QA approve/fail action on tasks in review.
- **solutions_engineer** — Overview, Leads, Quotes, Customers, Projects, Tasks, Boards, Timesheet, Attendance, Meetings, Messages, Announcements, plus inbound bookings inside Meetings.
- **client** — nothing internal; redirected to `/portal`.

## Things worth knowing before granting

- **`expenses:read` exposes salaries.** Payroll shares the expenses codes, so anyone who can read expenses can read every salary. There is no separate payroll permission.
- **`credentials:read` / `credentials:write`** are the client's live hosting, server and third-party logins. Seeded to admin only on purpose.
- **`announcements:write` is currently inert.** The code exists and can be granted, but create/edit/delete in `backend/app/api/v1/announcements.py` use `require_admin`, so only `admin:all` can actually post.
- **`dashboard:read` is wider than it looks.** It is accepted in place of `projects:read` on the project list and in place of `analytics:read` on the reports endpoint, so a role holding only `dashboard:read` can still read reports through the API even though the sidebar link stays hidden.
- **`admin:all` cannot be split.** Users, Teams, Roles and Booking pages have no finer-grained code, so there is no "can manage users but not finance" role without adding new permission codes.
