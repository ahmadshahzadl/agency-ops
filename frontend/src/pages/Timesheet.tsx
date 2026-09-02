import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/store/auth";
import { listProjectNames } from "@/api/projects";
import { listTasks, type Task } from "@/api/tasks";
import { listTimeEntries, createTimeEntry, deleteTimeEntry, getTimeSummary, type TimeEntry, type TimeSummary } from "@/api/time";

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

function weekAgo(): string {
  const d = new Date();
  d.setDate(d.getDate() - 30);
  return d.toISOString().slice(0, 10);
}

export default function Timesheet() {
  const { user, hasPermission } = useAuth();
  const isAdmin = hasPermission("admin:all");
  const canSeeOthers = isAdmin || !!user?.can_manage_tasks;

  const [projects, setProjects] = useState<{ id: string; name: string }[]>([]);
  const [entries, setEntries] = useState<TimeEntry[]>([]);
  const [summary, setSummary] = useState<TimeSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [filterProject, setFilterProject] = useState("");
  const [dateFrom, setDateFrom] = useState(weekAgo());
  const [dateTo, setDateTo] = useState(today());

  // Log form
  const [form, setForm] = useState({ project_id: "", task_id: "", work_date: today(), hours: "", description: "", billable: true });
  const [projectTasks, setProjectTasks] = useState<Task[]>([]);
  const [busy, setBusy] = useState(false);

  const showError = (msg: string) => {
    setError(msg);
    window.setTimeout(() => setError(null), 4000);
  };

  useEffect(() => {
    listProjectNames({ limit: 500 }).then((p) => {
      setProjects(p);
      setForm((f) => (f.project_id ? f : { ...f, project_id: p[0]?.id ?? "" }));
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!form.project_id) { setProjectTasks([]); return; }
    listTasks({ project_id: form.project_id, limit: 100 }).then(setProjectTasks).catch(() => setProjectTasks([]));
  }, [form.project_id]);

  const refresh = useCallback(() => {
    const params = {
      project_id: filterProject || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      limit: 500,
    };
    listTimeEntries(params).then(setEntries).catch(() => setEntries([]));
    getTimeSummary(params).then(setSummary).catch(() => setSummary(null));
  }, [filterProject, dateFrom, dateTo]);

  useEffect(() => { refresh(); }, [refresh]);

  const logTime = async () => {
    if (!form.project_id || !form.hours) return;
    setBusy(true);
    try {
      await createTimeEntry({
        project_id: form.project_id,
        task_id: form.task_id || null,
        work_date: form.work_date,
        hours: Number(form.hours),
        description: form.description || undefined,
        billable: form.billable,
      });
      setForm((f) => ({ ...f, hours: "", description: "" }));
      refresh();
    } catch (e) {
      showError(e instanceof Error ? e.message : "Could not log time");
    } finally {
      setBusy(false);
    }
  };

  const inputClass = "px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm";

  return (
    <div className="space-y-5">
      {error && <div className="rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-2.5">{error}</div>}

      {/* Log time */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">Log time</h3>
        <div className="flex flex-wrap items-center gap-2">
          <select className={`${inputClass} min-w-[180px]`} value={form.project_id} onChange={(e) => setForm((f) => ({ ...f, project_id: e.target.value, task_id: "" }))}>
            {projects.length === 0 && <option value="">No projects</option>}
            {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <select className={`${inputClass} min-w-[160px]`} value={form.task_id} onChange={(e) => setForm((f) => ({ ...f, task_id: e.target.value }))}>
            <option value="">No task</option>
            {projectTasks.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}
          </select>
          <input type="date" className={inputClass} value={form.work_date} onChange={(e) => setForm((f) => ({ ...f, work_date: e.target.value }))} />
          <input type="number" min="0.25" max="24" step="0.25" placeholder="Hours" className={`${inputClass} w-24`} value={form.hours} onChange={(e) => setForm((f) => ({ ...f, hours: e.target.value }))} />
          <input placeholder="What did you work on?" className={`${inputClass} flex-1 min-w-[180px]`} value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
          <label className="flex items-center gap-1.5 text-sm text-gray-600 dark:text-gray-300">
            <input type="checkbox" checked={form.billable} onChange={(e) => setForm((f) => ({ ...f, billable: e.target.checked }))} className="rounded border-gray-300 text-primary focus:ring-primary/20" />
            Billable
          </label>
          <button onClick={logTime} disabled={busy || !form.project_id || !form.hours} className="px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50">
            {busy ? "Saving…" : "Log"}
          </button>
        </div>
      </div>

      {/* Summary + filters */}
      <div className="flex flex-wrap items-center gap-3">
        <select className={inputClass} value={filterProject} onChange={(e) => setFilterProject(e.target.value)}>
          <option value="">All projects</option>
          {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <input type="date" className={inputClass} value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
        <span className="text-gray-400 text-sm">→</span>
        <input type="date" className={inputClass} value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
        {summary && (
          <div className="ml-auto flex items-center gap-4 text-sm">
            <span className="text-gray-500 dark:text-gray-400">Total <b className="text-gray-800 dark:text-gray-100">{Number(summary.total_hours)}h</b></span>
            <span className="text-gray-500 dark:text-gray-400">Billable <b className="text-gray-800 dark:text-gray-100">{Number(summary.billable_hours)}h</b></span>
            <span className="text-gray-500 dark:text-gray-400">Unbilled <b className="text-gray-800 dark:text-gray-100">{Number(summary.unbilled_billable_hours)}h</b></span>
            {canSeeOthers && Number(summary.unbilled_amount) > 0 && (
              <span className="text-gray-500 dark:text-gray-400">Unbilled value <b className="text-primary">{Number(summary.unbilled_amount).toFixed(2)}</b></span>
            )}
          </div>
        )}
      </div>

      {/* Entries */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-gray-400 border-b border-gray-100 dark:border-gray-700">
              <th className="px-4 py-2.5">Date</th>
              {canSeeOthers && <th className="px-4 py-2.5">Who</th>}
              <th className="px-4 py-2.5">Project</th>
              <th className="px-4 py-2.5">Task</th>
              <th className="px-4 py-2.5">Description</th>
              <th className="px-4 py-2.5 text-right">Hours</th>
              <th className="px-4 py-2.5"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50 dark:divide-gray-700">
            {entries.map((e) => (
              <tr key={e.id} className="text-gray-700 dark:text-gray-200">
                <td className="px-4 py-2.5 whitespace-nowrap">{e.work_date}</td>
                {canSeeOthers && <td className="px-4 py-2.5 whitespace-nowrap">{e.user_name}</td>}
                <td className="px-4 py-2.5">{e.project_name}</td>
                <td className="px-4 py-2.5 text-gray-500">{e.task_title ?? "—"}</td>
                <td className="px-4 py-2.5 text-gray-500 max-w-[280px] truncate" title={e.description ?? ""}>{e.description ?? "—"}</td>
                <td className="px-4 py-2.5 text-right font-medium">
                  {Number(e.hours)}h
                  {!e.billable && <span className="ml-1.5 text-[10px] text-gray-400">(non-billable)</span>}
                </td>
                <td className="px-4 py-2.5 text-right whitespace-nowrap">
                  {e.invoice_id ? (
                    <span className="text-[11px] text-green-600 font-medium" title="Billed on an invoice — locked">billed 🔒</span>
                  ) : (
                    <button
                      onClick={async () => {
                        try {
                          await deleteTimeEntry(e.id);
                          refresh();
                        } catch (err) { showError(err instanceof Error ? err.message : "Delete failed"); }
                      }}
                      className="text-xs font-medium text-red-400 hover:text-red-600"
                    >
                      ✕
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {entries.length === 0 && (
              <tr><td colSpan={canSeeOthers ? 7 : 6} className="px-4 py-6 text-center text-gray-400">No time entries in this range.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
