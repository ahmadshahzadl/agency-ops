import { useEffect, useMemo, useState } from "react";
import { listMyReports, listTeamActivity, type ReportSummary, type ActivityLogWithUser } from "@/api/team_activity";
import { useAuth } from "@/store/auth";

const ACTION_LABELS: Record<string, string> = {
  task_created: "Created task",
  task_updated: "Updated task",
  task_completed: "Completed task",
  task_deleted: "Deleted task",
  project_created: "Created project",
  project_updated: "Updated project",
  project_deleted: "Deleted project",
  client_created: "Created client",
  client_updated: "Updated client",
  client_deleted: "Deleted client",
  meeting_created: "Created meeting",
  meeting_updated: "Updated meeting",
  meeting_deleted: "Deleted meeting",
  lead_created: "Created lead",
  lead_updated: "Updated lead",
  lead_converted: "Converted lead",
  lead_deleted: "Deleted lead",
  invoice_created: "Created invoice",
  invoice_updated: "Updated invoice",
  invoice_deleted: "Deleted invoice",
  payment_created: "Recorded payment",
  expense_created: "Created expense",
  expense_updated: "Updated expense",
  expense_deleted: "Deleted expense",
  announcement_created: "Created announcement",
  announcement_updated: "Updated announcement",
  announcement_deleted: "Deleted announcement",
  user_created: "Created user",
  user_updated: "Updated user",
  user_deleted: "Deleted user",
  profile_updated: "Updated profile",
};

const ENTITY_LABELS: Record<string, string> = {
  task: "Task",
  project: "Project",
  client: "Client",
  meeting: "Meeting",
  lead: "Lead",
  invoice: "Invoice",
  payment: "Payment",
  expense: "Expense",
  announcement: "Announcement",
  user: "User",
  profile: "Profile",
};

