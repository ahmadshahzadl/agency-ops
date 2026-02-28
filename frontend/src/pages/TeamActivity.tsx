import { useEffect, useState } from "react";
import { listMyReports, listTeamActivity, type ReportSummary, type ActivityLogWithUser } from "@/api/team_activity";

const ACTION_LABELS: Record<string, string> = {
  task_created: "Created task",
  task_updated: "Updated task",
  task_completed: "Completed task",
  task_deleted: "Deleted task",
  project_created: "Created project",
  project_updated: "Updated project",
  client_created: "Created client",
  client_updated: "Updated client",
  meeting_created: "Created meeting",
  meeting_updated: "Updated meeting",
};

function formatDate(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  if (sameDay) return d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function TeamActivity() {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [activity, setActivity] = useState<ActivityLogWithUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterReportId, setFilterReportId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [reportsList, activityList] = await Promise.all([
        listMyReports(),
        listTeamActivity({ report_id: filterReportId || undefined, limit: 100 }),
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
  }, [filterReportId]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-white">Team activity</h1>
      </div>
      <p className="text-slate-400 text-sm mb-4">
        Activity and progress of team members who report to you. Use the filter to see one person’s activity.
      </p>

      {loading ? (
        <p className="text-slate-400">Loading...</p>
      ) : reports.length === 0 ? (
        <div className="rounded-xl border border-slate-700 p-6 text-center text-slate-400">
          You have no direct reports, or you don’t have permission to view team activity. Assign team members a
          manager in Admin → Users.
        </div>
      ) : (
        <>
          <div className="flex flex-wrap gap-2 mb-4">
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
          </div>

          <div className="rounded-xl border border-slate-700 overflow-hidden">
            <table className="w-full">
              <thead className="bg-slate-800 text-left text-sm text-slate-400">
                <tr>
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Member</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700">
                {activity.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                      No activity yet. When your reports create or update tasks, projects, clients, or meetings, it will
                      appear here.
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
