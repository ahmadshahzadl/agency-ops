import { useEffect, useState } from "react";
import { listTasks, createTask, updateTask, deleteTask, type Task } from "@/api/tasks";
import { listProjectNames } from "@/api/projects";
import { listAssignableUsers, type UserList } from "@/api/users";
import { SearchableUserSelect } from "@/components/SearchableUserSelect";
import { useAuth } from "@/store/auth";

export default function TasksPage() {
  const [items, setItems] = useState<Task[]>([]);
  const [projectNames, setProjectNames] = useState<{ id: string; name: string }[]>([]);
  const [assignableUsers, setAssignableUsers] = useState<UserList[]>([]);
  const [loading, setLoading] = useState(true);
  const [projectFilter, setProjectFilter] = useState<string>("");
  const [modal, setModal] = useState<"new" | Task | null>(null);
  const [form, setForm] = useState({
    title: "",
    description: "",
    status: "todo",
    priority: "medium",
    due_date: "",
    assignee_id: "" as string | null,
  });
  const { user, hasPermission } = useAuth();

  const canWrite = hasPermission("tasks:write");
  const canManageTasks = user?.can_manage_tasks ?? false;

  const load = () => {
    listProjectNames().then(setProjectNames).catch(() => setProjectNames([]));
    listTasks(projectFilter ? { project_id: projectFilter } : undefined)
      .then(setItems)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [projectFilter]);

  useEffect(() => {
    if (canWrite) listAssignableUsers().then(setAssignableUsers).catch(() => {});
  }, [canWrite]);

  const openNew = () => {
    setForm({
      title: "",
      description: "",
      status: "todo",
      priority: "medium",
      due_date: "",
      assignee_id: user?.id ?? null,
    });
    setModal("new");
  };
  const openEdit = (t: Task) => {
    setForm({
      title: t.title,
      description: t.description || "",
      status: t.status,
      priority: t.priority,
      due_date: t.due_date || "",
      assignee_id: t.assignee_id || null,
    });
    setModal(t);
  };

  const save = async () => {
    if (modal === null) return;
    if (modal === "new" && !form.title?.trim()) {
      alert("Please enter a title.");
      return;
    }
    try {
      if (modal === "new") {
        const payload: Record<string, unknown> = {
          project_id: null,
          title: form.title,
          description: form.description || null,
          status: form.status,
          priority: form.priority,
          due_date: form.due_date || null,
        };
        if (canManageTasks) payload.assignee_id = form.assignee_id || null;
        else payload.assignee_id = user?.id ?? null;
        await createTask(payload as Parameters<typeof createTask>[0]);
      } else {
        const payload = canManageTasks
          ? {
              title: form.title,
              description: form.description || null,
              status: form.status,
              priority: form.priority,
              due_date: form.due_date || null,
              assignee_id: form.assignee_id,
            }
          : { status: form.status, description: form.description || null, priority: form.priority, due_date: form.due_date || null };
        await updateTask(modal.id, payload);
      }
      setModal(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Delete this task?")) return;
    try {
      await deleteTask(id);
      setModal(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const projectMap = Object.fromEntries(projectNames.map((p) => [p.id, p.name]));
  const assigneeMap = Object.fromEntries(assignableUsers.map((u) => [u.id, u.full_name || u.email]));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-white">Tasks</h1>
        {canWrite && (
          <button
            onClick={openNew}
            className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover"
          >
            Add task
          </button>
        )}
      </div>

      <div className="mb-4">
        <select
          value={projectFilter}
          onChange={(e) => setProjectFilter(e.target.value)}
          className="px-3 py-2 rounded-lg bg-slate-800 border border-slate-600 text-white"
        >
          <option value="">All projects</option>
          {projectNames.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <p className="text-slate-400">Loading...</p>
      ) : (
        <div className="rounded-xl border border-slate-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-800 text-left text-sm text-slate-400">
              <tr>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Project</th>
                <th className="px-4 py-3">Assignee</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Priority</th>
                {canWrite && <th className="px-4 py-3 w-24"></th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {items.map((t) => (
                <tr key={t.id} className="hover:bg-slate-800/50">
                  <td className="px-4 py-3 text-white">{t.title}</td>
                  <td className="px-4 py-3 text-slate-300">{t.project_id ? (projectMap[t.project_id] ?? "—") : "—"}</td>
                  <td className="px-4 py-3 text-slate-300">{t.assignee_id ? (assigneeMap[t.assignee_id] ?? "—") : "—"}</td>
                  <td className="px-4 py-3 text-slate-300">{t.status}</td>
                  <td className="px-4 py-3 text-slate-300">{t.priority}</td>
                  {canWrite && (
                    <td className="px-4 py-3">
                      <button onClick={() => openEdit(t)} className="text-primary hover:underline mr-2">
                        Edit
                      </button>
                      {canManageTasks && (
                        <button onClick={() => remove(t.id)} className="text-red-400 hover:underline">
                          Delete
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-10" onClick={() => setModal(null)}>
          <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-white mb-4">{modal === "new" ? "New task" : "Edit task"}</h2>
            <div className="space-y-3">
              {(modal === "new" || canManageTasks) && (
                <input
                  placeholder="Title *"
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                  required
                />
              )}
              {(modal === "new" || canManageTasks) && (
                <div>
                  <label className="block text-sm text-slate-400 mb-1">Assign to</label>
                  <SearchableUserSelect
                    users={assignableUsers}
                    value={form.assignee_id}
                    onChange={(id) => setForm((f) => ({ ...f, assignee_id: id }))}
                    placeholder="Search and select user..."
                  />
                </div>
              )}
              <textarea
                placeholder="Description"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                rows={2}
              />
              <div className="grid grid-cols-2 gap-2">
                <select
                  value={form.status}
                  onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
                  className="px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                >
                  <option value="todo">Todo</option>
                  <option value="in_progress">In progress</option>
                  <option value="review">Review</option>
                  <option value="done">Done</option>
                </select>
                <select
                  value={form.priority}
                  onChange={(e) => setForm((f) => ({ ...f, priority: e.target.value }))}
                  className="px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
              <input
                type="date"
                value={form.due_date}
                onChange={(e) => setForm((f) => ({ ...f, due_date: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-slate-400 hover:text-white">
                Cancel
              </button>
              <button onClick={save} className="px-4 py-2 rounded-lg bg-primary text-white font-medium">
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
