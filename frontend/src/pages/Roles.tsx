import { useEffect, useState } from "react";
import {
  listRoles,
  listPermissions,
  createRole,
  updateRole,
  type Role,
  type Permission,
} from "@/api/roles";

export default function Roles() {
  const [items, setItems] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<"new" | Role | null>(null);
  const [form, setForm] = useState({
    name: "",
    description: "",
    permission_ids: [] as string[],
  });

  const load = async () => {
    setLoading(true);
    try {
      const [roleList, permList] = await Promise.all([listRoles(), listPermissions()]);
      setItems(roleList);
      setPermissions(permList);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openNew = () => {
    setForm({ name: "", description: "", permission_ids: [] });
    setModal("new");
  };

  const openEdit = (r: Role) => {
    setForm({
      name: r.name,
      description: r.description || "",
      permission_ids: r.permission_ids || [],
    });
    setModal(r);
  };

  const togglePermission = (id: string) => {
    setForm((f) => ({
      ...f,
      permission_ids: f.permission_ids.includes(id)
        ? f.permission_ids.filter((p) => p !== id)
        : [...f.permission_ids, id],
    }));
  };

  const save = async () => {
    if (modal === null) return;
    try {
      if (modal === "new") {
        await createRole({
          name: form.name,
          description: form.description || undefined,
          permission_ids: form.permission_ids.length ? form.permission_ids : undefined,
        });
      } else {
        await updateRole(modal.id, {
          name: form.name,
          description: form.description || undefined,
          permission_ids: form.permission_ids,
        });
      }
      setModal(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-white">Roles</h1>
        <button
          onClick={openNew}
          className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover"
        >
          Add role
        </button>
      </div>

      {loading ? (
        <p className="text-slate-400">Loading...</p>
      ) : (
        <div className="rounded-xl border border-slate-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-800 text-left text-sm text-slate-400">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3">Permissions</th>
                <th className="px-4 py-3 w-24"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {items.map((r) => (
                <tr key={r.id} className="hover:bg-slate-800/50">
                  <td className="px-4 py-3 text-white">{r.name}</td>
                  <td className="px-4 py-3 text-slate-300">{r.description || "—"}</td>
                  <td className="px-4 py-3 text-slate-300 text-sm">
                    {r.permission_ids?.length ? `${r.permission_ids.length} permission(s)` : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => openEdit(r)} className="text-primary hover:underline">
                      Edit
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
            className="bg-slate-800 rounded-xl border border-slate-700 p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-white mb-4">
              {modal === "new" ? "New role" : "Edit role"}
            </h2>
            <div className="space-y-3">
              <input
                placeholder="Name"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
              <input
                placeholder="Description"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
              <div>
                <span className="text-sm text-slate-400 block mb-1">Permissions</span>
                <div className="flex flex-wrap gap-x-4 gap-y-1">
                  {permissions.map((p) => (
                    <label key={p.id} className="flex items-center gap-1 text-sm text-slate-300">
                      <input
                        type="checkbox"
                        checked={form.permission_ids.includes(p.id)}
                        onChange={() => togglePermission(p.id)}
                        className="rounded"
                      />
                      {p.code}
                    </label>
                  ))}
                </div>
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
