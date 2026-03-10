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

  const inputClass = "w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";

  return (
    <div>
      <div className="flex items-center justify-end mb-4">
        <button
          onClick={openNew}
          className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover"
        >
          New announcement
        </button>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading…</p>
      ) : (
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600">
              <tr>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Target</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3 w-24 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((a) => (
                <tr key={a.id} className="hover:bg-gray-50/80">
                  <td className="px-4 py-3 font-medium text-gray-900">{a.title}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {a.target_type === "all" ? "All users" : `${(a.target_user_ids || []).length} users`}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {new Date(a.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        type="button"
                        onClick={() => openEdit(a)}
                        title="Edit"
                        className="p-1.5 rounded-lg text-gray-500 hover:text-primary hover:bg-gray-100 transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                        </svg>
                      </button>
                      <button
                        type="button"
                        onClick={() => remove(a.id)}
                        title="Delete"
                        className="p-1.5 rounded-lg text-gray-500 hover:text-red-600 hover:bg-gray-100 transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-10"
          onClick={() => setModal(null)}
        >
          <div
            className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              {modal === "new" ? "New announcement" : "Edit announcement"}
            </h2>
            <div className="space-y-3">
              <div>
                <label className={labelClass}>Title</label>
                <input
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                  className={inputClass}
                  placeholder="Announcement title"
                />
              </div>
              <div>
                <label className={labelClass}>Body</label>
                <textarea
                  value={form.body}
                  onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
                  className={inputClass}
                  rows={3}
                  placeholder="Message (optional)"
                />
              </div>
              <div>
                <label className={labelClass}>Send to</label>
                <select
                  value={form.target_type}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      target_type: e.target.value as "all" | "users",
                      target_user_ids: e.target.value === "all" ? [] : f.target_user_ids,
                    }))
                  }
                  className={inputClass}
                >
                  <option value="all">All users</option>
                  <option value="users">Specific users</option>
                </select>
              </div>
              {form.target_type === "users" && (
                <div className="max-h-40 overflow-y-auto border border-gray-200 rounded-lg p-3 bg-gray-50/50">
                  <p className="text-xs font-medium text-gray-600 mb-2">Select users:</p>
                  {users.map((u) => (
                    <label key={u.id} className="flex items-center gap-2 py-1.5 text-sm text-gray-700 cursor-pointer hover:bg-gray-100/80 rounded px-2 -mx-2">
                      <input
                        type="checkbox"
                        checked={form.target_user_ids.includes(u.id)}
                        onChange={() => toggleUser(u.id)}
                        className="rounded border-gray-300 text-primary focus:ring-primary/20"
                      />
                      {u.full_name || u.email}
                    </label>
                  ))}
                </div>
              )}
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">
                Cancel
              </button>
              <button
                onClick={save}
                disabled={!form.title.trim()}
                className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover disabled:opacity-50"
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
