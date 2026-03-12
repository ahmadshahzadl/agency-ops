import { useEffect, useState } from "react";
import { listTasks, createTask, updateTask, deleteTask, type Task } from "@/api/tasks";
import { listProjectNames } from "@/api/projects";
import { listAssignableUsers, type UserList } from "@/api/users";
import { SearchableUserSelect } from "@/components/SearchableUserSelect";
import { useAuth } from "@/store/auth";
import { NotesSection } from "@/components/NotesSection";

export default function TasksPage() {
  const [items, setItems] = useState<Task[]>([]);
  const [projectNames, setProjectNames] = useState<{ id: string; name: string }[]>([]);
  const [assignableUsers, setAssignableUsers] = useState<UserList[]>([]);
  const [loading, setLoading] = useState(true);
  const [projectFilter, setProjectFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [assigneeFilter, setAssigneeFilter] = useState<string>("");
  const [searchText, setSearchText] = useState("");
  const [priorityFilter, setPriorityFilter] = useState<string>("");
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
    const params: { project_id?: string; status_filter?: string; assignee_id?: string } = {};
    if (projectFilter) params.project_id = projectFilter;
    if (statusFilter) params.status_filter = statusFilter;
    if (assigneeFilter) params.assignee_id = assigneeFilter;
    listTasks(Object.keys(params).length ? params : undefined)
      .then(setItems)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [projectFilter, statusFilter, assigneeFilter]);

  useEffect(() => {
    const onTasksUpdated = () => load();
    window.addEventListener("ws:tasks_updated", onTasksUpdated);
    return () => window.removeEventListener("ws:tasks_updated", onTasksUpdated);
  }, [projectFilter, statusFilter, assigneeFilter]);

  useEffect(() => {
    listAssignableUsers().then(setAssignableUsers).catch(() => []);
  }, []);

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
  const searchLower = searchText.trim().toLowerCase();
  const filteredItems = items.filter((t) => {
    if (searchLower && !(t.title ?? "").toLowerCase().includes(searchLower) && !(t.description ?? "").toLowerCase().includes(searchLower))
      return false;
    if (priorityFilter && t.priority !== priorityFilter) return false;
    return true;
  });
  const inputClass = "w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";

  const taskStatusOptions = ["todo", "in_progress", "review", "done"];
  const taskPriorityOptions = ["low", "medium", "high"];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <label className="text-sm font-medium text-gray-700">Project</label>
          <select
            value={projectFilter}
            onChange={(e) => setProjectFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[160px]"
          >
            <option value="">All projects</option>
            {projectNames.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <label className="text-sm font-medium text-gray-700">Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[120px]"
          >
            <option value="">All statuses</option>
            {taskStatusOptions.map((s) => (
              <option key={s} value={s}>{s.replace("_", " ")}</option>
            ))}
          </select>
          <label className="text-sm font-medium text-gray-700">Priority</label>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[100px]"
          >
            <option value="">All</option>
            {taskPriorityOptions.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
          <label className="text-sm font-medium text-gray-700">Assignee</label>
          <select
            value={assigneeFilter}
            onChange={(e) => setAssigneeFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[160px]"
          >
            <option value="">All assignees</option>
            {assignableUsers.map((u) => (
              <option key={u.id} value={u.id}>{u.full_name || u.email}</option>
            ))}
          </select>
          <label className="text-sm font-medium text-gray-700">Search</label>
          <input
            type="search"
            placeholder="Title or description..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[180px]"
          />
        </div>
        {canWrite && (
          <button
            onClick={openNew}
            className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover shadow-sm"
          >
            Add task
          </button>
        )}
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600">
              <tr>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Project</th>
                <th className="px-4 py-3">Assignee</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Priority</th>
                {canWrite && <th className="px-4 py-3 w-24 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredItems.map((t) => (
                <tr key={t.id} className="hover:bg-gray-50/80">
                  <td className="px-4 py-3 font-medium text-gray-900">{t.title}</td>
                  <td className="px-4 py-3 text-gray-600">{t.project_id ? (projectMap[t.project_id] ?? "—") : "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{t.assignee_id ? (assigneeMap[t.assignee_id] ?? "—") : "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{t.status}</td>
                  <td className="px-4 py-3 text-gray-600">{t.priority}</td>
                  {canWrite && (
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button type="button" onClick={() => openEdit(t)} title="Edit" className="p-1.5 rounded-lg text-gray-500 hover:text-primary hover:bg-gray-100 transition-colors">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                        {canManageTasks && (
                          <button type="button" onClick={() => remove(t.id)} title="Delete" className="p-1.5 rounded-lg text-gray-500 hover:text-red-600 hover:bg-gray-100 transition-colors">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-10" onClick={() => setModal(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">{modal === "new" ? "New task" : "Edit task"}</h2>
            <div className="space-y-3">
              {(modal === "new" || canManageTasks) && (
                <input
                  placeholder="Title *"
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  className={`${inputClass} placeholder-gray-500`}
                  required
                />
              )}
              {(modal === "new" || canManageTasks) && (
                <div>
                  <label className={labelClass}>Assign to</label>
                  <SearchableUserSelect
                    users={assignableUsers}
                    value={form.assignee_id}
                    onChange={(id) => setForm((f) => ({ ...f, assignee_id: id }))}
                    placeholder="Search and select user..."
                    variant="light"
                  />
                </div>
              )}
              <textarea
                placeholder="Description"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                className={`${inputClass} placeholder-gray-500`}
                rows={2}
              />
              <div className="grid grid-cols-2 gap-2">
                <select value={form.status} onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))} className={inputClass}>
                  <option value="todo">Todo</option>
                  <option value="in_progress">In progress</option>
                  <option value="review">Review</option>
                  <option value="done">Done</option>
                </select>
                <select value={form.priority} onChange={(e) => setForm((f) => ({ ...f, priority: e.target.value }))} className={inputClass}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
              <input type="date" value={form.due_date} onChange={(e) => setForm((f) => ({ ...f, due_date: e.target.value }))} className={inputClass} />
            </div>
            <NotesSection entityType="task" entityId={modal !== "new" ? (modal as Task).id : undefined} />
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">Cancel</button>
              <button onClick={save} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
