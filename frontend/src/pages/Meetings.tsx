import { useEffect, useState } from "react";
import { listMeetings, createMeeting, updateMeeting, deleteMeeting, type Meeting } from "@/api/meetings";
import { listProjectNames } from "@/api/projects";
import { listAssignableUsers, type UserList } from "@/api/users";
import { SearchableUserMultiSelect } from "@/components/SearchableUserMultiSelect";
import { useAuth } from "@/store/auth";

export default function MeetingsPage() {
  const [items, setItems] = useState<Meeting[]>([]);
  const [projectNames, setProjectNames] = useState<{ id: string; name: string }[]>([]);
  const [assignableUsers, setAssignableUsers] = useState<UserList[]>([]);
  const [loading, setLoading] = useState(true);
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
    listMeetings()
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
    listProjectNames()
      .then(setProjectNames)
      .catch(() => setProjectNames([]));
  };

  useEffect(() => {
    load();
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

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-white">Meetings</h1>
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
        <p className="text-slate-400">Loading...</p>
      ) : (
        <div className="rounded-xl border border-slate-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-800 text-left text-sm text-slate-400">
              <tr>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Project</th>
                <th className="px-4 py-3">Start</th>
                <th className="px-4 py-3">End</th>
                {canWrite && <th className="px-4 py-3 w-24"></th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {items.map((m) => (
                <tr key={m.id} className="hover:bg-slate-800/50">
                  <td className="px-4 py-3 text-white">{m.title}</td>
                  <td className="px-4 py-3 text-slate-300">{m.project_id ? projectMap[m.project_id] || m.project_id : "—"}</td>
                  <td className="px-4 py-3 text-slate-300">{new Date(m.start_at).toLocaleString()}</td>
                  <td className="px-4 py-3 text-slate-300">{new Date(m.end_at).toLocaleString()}</td>
                  {canWrite && (
                    <td className="px-4 py-3">
                      <button onClick={() => openEdit(m)} className="text-primary hover:underline mr-2">
                        Edit
                      </button>
                      <button onClick={() => remove(m.id)} className="text-red-400 hover:underline">
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
            <h2 className="text-lg font-semibold text-white mb-4">{modal === "new" ? "New meeting" : "Edit meeting"}</h2>
            <div className="space-y-3">
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
              <div>
                <label className="block text-sm text-slate-400 mb-1">Start</label>
                <input
                  type="datetime-local"
                  value={form.start_at}
                  onChange={(e) => setForm((f) => ({ ...f, start_at: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">End</label>
                <input
                  type="datetime-local"
                  value={form.end_at}
                  onChange={(e) => setForm((f) => ({ ...f, end_at: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                />
              </div>
              <input
                placeholder="Location"
                value={form.location}
                onChange={(e) => setForm((f) => ({ ...f, location: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
              <div>
                <label className="block text-sm text-slate-400 mb-1">Assign attendees</label>
                <SearchableUserMultiSelect
                  users={assignableUsers}
                  value={form.attendee_ids}
                  onChange={(ids) => setForm((f) => ({ ...f, attendee_ids: ids }))}
                  placeholder="Search and add attendees..."
                />
              </div>
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
