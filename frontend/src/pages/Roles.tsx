import { useEffect, useMemo, useState } from "react";
import {
  listRoles,
  listPermissions,
  createRole,
  updateRole,
  type Role,
  type Permission,
} from "@/api/roles";

function permissionGroup(code: string): string {
  const idx = code.indexOf(":");
  if (idx > 0) return code.slice(0, idx);
  return "Other";
}

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
  const [search, setSearch] = useState("");

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

  const filteredItems = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (r) =>
        (r.name || "").toLowerCase().includes(q) ||
        (r.description || "").toLowerCase().includes(q)
    );
  }, [items, search]);

  const permissionsByGroup = useMemo(() => {
    const map = new Map<string, Permission[]>();
    for (const p of permissions) {
      const group = permissionGroup(p.code);
      if (!map.has(group)) map.set(group, []);
      map.get(group)!.push(p);
    }
    const groups = Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0]));
    if (map.has("Other")) {
      const other = map.get("Other")!;
      return groups.filter(([k]) => k !== "Other").concat([["Other", other]]);
    }
    return groups;
  }, [permissions]);

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

  const openDuplicate = (r: Role) => {
    setForm({
      name: `Copy of ${r.name}`,
      description: r.description || "",
      permission_ids: r.permission_ids || [],
    });
    setModal("new");
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

  const inputClass = "w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="relative flex-1 min-w-[180px] max-w-xs">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search roles by name or description..."
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>
        <button
          onClick={openNew}
          className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover whitespace-nowrap"
        >
          Add role
        </button>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3">Permissions</th>
                <th className="px-4 py-3 w-28 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                    {search ? "No roles match your search." : "No roles yet."}
                  </td>
                </tr>
              ) : (
                filteredItems.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50/80">
                    <td className="px-4 py-3 font-medium text-gray-900">{r.name}</td>
                    <td className="px-4 py-3 text-gray-600">{r.description || "—"}</td>
                    <td className="px-4 py-3 text-gray-600 text-sm">
                      {r.permission_ids?.length ? `${r.permission_ids.length} permission(s)` : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => openEdit(r)}
                          title="Edit"
                          className="p-1.5 rounded-lg text-gray-500 hover:text-primary hover:bg-gray-100 transition-colors"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          onClick={() => openDuplicate(r)}
                          title="Duplicate role"
                          className="p-1.5 rounded-lg text-gray-500 hover:text-emerald-600 hover:bg-gray-100 transition-colors"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h2m8 0h2a2 2 0 012 2v2m0 8V6a2 2 0 012-2h-2m-4-1v8m0 0v2m0-2v-2m0-2V9m0 2v2" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
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
              {modal === "new" ? "New role" : "Edit role"}
            </h2>
            <div className="space-y-3">
              <div>
                <label className={labelClass}>Name</label>
                <input
                  placeholder="Role name"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Description</label>
                <input
                  placeholder="Description"
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  className={inputClass}
                />
              </div>
              <div>
                <span className={labelClass}>Permissions (grouped by category)</span>
                <div className="max-h-56 overflow-y-auto border border-gray-200 rounded-lg py-2 px-3 bg-gray-50/50 space-y-3">
                  {permissionsByGroup.map(([groupName, perms]) => (
                    <div key={groupName}>
                      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1.5 sticky top-0 bg-gray-50/95 py-0.5">
                        {groupName}
                      </p>
                      <div className="flex flex-wrap gap-x-4 gap-y-2">
                        {perms.map((p) => (
                          <label key={p.id} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={form.permission_ids.includes(p.id)}
                              onChange={() => togglePermission(p.id)}
                              className="rounded border-gray-300 text-primary focus:ring-primary/20"
                            />
                            {p.code}
                          </label>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
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
