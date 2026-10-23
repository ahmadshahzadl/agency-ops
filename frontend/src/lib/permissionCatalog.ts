/**
 * Page-wise map of permission codes -> what they actually unlock in the app.
 *
 * Source of truth for the codes themselves is backend/scripts/seed_db.py (PERMISSIONS)
 * and the require_permission(...) guards in backend/app/api/v1/*.py. This file only adds
 * human labels and the page each code belongs to, so the Roles screen can show a super
 * admin what a role will be able to open instead of a flat list of raw codes.
 *
 * Any permission that exists in the database but is not listed here still shows up in
 * the picker, under the "Other permissions" group.
 */

export interface CatalogPermission {
  code: string;
  /** Short label for the checkbox. */
  label: string;
  /** One line on what the code actually allows. */
  detail: string;
  /** Grants that let the holder change data (shown with a write badge). */
  write?: boolean;
  /** Shown with a warning badge: sensitive or app-wide. */
  sensitive?: boolean;
}

export interface CatalogPage {
  /** Page / screen name as it reads in the sidebar or header. */
  page: string;
  /** Route in the app, or null for things that live inside another page. */
  route: string | null;
  /**
   * Permission the sidebar link checks (see navItems in layouts/Layout.tsx).
   * null = every signed-in staff user sees the link.
   */
  navGate: string | null;
  /** Extra context for the super admin. */
  note?: string;
  permissions: CatalogPermission[];
}

