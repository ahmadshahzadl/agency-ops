import { useEffect, useState } from "react";
import { listMeetings, createMeeting, updateMeeting, deleteMeeting, type Meeting } from "@/api/meetings";
import { listProjectNames } from "@/api/projects";
import { listAssignableUsers, type UserList } from "@/api/users";
import { SearchableUserMultiSelect } from "@/components/SearchableUserMultiSelect";
import { useAuth } from "@/store/auth";
import { NotesSection } from "@/components/NotesSection";

export default function MeetingsPage() {
  const [items, setItems] = useState<Meeting[]>([]);
  const [projectNames, setProjectNames] = useState<{ id: string; name: string }[]>([]);
  const [assignableUsers, setAssignableUsers] = useState<UserList[]>([]);
  const [loading, setLoading] = useState(true);
  const [projectFilter, setProjectFilter] = useState("");
  const [searchText, setSearchText] = useState("");
  const [modal, setModal] = useState<"new" | Meeting | null>(null);
  const [form, setForm] = useState({
    title: "",
    description: "",
    start_at: "",
    end_at: "",
    location: "",
    attendee_ids: [] as string[],
  });
  const { hasPermission } = useAuth();

  const canWrite = hasPermission("meetings:write");

  const load = () => {
    listProjectNames().then(setProjectNames).catch(() => setProjectNames([]));
    const params = projectFilter ? { project_id: projectFilter } : undefined;
    listMeetings(params)
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [projectFilter]);

  useEffect(() => {
    const onMeetingsUpdated = () => load();
    window.addEventListener("ws:meetings_updated", onMeetingsUpdated);
    return () => window.removeEventListener("ws:meetings_updated", onMeetingsUpdated);
  }, []);

  useEffect(() => {
    if (canWrite) listAssignableUsers().then(setAssignableUsers).catch(() => {});
  }, [canWrite]);

  const openNew = () => {
    const now = new Date();
    const start = new Date(now);
    start.setHours(10, 0, 0, 0);
    const end = new Date(now);
    end.setHours(11, 0, 0, 0);
    setForm({
      title: "",
      description: "",
      start_at: start.toISOString().slice(0, 16),
      end_at: end.toISOString().slice(0, 16),
      location: "",
      attendee_ids: [],
    });
    setModal("new");
  };
  const openEdit = (m: Meeting) => {
    setForm({
      title: m.title,
      description: m.description || "",
      start_at: m.start_at.slice(0, 16),
      end_at: m.end_at.slice(0, 16),
      location: m.location || "",
      attendee_ids: m.attendee_ids ?? [],
    });
    setModal(m);
  };

  const save = async () => {
    if (modal === null) return;
    const basePayload = {
      title: form.title,
      description: form.description || undefined,
      start_at: new Date(form.start_at).toISOString(),
      end_at: new Date(form.end_at).toISOString(),
      location: form.location || undefined,
      attendee_ids: form.attendee_ids,
    };
    try {
      if (modal === "new") {
        await createMeeting(basePayload);
      } else {
        await updateMeeting(modal.id, basePayload);
      }
      setModal(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Delete this meeting?")) return;
    try {
      await deleteMeeting(id);
      setModal(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const projectMap = Object.fromEntries(projectNames.map((p) => [p.id, p.name]));
  const searchLower = searchText.trim().toLowerCase();
  const filteredItems = searchLower
    ? items.filter(
        (m) =>
          (m.title ?? "").toLowerCase().includes(searchLower) ||
          (m.description ?? "").toLowerCase().includes(searchLower) ||
          (m.location ?? "").toLowerCase().includes(searchLower) ||
          (m.project_id && (projectMap[m.project_id] ?? "").toLowerCase().includes(searchLower))
      )
    : items;
  const inputClass = "w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <label className="text-sm font-medium text-gray-700">Project</label>
          <select
            value={projectFilter}
            onChange={(e) => setProjectFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[180px]"
          >
            <option value="">All projects</option>
            {projectNames.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <label className="text-sm font-medium text-gray-700">Search</label>
          <input
            type="search"
            placeholder="Title, description, location..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[200px]"
          />
        </div>
        {canWrite && (
          <button
            onClick={openNew}
            className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover"
          >
            Add meeting
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
                <th className="px-4 py-3">Start</th>
                <th className="px-4 py-3">End</th>
                {canWrite && <th className="px-4 py-3 w-24 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredItems.map((m) => (
                <tr key={m.id} className="hover:bg-gray-50/80">
                  <td className="px-4 py-3 font-medium text-gray-900">{m.title}</td>
                  <td className="px-4 py-3 text-gray-600">{m.project_id ? projectMap[m.project_id] || m.project_id : "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{new Date(m.start_at).toLocaleString()}</td>
                  <td className="px-4 py-3 text-gray-600">{new Date(m.end_at).toLocaleString()}</td>
                  {canWrite && (
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button type="button" onClick={() => openEdit(m)} title="Edit" className="p-1.5 rounded-lg text-gray-500 hover:text-primary hover:bg-gray-100 transition-colors">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                        <button type="button" onClick={() => remove(m.id)} title="Delete" className="p-1.5 rounded-lg text-gray-500 hover:text-red-600 hover:bg-gray-100 transition-colors">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
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
            <h2 className="text-lg font-semibold text-gray-900 mb-4">{modal === "new" ? "New meeting" : "Edit meeting"}</h2>
            <div className="space-y-3">
              <input
                placeholder="Title"
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                className={inputClass}
              />
              <textarea
                placeholder="Description"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                className={inputClass}
                rows={2}
              />
              <div>
                <label className={labelClass}>Start</label>
                <input
                  type="datetime-local"
                  value={form.start_at}
                  onChange={(e) => setForm((f) => ({ ...f, start_at: e.target.value }))}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>End</label>
                <input
                  type="datetime-local"
                  value={form.end_at}
                  onChange={(e) => setForm((f) => ({ ...f, end_at: e.target.value }))}
                  className={inputClass}
                />
              </div>
              <input
                placeholder="Location"
                value={form.location}
                onChange={(e) => setForm((f) => ({ ...f, location: e.target.value }))}
                className={inputClass}
              />
              <div>
                <label className={labelClass}>Assign attendees</label>
                <SearchableUserMultiSelect
                  users={assignableUsers}
                  value={form.attendee_ids}
                  onChange={(ids) => setForm((f) => ({ ...f, attendee_ids: ids }))}
                  placeholder="Search and add attendees..."
                  variant="light"
                />
              </div>
            </div>
            <NotesSection entityType="meeting" entityId={modal !== "new" ? (modal as Meeting).id : undefined} />
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">
                Cancel
              </button>
              <button onClick={save} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover">
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