function formatDate(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  if (sameDay) return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function matchesSearch(log: ActivityLogWithUser, searchLower: string, actionLabels: Record<string, string>, entityLabels: Record<string, string>): boolean {
  if (!searchLower) return true;
  const user = (log.user_full_name || log.user_email || "").toLowerCase();
  const action = (actionLabels[log.action] || log.action).toLowerCase();
  const entity = (entityLabels[log.entity_type] || log.entity_type).toLowerCase();
  const details = (log.details || "").toLowerCase();
  return user.includes(searchLower) || action.includes(searchLower) || entity.includes(searchLower) || details.includes(searchLower);
}

function startOfDay(dateStr: string): Date {
  const d = new Date(dateStr + "T00:00:00");
  return isNaN(d.getTime()) ? new Date(0) : d;
}

function endOfDay(dateStr: string): Date {
  const d = new Date(dateStr + "T23:59:59.999");
  return isNaN(d.getTime()) ? new Date(8640000000000000) : d;
}

const selectClass = "px-3 py-2 rounded-lg border border-gray-300 text-gray-900 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary min-w-[140px]";

export default function TeamActivity() {
  const { hasPermission } = useAuth();
  const isAdmin = hasPermission("admin:all");
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [activity, setActivity] = useState<ActivityLogWithUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterReportId, setFilterReportId] = useState<string | null>(null);
  const [filterEntityType, setFilterEntityType] = useState<string | null>(null);
  const [filterAction, setFilterAction] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");
  const [datePreset, setDatePreset] = useState<"" | "24h" | "7d" | "30d">("");

  const load = async () => {
    setLoading(true);
    try {
      const [reportsList, activityList] = await Promise.all([
        listMyReports(),
        listTeamActivity({
          report_id: filterReportId || undefined,
          entity_type: filterEntityType || undefined,
          action: filterAction || undefined,
          limit: 300,
        }),
      ]);
      setReports(reportsList);
      setActivity(activityList);
    } catch (e) {
      console.error(e);
      setReports([]);
      setActivity([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [filterReportId, filterEntityType, filterAction]);

  const searchLower = search.trim().toLowerCase();

  const filteredActivity = useMemo(() => {
    let list = activity;
    if (searchLower) list = list.filter((log) => matchesSearch(log, searchLower, ACTION_LABELS, ENTITY_LABELS));
    if (datePreset === "24h") {
      const cutoff = Date.now() - 24 * 60 * 60 * 1000;
      list = list.filter((log) => new Date(log.created_at).getTime() >= cutoff);
    } else if (datePreset === "7d") {
      const cutoff = Date.now() - 7 * 24 * 60 * 60 * 1000;
      list = list.filter((log) => new Date(log.created_at).getTime() >= cutoff);
    } else if (datePreset === "30d") {
      const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000;
      list = list.filter((log) => new Date(log.created_at).getTime() >= cutoff);
    } else {
      if (dateFrom) list = list.filter((log) => new Date(log.created_at).getTime() >= startOfDay(dateFrom).getTime());
      if (dateTo) list = list.filter((log) => new Date(log.created_at).getTime() <= endOfDay(dateTo).getTime());
    }
    return list;
  }, [activity, searchLower, dateFrom, dateTo, datePreset]);

  return (
    <div>
      <p className="text-gray-600 text-sm mb-4">
        {isAdmin
          ? "Audit log of all user actions (create, update, delete). Viewing or opening a page does not generate logs."
          : "Activity of team members who report to you. Only create, update, and delete actions are logged; viewing does not."}
      </p>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : !isAdmin && reports.length === 0 ? (
        <div className="rounded-xl bg-white border border-gray-200 p-6 text-center text-gray-600">
          You have no direct reports, or you don’t have permission to view team activity. Assign team members a
          manager in Admin → Users.
        </div>
      ) : (
        <>
          <div className="rounded-xl bg-white border border-gray-100 shadow-sm p-5 mb-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">
              {isAdmin ? "Users" : "Your team members"}
            </h2>
            <p className="text-sm text-gray-600 mb-3">
              {isAdmin
                ? "All active users (admins see everyone). Filter activity by user below."
                : "Employees and members who report to you. You can filter their activity below."}
            </p>
            <ul className="flex flex-wrap gap-3">
              {reports.length === 0 ? (
                <li className="text-gray-500 text-sm">No users</li>
              ) : (
                reports.map((r) => (
                  <li
                    key={r.id}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-gray-50 border border-gray-100 text-gray-800"
                  >
                    <span className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-semibold text-sm">
                      {(r.full_name || r.email || "?").charAt(0).toUpperCase()}
                    </span>
                    <div>
                      <span className="font-medium text-gray-900">{r.full_name || "—"}</span>
                      <span className="text-gray-500 text-sm block">{r.email}</span>
                    </div>
                  </li>
                ))
              )}
            </ul>
          </div>

          <div className="rounded-xl bg-white border border-gray-100 shadow-sm p-4 mb-4 space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative flex-1 min-w-[200px] max-w-sm">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </span>
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search user, action, entity, details..."
                  className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
              </div>
              <div className="flex items-center gap-2">
                <label htmlFor="user-filter" className="text-sm font-medium text-gray-700 whitespace-nowrap">User</label>
                <select
                  id="user-filter"
                  value={filterReportId ?? ""}
                  onChange={(e) => setFilterReportId(e.target.value || null)}
                  className={selectClass}
                >
                  <option value="">All users</option>
                  {reports.map((r) => (
                    <option key={r.id} value={r.id}>{r.full_name || r.email}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2">
                <label htmlFor="entity-filter" className="text-sm font-medium text-gray-700 whitespace-nowrap">Entity</label>
                <select
                  id="entity-filter"
                  value={filterEntityType ?? ""}
                  onChange={(e) => setFilterEntityType(e.target.value || null)}
                  className={selectClass}
                >
                  <option value="">All entities</option>
                  {Object.entries(ENTITY_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2">
                <label htmlFor="action-filter" className="text-sm font-medium text-gray-700 whitespace-nowrap">Action</label>
                <select
                  id="action-filter"
                  value={filterAction ?? ""}
                  onChange={(e) => setFilterAction(e.target.value || null)}
                  className={selectClass}
                >
                  <option value="">All actions</option>
                  {Object.entries(ACTION_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-gray-100">
              <span className="text-sm font-medium text-gray-700">Date range</span>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => { setDatePreset("24h"); setDateFrom(""); setDateTo(""); }}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${datePreset === "24h" ? "bg-primary text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}
                >
                  Last 24 hours
                </button>
                <button
                  type="button"
                  onClick={() => { setDatePreset("7d"); setDateFrom(""); setDateTo(""); }}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${datePreset === "7d" ? "bg-primary text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}
                >
                  Last 7 days
                </button>
                <button
                  type="button"
                  onClick={() => { setDatePreset("30d"); setDateFrom(""); setDateTo(""); }}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${datePreset === "30d" ? "bg-primary text-white" : "bg-gray-100 text-gray-700 hover:bg-gray-200"}`}
                >
                  Last 30 days
                </button>
                <button
                  type="button"
                  onClick={() => { setDatePreset(""); setDateFrom(""); setDateTo(""); }}
                  className="px-3 py-1.5 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100"
                >
                  Clear
                </button>
              </div>
              <span className="text-gray-400 text-sm">or</span>
              <div className="flex items-center gap-2">
                <label htmlFor="date-from" className="text-sm text-gray-600">From</label>
                <input
                  id="date-from"
                  type="date"
                  value={dateFrom}
                  onChange={(e) => { setDateFrom(e.target.value); setDatePreset(""); }}
                  className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
                <label htmlFor="date-to" className="text-sm text-gray-600">To</label>
                <input
                  id="date-to"
                  type="date"
                  value={dateTo}
                  onChange={(e) => { setDateTo(e.target.value); setDatePreset(""); }}
                  className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary"
                />
              </div>
            </div>
          </div>

          <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600">
                <tr>
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">User</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Entity</th>
                  <th className="px-4 py-3">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredActivity.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                      {searchLower || datePreset || dateFrom || dateTo
                        ? "No entries match your filters. Try different filters or clear search and date range."
                        : "No audit entries yet. Create, update, or delete tasks, leads, projects, clients, meetings, invoices, or other items to see them here."}
                    </td>
                  </tr>
                ) : (
                  filteredActivity.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50/80">
                      <td className="px-4 py-3 text-gray-500 text-sm whitespace-nowrap">
                        {formatDate(log.created_at)}
                      </td>
                      <td className="px-4 py-3 text-gray-900 font-medium">
                        {log.user_full_name || log.user_email}
                      </td>
                      <td className="px-4 py-3 text-gray-700">
                        {ACTION_LABELS[log.action] || log.action}
                      </td>
                      <td className="px-4 py-3 text-gray-600">
                        {ENTITY_LABELS[log.entity_type] || log.entity_type}
                      </td>
                      <td className="px-4 py-3 text-gray-600">{log.details || "—"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
