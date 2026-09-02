import { useCallback, useEffect, useState } from "react";
import {
  listMilestones, createMilestone, completeMilestone, reopenMilestone, deleteMilestone,
  type Milestone,
} from "@/api/milestones";
import { useAuth } from "@/store/auth";

const STATE_STYLES: Record<string, string> = {
  upcoming: "bg-gray-100 text-gray-600",
  overdue: "bg-red-100 text-red-600",
  completed: "bg-green-100 text-green-700",
};

export function MilestonesSection({ projectId, className = "" }: { projectId: string | undefined; className?: string }) {
  const { user, hasPermission } = useAuth();
  const canManage = hasPermission("admin:all") || !!user?.can_manage_tasks;
  const [items, setItems] = useState<Milestone[]>([]);
  const [name, setName] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!projectId) return;
    listMilestones(projectId).then(setItems).catch(() => setItems([]));
  }, [projectId]);

  useEffect(() => { refresh(); }, [refresh]);

  if (!projectId) return null;

  const showError = (msg: string) => {
    setError(msg);
    window.setTimeout(() => setError(null), 4000);
  };

  const act = (fn: () => Promise<unknown>) =>
    fn().then(refresh).catch((e) => showError(e instanceof Error ? e.message : "Failed"));

  return (
    <div className={`mt-4 ${className}`}>
      <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-400">Milestones</h4>
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
      <ul className="mt-2 space-y-1.5">
        {items.map((m) => (
          <li key={m.id} className="rounded-lg border border-gray-200 dark:border-gray-600 px-3 py-2">
            <div className="flex items-center gap-2">
              <span className={`text-sm ${m.state === "completed" ? "line-through text-gray-400" : "text-gray-800 dark:text-gray-100"} font-medium`}>{m.name}</span>
              <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${STATE_STYLES[m.state]}`}>{m.state}</span>
              {m.due_date && <span className="text-[11px] text-gray-400">due {m.due_date}</span>}
              <span className="ml-auto text-[11px] text-gray-400">{m.task_done}/{m.task_total} tasks</span>
              {canManage && (
                <>
                  {m.state === "completed" ? (
                    <button onClick={() => act(() => reopenMilestone(m.id))} className="text-[11px] font-medium text-gray-400 hover:text-primary">reopen</button>
                  ) : (
                    <button onClick={() => act(() => completeMilestone(m.id))} className="text-[11px] font-medium text-green-600 hover:underline">complete</button>
                  )}
                  <button onClick={() => act(() => deleteMilestone(m.id))} className="text-[11px] font-medium text-red-400 hover:text-red-600">✕</button>
                </>
              )}
            </div>
            {m.task_total > 0 && (
              <div className="mt-1.5 h-1.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                <div className="h-full bg-primary rounded-full" style={{ width: `${Math.round((m.task_done / m.task_total) * 100)}%` }} />
              </div>
            )}
          </li>
        ))}
        {items.length === 0 && <li className="text-xs text-gray-400 py-1">No milestones yet.</li>}
      </ul>
      {canManage && (
        <div className="mt-2 flex gap-2">
          <input
            placeholder="New milestone (e.g. Phase 1: Design)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="flex-1 px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
          <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} className="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm" />
          <button
            disabled={!name.trim()}
            onClick={() => act(async () => {
              await createMilestone(projectId, { name: name.trim(), due_date: dueDate || null });
              setName("");
              setDueDate("");
            })}
            className="px-3 py-1.5 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50"
          >
            Add
          </button>
        </div>
      )}
    </div>
  );
}
