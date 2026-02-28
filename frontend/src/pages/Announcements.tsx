import { useEffect, useState } from "react";
import {
  listAnnouncements,
  createAnnouncement,
  updateAnnouncement,
  deleteAnnouncement,
  type Announcement,
  type AnnouncementCreate,
} from "@/api/announcements";
import { listUsers } from "@/api/users";

export default function AnnouncementsPage() {
  const [items, setItems] = useState<Announcement[]>([]);
  const [users, setUsers] = useState<{ id: string; email: string; full_name: string | null }[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<"new" | Announcement | null>(null);
  const [form, setForm] = useState<{
    title: string;
    body: string;
    target_type: "all" | "users";
    target_user_ids: string[];
  }>({ title: "", body: "", target_type: "all", target_user_ids: [] });

  const load = async () => {
    setLoading(true);
    try {
      const [anns, userList] = await Promise.all([listAnnouncements(), listUsers()]);
      setItems(anns);
      setUsers(userList.map((u) => ({ id: u.id, email: u.email, full_name: u.full_name })));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openNew = () => {
    setForm({ title: "", body: "", target_type: "all", target_user_ids: [] });
    setModal("new");
  };

  const openEdit = (a: Announcement) => {
    setForm({
      title: a.title,
      body: a.body || "",
      target_type: a.target_type as "all" | "users",
      target_user_ids: a.target_user_ids || [],
    });
    setModal(a);
  };

  const save = async () => {
    if (!form.title.trim()) return;
    try {
      const payload: AnnouncementCreate = {
        title: form.title.trim(),
        body: form.body.trim() || null,
        target_type: form.target_type,
        target_user_ids: form.target_type === "users" ? form.target_user_ids : null,
      };
      if (modal === "new") {
        await createAnnouncement(payload);
      } else {
        await updateAnnouncement(modal.id, payload);
      }
      setModal(null);
      load();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Delete this announcement? Notifications already sent will remain.")) return;
    try {
      await deleteAnnouncement(id);
      setModal(null);
      load();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const toggleUser = (id: string) => {
    setForm((f) => ({
      ...f,
      target_user_ids: f.target_user_ids.includes(id)
        ? f.target_user_ids.filter((u) => u !== id)
        : [...f.target_user_ids, id],
    }));
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-white">Announcements</h1>
        <button
          onClick={openNew}
          className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover"
        >
          New announcement
        </button>
      </div>
      {loading ? (
        <p className="text-slate-400">Loading…</p>
      ) : (
        <div className="rounded-xl border border-slate-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-800 text-left text-sm text-slate-400">
              <tr>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Target</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3 w-24"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {items.map((a) => (
                <tr key={a.id} className="hover:bg-slate-800/50">
                  <td className="px-4 py-3 text-white">{a.title}</td>
                  <td className="px-4 py-3 text-slate-300">
                    {a.target_type === "all" ? "All users" : `${(a.target_user_ids || []).length} users`}
                  </td>
                  <td className="px-4 py-3 text-slate-300">
                    {new Date(a.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => openEdit(a)} className="text-primary hover:underline mr-2">
                      Edit
                    </button>
                    <button onClick={() => remove(a.id)} className="text-red-400 hover:underline">
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modal && (
        <div
          className="fixed inset-0 bg-black/60 flex items-center justify-center z-10"
          onClick={() => setModal(null)}
        >
          <div
            className="bg-slate-800 rounded-xl border border-slate-700 p-6 w-full max-w-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-white mb-4">
              {modal === "new" ? "New announcement" : "Edit announcement"}
            </h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-slate-400 mb-1">Title</label>
                <input
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                  placeholder="Announcement title"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Body</label>
                <textarea
                  value={form.body}
                  onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                  rows={3}
                  placeholder="Message (optional)"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Send to</label>
                <select
                  value={form.target_type}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      target_type: e.target.value as "all" | "users",
                      target_user_ids: e.target.value === "all" ? [] : f.target_user_ids,
                    }))
                  }
                  className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                >
                  <option value="all">All users</option>
                  <option value="users">Specific users</option>
                </select>
              </div>
              {form.target_type === "users" && (
                <div className="max-h-40 overflow-y-auto border border-slate-600 rounded-lg p-2">
                  <p className="text-xs text-slate-400 mb-2">Select users:</p>
                  {users.map((u) => (
                    <label key={u.id} className="flex items-center gap-2 py-1 text-sm text-slate-300">
                      <input
                        type="checkbox"
                        checked={form.target_user_ids.includes(u.id)}
                        onChange={() => toggleUser(u.id)}
                        className="rounded"
                      />
                      {u.full_name || u.email}
                    </label>
                  ))}
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-slate-400 hover:text-white">
                Cancel
              </button>
              <button
                onClick={save}
                disabled={!form.title.trim()}
                className="px-4 py-2 rounded-lg bg-primary text-white font-medium disabled:opacity-50"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