export const PERMISSION_CATALOG: CatalogPage[] = [
  {
    page: "Full access",
    route: null,
    navGate: null,
    note: "admin:all satisfies every permission check in the app, so it also unlocks Users, Teams, Roles and Booking pages, which have no finer-grained code.",
    permissions: [
      {
        code: "admin:all",
        label: "Administrator (everything)",
        detail: "Passes every permission check: all pages plus Users, Teams, Roles, Booking pages and recurring-expense reminders.",
        write: true,
        sensitive: true,
      },
    ],
  },
  {
    page: "Overview (Dashboard)",
    route: "/dashboard",
    navGate: null,
    note: "The sidebar link is always visible; dashboard:read is what fills it. It also works as a fallback read for Projects and Reports.",
    permissions: [
      {
        code: "dashboard:read",
        label: "Open the dashboard",
        detail: "Dashboard widgets and counters. Also accepted in place of projects:read (project list) and analytics:read (reports).",
      },
    ],
  },
  {
    page: "Leads",
    route: "/leads",
    navGate: "leads:read",
    note: "Visibility inside the page is scoped: a user with the 'sales' role and no direct reports sees only their own leads plus unassigned new ones; managers also see their reports' leads.",
    permissions: [
      { code: "leads:read", label: "View leads", detail: "Lead list, lead detail drawer, pipeline stages and logged interactions." },
      { code: "leads:write", label: "Create / edit leads", detail: "Add leads, change stage, assign, log interactions, convert to client.", write: true },
    ],
  },
  {
    page: "Quotes",
    route: "/quotes",
    navGate: "quotes:read",
    permissions: [
      { code: "quotes:read", label: "View quotes", detail: "Quote list, line items and PDF preview." },
      { code: "quotes:write", label: "Create / edit quotes", detail: "Draft, send, accept and reject quotes.", write: true },
      { code: "finance:write", label: "Convert quote to invoice", detail: "The 'create invoice from quote' action is gated on finance:write, not quotes:write.", write: true },
    ],
  },
  {
    page: "Agreements",
    route: "/agreements",
    navGate: "agreements:read",
    permissions: [
      { code: "agreements:read", label: "View agreements", detail: "Agreement list, types, generated documents and signing status." },
      { code: "agreements:write", label: "Create / send agreements", detail: "Draft agreements, issue signing links and void them.", write: true },
    ],
  },
  {
    page: "Letters",
    route: "/letters",
    navGate: "letters:read",
    permissions: [
      { code: "letters:read", label: "View letters", detail: "Letter list and generated letter PDFs." },
      { code: "letters:write", label: "Create / edit letters", detail: "Write, regenerate and delete letters.", write: true },
    ],
  },
  {
    page: "Customers (Clients)",
    route: "/clients",
    navGate: "clients:read",
    note: "Hidden from the sidebar for sales-only users even when clients:read is granted.",
    permissions: [
      { code: "clients:read", label: "View clients", detail: "Client list and client detail, including linked projects." },
      { code: "clients:write", label: "Create / edit clients", detail: "Add and edit clients, assign teams, archive.", write: true },
    ],
  },
  {
    page: "Projects",
    route: "/projects",
    navGate: "projects:read",
    note: "The sidebar link also appears with dashboard:read alone. Project detail additionally uses the notes, attachments and credentials permissions.",
    permissions: [
      { code: "projects:read", label: "View projects", detail: "Project list, project detail, milestones and progress." },
      { code: "projects:write", label: "Create / edit projects", detail: "Create and edit projects, milestones, board columns and public share links.", write: true },
    ],
  },
  {
    page: "Tasks",
    route: "/tasks",
    navGate: "tasks:read",
    permissions: [
      { code: "tasks:read", label: "View tasks", detail: "Task list and task detail (scoped to own / team / reports)." },
      { code: "tasks:write", label: "Create / edit tasks", detail: "Create, assign and move tasks through the workflow.", write: true },
      {
        code: "tasks:qa_approve",
        label: "Approve or fail QA",
        detail: "Only holders can move a task out of 'review' to done or QA-failed, and they see the QA tiles in Reports.",
        write: true,
      },
    ],
  },
  {
    page: "Boards",
    route: "/boards",
    navGate: "tasks:read",
    permissions: [
      { code: "tasks:read", label: "View boards", detail: "Open the kanban boards and their cards." },
      { code: "tasks:write", label: "Move cards", detail: "Drag tasks between columns and edit them from the board.", write: true },
      { code: "projects:write", label: "Manage board columns", detail: "Create, rename, reorder and delete board columns.", write: true },
    ],
  },
  {
    page: "Timesheet",
    route: "/timesheet",
    navGate: "time:read",
    permissions: [
      { code: "time:read", label: "View time entries", detail: "Own timesheet and summary; managers also see their reports' entries." },
      { code: "time:write", label: "Log / edit time", detail: "Add, edit and delete time entries.", write: true },
      { code: "finance:read", label: "See invoiced time", detail: "Open the time entries behind an invoice." },
      { code: "finance:write", label: "Invoice logged time", detail: "Turn time entries into an invoice.", write: true },
    ],
  },
  {
    page: "Attendance",
    route: "/attendance",
    navGate: null,
    note: "The link is visible to every staff user: without attendance:manage they only get their own check-in / check-out.",
    permissions: [
      {
        code: "attendance:manage",
        label: "Manage everyone's attendance",
        detail: "Today's board for the whole team, the attendance summary, and correcting or deleting records.",
        write: true,
      },
    ],
  },
  {
    page: "Meetings",
    route: "/meetings",
    navGate: "meetings:read",
    permissions: [
      { code: "meetings:read", label: "View meetings", detail: "Meeting list and detail (own / team / reports)." },
      { code: "meetings:write", label: "Create / edit meetings", detail: "Schedule, reschedule and cancel meetings.", write: true },
      {
        code: "bookings:manage",
        label: "See and claim inbound bookings",
        detail: "Every booking that comes in from the website, and assigning it to a solutions engineer.",
        write: true,
      },
    ],
  },
  {
    page: "Booking pages",
    route: "/booking",
    navGate: "admin:all",
    note: "Admin-only: there is no finer-grained code for configuring booking pages and availability.",
    permissions: [
      {
        code: "admin:all",
        label: "Configure booking pages",
        detail: "Create and edit booking pages, slots, availability and assignment rules.",
        write: true,
        sensitive: true,
      },
    ],
  },
  {
    page: "Website content",
    route: "/content",
    navGate: "content:manage",
    permissions: [
      {
        code: "content:manage",
        label: "Manage website content",
        detail: "Write, edit, publish and delete blog posts and case studies, and upload media to the public site.",
        write: true,
      },
    ],
  },
  {
    page: "Messages",
    route: "/messages",
    navGate: null,
    note: "Login-gated only: every internal user can use Messages. Client-portal accounts cannot.",
    permissions: [],
  },
  {
    page: "Invoices",
    route: "/invoices",
    navGate: "finance:read",
    note: "Hidden from the sidebar for users with the 'sales' role.",
    permissions: [
      { code: "finance:read", label: "View invoices", detail: "Invoice list, detail, PDFs and recorded payments." },
      {
        code: "finance:write",
        label: "Create / send invoices, record payments",
        detail: "Create and edit invoices, email them, record payments, delete drafts.",
        write: true,
        sensitive: true,
      },
    ],
  },
  {
    page: "Expenses",
    route: "/expenses",
    navGate: "expenses:read",
    note: "Hidden from the sidebar for the 'sales' role. Also covers recurring bills and subscriptions.",
    permissions: [
      { code: "expenses:read", label: "View expenses", detail: "Expense list, categories, recurring bills and their payment history." },
      {
        code: "expenses:write",
        label: "Create / edit expenses",
        detail: "Add and edit expenses and recurring bills, mark them paid or skipped.",
        write: true,
        sensitive: true,
      },
      { code: "admin:all", label: "Run recurring-bill reminders", detail: "Trigger the recurring-expense reminder job by hand.", write: true, sensitive: true },
    ],
  },
  {
    page: "Payroll",
    route: "/payroll",
    navGate: "expenses:read",
    note: "Shares the expenses:* codes, so anyone who can read expenses can read salaries. Hidden from the sidebar for the 'sales' role.",
    permissions: [
      { code: "expenses:read", label: "View payroll", detail: "Salary rows per user, employment type and payment status.", sensitive: true },
      { code: "expenses:write", label: "Edit payroll / pay salaries", detail: "Set salaries and record a salary as paid.", write: true, sensitive: true },
    ],
  },
  {
    page: "Reports (Analytics)",
    route: "/analytics",
    navGate: "analytics:read",
    note: "The endpoint also accepts dashboard:read, so a user holding only dashboard:read can still read reports through the API even though the sidebar link is hidden. Hidden from the sidebar for the 'sales' role.",
    permissions: [
      { code: "analytics:read", label: "View reports", detail: "Lead, project, task, time and finance analytics. QA tiles need tasks:qa_approve." },
    ],
  },
  {
    page: "Team activity",
    route: "/team-activity",
    navGate: "team_activity:read",
    note: "Hidden from the sidebar for sales-only users.",
    permissions: [
      { code: "team_activity:read", label: "View team activity", detail: "The activity feed of who did what across the workspace." },
    ],
  },
  {
    page: "Announcements",
    route: "/announcements",
    navGate: "announcements:read",
    permissions: [
      { code: "announcements:read", label: "Read announcements", detail: "See announcements posted to the workspace." },
      {
        code: "announcements:write",
        label: "Post announcements",
        detail: "Reserved for posting announcements, but create / edit / delete currently require admin:all, so granting this alone has no effect yet.",
        write: true,
      },
    ],
  },
  {
    page: "Users",
    route: "/users",
    navGate: "admin:all",
    note: "Admin-only. Non-admins can still look up colleagues for assignment if they hold tasks:write or meetings:write.",
    permissions: [
      {
        code: "admin:all",
        label: "Manage users",
        detail: "Create, edit and deactivate users, set roles, teams, managers and employment details.",
        write: true,
        sensitive: true,
      },
      { code: "tasks:write", label: "Pick users for assignment", detail: "Read the assignable-user list (names only) when assigning tasks." },
      { code: "meetings:write", label: "Pick users for meetings", detail: "Read the assignable-user list (names only) when inviting to meetings." },
    ],
  },
  {
    page: "Teams",
    route: "/teams",
    navGate: "admin:all",
    permissions: [
      { code: "admin:all", label: "Manage teams", detail: "Create and edit teams, team types and membership.", write: true, sensitive: true },
    ],
  },
  {
    page: "Roles",
    route: "/roles",
    navGate: "admin:all",
    note: "This screen. Only admin:all holders can see or change roles and permissions.",
    permissions: [
      {
        code: "admin:all",
        label: "Manage roles and permissions",
        detail: "Create, edit, duplicate and delete roles, and grant permissions to them.",
        write: true,
        sensitive: true,
      },
    ],
  },
  {
    page: "Notes (on leads, clients, projects, tasks)",
    route: null,
    navGate: null,
    note: "Not a page of its own: the notes panel appears inside lead, client, project and task detail.",
    permissions: [
      { code: "notes:read", label: "Read notes", detail: "See notes attached to a record." },
      { code: "notes:write", label: "Write notes", detail: "Add, edit and delete own notes.", write: true },
    ],
  },
  {
    page: "Attachments (files on records)",
    route: null,
    navGate: null,
    note: "Not a page of its own: the attachments panel appears inside lead, client, project and task detail.",
    permissions: [
      { code: "attachments:read", label: "View / download files", detail: "List and download files attached to a record." },
      { code: "attachments:write", label: "Upload / delete files", detail: "Attach files to a record and remove them.", write: true },
    ],
  },
  {
    page: "Credentials vault (inside Project detail)",
    route: null,
    navGate: null,
    note: "Seeded to admin only. Grant deliberately: these are the client's live server, hosting and third-party logins.",
    permissions: [
      { code: "credentials:read", label: "View stored credentials", detail: "Read the saved logins and secrets on a project.", sensitive: true },
      { code: "credentials:write", label: "Add / edit credentials", detail: "Store, edit and delete project credentials.", write: true, sensitive: true },
    ],
  },
  {
    page: "Settings (own profile)",
    route: "/profile",
    navGate: null,
    note: "Login-gated only: every user can edit their own profile, password, signature and theme.",
    permissions: [],
  },
  {
    page: "Client portal",
    route: "/portal",
    navGate: null,
    note: "Not permission-driven: an account is a portal account when it is linked to a client. Portal accounts are locked out of the internal app, so give them the 'client' role and no permissions.",
    permissions: [],
  },
];

