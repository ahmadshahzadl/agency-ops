import { useCallback, useEffect, useState } from "react";
import {
  listAnnouncements,
  createAnnouncement,
  updateAnnouncement,
  deleteAnnouncement,
  type Announcement,
  type AnnouncementCreate,
} from "@/api/announcements";
import { listUsers } from "@/api/users";
import { NotesSection } from "@/components/NotesSection";
import { useModal } from "@/contexts/ModalContext";
import { useAuth } from "@/store/auth";
import { BulkActionsBar } from "@/components/BulkActionsBar";

export default function AnnouncementsPage() {
  const { showConfirm, showAlert } = useModal();
  const { hasPermission } = useAuth();
  const canCreate = hasPermission("admin:all") || hasPermission("announcements:write");
  const canBulk = canCreate;
  const [items, setItems] = useState<Announcement[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [users, setUsers] = useState<{ id: string; email: string; full_name: string | null }[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<"new" | Announcement | null>(null);
  const [form, setForm] = useState<{
    title: string;
    body: string;
    target_type: "all" | "users";
    target_user_ids: string[];
  }>({ title: "", body: "", target_type: "all", target_user_ids: [] });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (canCreate) {
        const [anns, userList] = await Promise.all([listAnnouncements(), listUsers()]);
        setItems(anns);
        setUsers(userList.map((u) => ({ id: u.id, email: u.email, full_name: u.full_name })));
      } else {
        const anns = await listAnnouncements();
        setItems(anns);
      }
    } finally {
      setLoading(false);
    }
  }, [canCreate]);

  useEffect(() => {
    load();
  }, [load]);

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
      } else if (modal) {
        await updateAnnouncement(modal.id, payload);
      }
      setModal(null);
      load();
    } catch (e) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    }
  };

  const remove = (id: string) => {
    showConfirm({
      title: "Delete announcement",
      message: "Delete this announcement? Notifications already sent will remain.",
      confirmLabel: "Delete",
      variant: "danger",
      onConfirm: async () => {
        try {
          await deleteAnnouncement(id);
          setModal(null);
          setSelectedIds((s) => {
            const next = new Set(s);
            next.delete(id);
            return next;
          });
          load();
        } catch (e) {
          showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
          throw e;
        }
      },
    });
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };
  const toggleSelectAll = () => {
    if (selectedIds.size === items.length) setSelectedIds(new Set());
    else setSelectedIds(new Set(items.map((a) => a.id)));
  };
  const bulkDelete = () => {
    const ids = Array.from(selectedIds);
    showConfirm({
      title: "Delete announcements",
      message: `Delete ${ids.length} announcement(s)? Notifications already sent will remain.`,
      confirmLabel: "Delete all",
      variant: "danger",
      onConfirm: async () => {
        setBulkDeleting(true);
        try {
          for (const id of ids) {
            try {
              await deleteAnnouncement(id);
            } catch (e) {
              showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed to delete announcement" });
              throw e;
            }
          }
          setSelectedIds(new Set());
          setModal(null);
          load();
        } finally {
          setBulkDeleting(false);
        }
      },
    });
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
        {canCreate && (
          <button
            onClick={openNew}
            className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover"
          >
            New announcement
          </button>
        )}
      </div>

      {canBulk && (
        <BulkActionsBar
          selectedCount={selectedIds.size}
          entityName="announcements"
          onClear={() => setSelectedIds(new Set())}
          onDelete={bulkDelete}
          loading={bulkDeleting}
        />
      )}

      {loading ? (
        <p className="text-gray-500">Loading…</p>
      ) : (
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600">
              <tr>
                {canBulk && (
                  <th className="px-4 py-3 w-10">
                    <input
                      type="checkbox"
                      checked={items.length > 0 && selectedIds.size === items.length}
                      onChange={toggleSelectAll}
                      className="rounded border-gray-300 text-primary focus:ring-primary/20"
                    />
                  </th>
                )}
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Target</th>
                <th className="px-4 py-3">Created</th>
                {canCreate && <th className="px-4 py-3 w-24 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((a) => (
                <tr key={a.id} className={`hover:bg-gray-50/80 ${selectedIds.has(a.id) ? "bg-primary/5" : ""}`}>
                  {canBulk && (
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(a.id)}
                        onChange={() => toggleSelect(a.id)}
                        className="rounded border-gray-300 text-primary focus:ring-primary/20"
                      />
                    </td>
                  )}
                  <td className="px-4 py-3 font-medium text-gray-900">{a.title}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {a.target_type === "all" ? "All users" : `${(a.target_user_ids || []).length} users`}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {new Date(a.created_at).toLocaleString()}
                  </td>
                  {canCreate && (
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
                  )}
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
            <NotesSection entityType="announcement" entityId={modal !== "new" ? (modal as Announcement).id : undefined} />
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
