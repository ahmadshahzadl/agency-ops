import { useEffect, useState } from "react";
import { listTasks, createTask, updateTask, deleteTask, type Task } from "@/api/tasks";
import { listProjects, type Project } from "@/api/projects";
import { useAuth } from "@/store/auth";

export default function TasksPage() {
  const [items, setItems] = useState<Task[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [projectFilter, setProjectFilter] = useState<string>("");
  const [modal, setModal] = useState<"new" | Task | null>(null);
  const [form, setForm] = useState({
    project_id: "",
    title: "",
    description: "",
    status: "todo",
    priority: "medium",
    due_date: "",
  });
  const { hasPermission } = useAuth();

  const load = () => {
    listProjects().then(setProjects);
    listTasks(projectFilter ? { project_id: projectFilter } : undefined)
      .then(setItems)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [projectFilter]);

  const openNew = () => {
    setForm({
      project_id: projects[0]?.id || "",
      title: "",
      description: "",
      status: "todo",
      priority: "medium",
      due_date: "",
    });
    setModal("new");
  };
  const openEdit = (t: Task) => {
    setForm({
      project_id: t.project_id,
      title: t.title,
      description: t.description || "",
      status: t.status,
      priority: t.priority,
      due_date: t.due_date || "",
    });
    setModal(t);
  };

  const save = async () => {
    if (modal === null) return;
    const payload = {
      project_id: form.project_id,
      title: form.title,
      description: form.description || null,
      status: form.status,
      priority: form.priority,
      due_date: form.due_date || null,
    };
    try {
      if (modal === "new") {
        await createTask(payload as Task);
      } else {
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

  const canWrite = hasPermission("tasks:write");
  const projectMap = Object.fromEntries(projects.map((p) => [p.id, p.name]));

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
          {projects.map((p) => (
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
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Priority</th>
                {canWrite && <th className="px-4 py-3 w-24"></th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {items.map((t) => (
                <tr key={t.id} className="hover:bg-slate-800/50">
                  <td className="px-4 py-3 text-white">{t.title}</td>
                  <td className="px-4 py-3 text-slate-300">{projectMap[t.project_id] || t.project_id}</td>
                  <td className="px-4 py-3 text-slate-300">{t.status}</td>
                  <td className="px-4 py-3 text-slate-300">{t.priority}</td>
                  {canWrite && (
                    <td className="px-4 py-3">
                      <button onClick={() => openEdit(t)} className="text-primary hover:underline mr-2">
                        Edit
                      </button>
                      <button onClick={() => remove(t.id)} className="text-red-400 hover:underline">
                        Delete
                      </button>
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
              <div>
                <label className="block text-sm text-slate-400 mb-1">Project</label>
                <select
                  value={form.project_id}
                  onChange={(e) => setForm((f) => ({ ...f, project_id: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <input
                placeholder="Title"
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
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
