import { useEffect, useState } from "react";
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

export default function TeamActivity() {
  const { hasPermission } = useAuth();
  const isAdmin = hasPermission("admin:all");
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [activity, setActivity] = useState<ActivityLogWithUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterReportId, setFilterReportId] = useState<string | null>(null);
  const [filterEntityType, setFilterEntityType] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [reportsList, activityList] = await Promise.all([
        listMyReports(),
        listTeamActivity({
          report_id: filterReportId || undefined,
          entity_type: filterEntityType || undefined,
          limit: 200,
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
  }, [filterReportId, filterEntityType]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-white">Team activity</h1>
      </div>
      <p className="text-slate-400 text-sm mb-4">
        {isAdmin
          ? "Audit log of all user actions (create, update, delete). Viewing or opening a page does not generate logs."
          : "Activity of team members who report to you. Only create, update, and delete actions are logged; viewing does not."}
      </p>

      {loading ? (
        <p className="text-slate-400">Loading...</p>
      ) : !isAdmin && reports.length === 0 ? (
        <div className="rounded-xl border border-slate-700 p-6 text-center text-slate-400">
          You have no direct reports, or you don’t have permission to view team activity. Assign team members a
          manager in Admin → Users.
        </div>
      ) : (
        <>
          <div className="flex flex-wrap gap-2 mb-4 items-center">
            <span className="text-slate-400 text-sm mr-2">User:</span>
            <button
              onClick={() => setFilterReportId(null)}
              className={`px-3 py-1.5 rounded-lg text-sm ${filterReportId === null ? "bg-primary text-white" : "bg-slate-700 text-slate-300 hover:bg-slate-600"}`}
            >
              All
            </button>
            {reports.map((r) => (
              <button
                key={r.id}
                onClick={() => setFilterReportId(r.id)}
                className={`px-3 py-1.5 rounded-lg text-sm ${filterReportId === r.id ? "bg-primary text-white" : "bg-slate-700 text-slate-300 hover:bg-slate-600"}`}
              >
                {r.full_name || r.email}
              </button>
            ))}
            <span className="text-slate-400 text-sm ml-4 mr-2">Entity:</span>
            <button
              onClick={() => setFilterEntityType(null)}
              className={`px-3 py-1.5 rounded-lg text-sm ${filterEntityType === null ? "bg-primary text-white" : "bg-slate-700 text-slate-300 hover:bg-slate-600"}`}
            >
              All
            </button>
            {Object.entries(ENTITY_LABELS).map(([value, label]) => (
              <button
                key={value}
                onClick={() => setFilterEntityType(value)}
                className={`px-3 py-1.5 rounded-lg text-sm ${filterEntityType === value ? "bg-primary text-white" : "bg-slate-700 text-slate-300 hover:bg-slate-600"}`}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="rounded-xl border border-slate-700 overflow-hidden">
            <table className="w-full">
              <thead className="bg-slate-800 text-left text-sm text-slate-400">
                <tr>
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">User</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Entity</th>
                  <th className="px-4 py-3">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {activity.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center text-slate-500">
                      No audit entries yet. Create, update, or delete tasks, leads, projects, clients, meetings,
                      invoices, or other items to see them here.
                    </td>
                  </tr>
                ) : (
                  activity.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-800/50">
                      <td className="px-4 py-3 text-slate-400 text-sm whitespace-nowrap">
                        {formatDate(log.created_at)}
                      </td>
                      <td className="px-4 py-3 text-slate-300">
                        {log.user_full_name || log.user_email}
                      </td>
                      <td className="px-4 py-3 text-slate-300">
                        {ACTION_LABELS[log.action] || log.action}
                      </td>
                      <td className="px-4 py-3 text-slate-300">
                        {ENTITY_LABELS[log.entity_type] || log.entity_type}
                      </td>
                      <td className="px-4 py-3 text-slate-300">{log.details || "—"}</td>
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