/** code -> every page that uses it (one code can unlock parts of several pages). */
export const PAGES_BY_PERMISSION: Record<string, string[]> = (() => {
  const map: Record<string, string[]> = {};
  for (const page of PERMISSION_CATALOG) {
    for (const perm of page.permissions) {
      if (!map[perm.code]) map[perm.code] = [];
      if (!map[perm.code].includes(page.page)) map[perm.code].push(page.page);
    }
  }
  return map;
})();

/** First catalog entry for a code, for labels outside the page-wise view. */
export function permissionInfo(code: string): CatalogPermission | undefined {
  for (const page of PERMISSION_CATALOG) {
    const hit = page.permissions.find((p) => p.code === code);
    if (hit) return hit;
  }
  return undefined;
}

/** Sidebar pages a role holding these codes will actually see (mirrors navItems in Layout.tsx). */
export function visiblePagesFor(codes: Set<string>): string[] {
  const isAdmin = codes.has("admin:all");
  const has = (code: string) => isAdmin || codes.has(code);
  return PERMISSION_CATALOG.filter((p) => {
    if (p.page === "Full access") return false;
    if (p.route === null || p.route === "/portal" || p.route === "/profile") return false;
    if (p.navGate === null) return true;
    if (p.navGate === "projects:read") return has("projects:read") || has("dashboard:read");
    return has(p.navGate);
  }).map((p) => p.page);
}
