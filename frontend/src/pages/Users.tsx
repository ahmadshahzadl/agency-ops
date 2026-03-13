import { useEffect, useMemo, useState } from "react";
import { listUsers, createUser, updateUser, deleteUser, type UserList } from "@/api/users";
import { listRoles } from "@/api/roles";
import { listTeams } from "@/api/teams";
import { useModal } from "@/contexts/ModalContext";
import { useAuth } from "@/store/auth";
import { BulkActionsBar } from "@/components/BulkActionsBar";

export default function Users() {
  const { showConfirm, showAlert } = useModal();
  const { hasPermission } = useAuth();
  const canBulk = hasPermission("admin:all");
  const [items, setItems] = useState<UserList[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [roles, setRoles] = useState<{ id: string; name: string }[]>([]);
  const [teams, setTeams] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<"new" | UserList | null>(null);
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    phone: "",
    job_title: "",
    is_active: true,
    manager_id: null as string | null,
    role_ids: [] as string[],
    team_ids: [] as string[],
  });
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"" | "active" | "inactive">("");
  const [roleFilter, setRoleFilter] = useState("");
  const [teamFilter, setTeamFilter] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [userList, roleList, teamList] = await Promise.all([
        listUsers(),
        listRoles(),
        listTeams(),
      ]);
      setItems(userList);
      setRoles(roleList);
      setTeams(teamList);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filteredItems = useMemo(() => {
    let list = items;
    const q = search.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (u) =>
          (u.email || "").toLowerCase().includes(q) ||
          (u.full_name || "").toLowerCase().includes(q)
      );
    }
    if (statusFilter === "active") list = list.filter((u) => u.is_active);
    if (statusFilter === "inactive") list = list.filter((u) => !u.is_active);
    if (roleFilter) list = list.filter((u) => (u.role_ids || []).includes(roleFilter));
    if (teamFilter) list = list.filter((u) => (u.team_ids || []).includes(teamFilter));
    return list;
  }, [items, search, statusFilter, roleFilter, teamFilter]);

  const openNew = () => {
    setForm({
      email: "",
      password: "",
      full_name: "",
      phone: "",
      job_title: "",
      is_active: true,
      manager_id: null,
      role_ids: [],
      team_ids: [],
    });
    setModal("new");
  };

  const openEdit = (u: UserList) => {
    setForm({
      email: u.email,
      password: "",
      full_name: u.full_name || "",
      phone: u.phone || "",
      job_title: u.job_title || "",
      is_active: u.is_active,
      manager_id: u.manager_id || null,
      role_ids: u.role_ids || [],
      team_ids: u.team_ids || [],
    });
    setModal(u);
  };

  const toggleRole = (id: string) => {
    setForm((f) => ({
      ...f,
      role_ids: f.role_ids.includes(id) ? f.role_ids.filter((r) => r !== id) : [...f.role_ids, id],
    }));
  };

  const toggleTeam = (id: string) => {
    setForm((f) => ({
      ...f,
      team_ids: f.team_ids.includes(id) ? f.team_ids.filter((t) => t !== id) : [...f.team_ids, id],
    }));
  };

  const save = async () => {
    if (modal === null) return;
    try {
      if (modal === "new") {
        await createUser({
          email: form.email,
          password: form.password,
          full_name: form.full_name || undefined,
          phone: form.phone || undefined,
          job_title: form.job_title || undefined,
          is_active: form.is_active,
          manager_id: form.manager_id,
          role_ids: form.role_ids.length ? form.role_ids : undefined,
          team_ids: form.team_ids.length ? form.team_ids : undefined,
        });
      } else {
        await updateUser(modal.id, {
          full_name: form.full_name || undefined,
          phone: form.phone || undefined,
          job_title: form.job_title || undefined,
          is_active: form.is_active,
          manager_id: form.manager_id,
          role_ids: form.role_ids,
          team_ids: form.team_ids,
        });
      }
      setModal(null);
      load();
    } catch (e: unknown) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    }
  };

  const remove = (id: string) => {
    showConfirm({
      title: "Delete user",
      message: "Delete this user?",
      confirmLabel: "Delete",
      variant: "danger",
      onConfirm: async () => {
        try {
          await deleteUser(id);
          setModal(null);
          setSelectedIds((s) => {
            const next = new Set(s);
            next.delete(id);
            return next;
          });
          load();
        } catch (e: unknown) {
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
    if (selectedIds.size === filteredItems.length) setSelectedIds(new Set());
    else setSelectedIds(new Set(filteredItems.map((u) => u.id)));
  };
  const bulkDelete = () => {
    const ids = Array.from(selectedIds);
    showConfirm({
      title: "Delete users",
      message: `Delete ${ids.length} user(s)? This cannot be undone.`,
      confirmLabel: "Delete all",
      variant: "danger",
      onConfirm: async () => {
        setBulkDeleting(true);
        try {
          for (const id of ids) {
            try {
              await deleteUser(id);
            } catch (e) {
              showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed to delete user" });
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

  const roleMap = Object.fromEntries(roles.map((r) => [r.id, r.name]));
  const teamMap = Object.fromEntries(teams.map((t) => [t.id, t.name]));
  const userMap = Object.fromEntries(items.map((u) => [u.id, u.full_name || u.email]));
  const getRoleNames = (roleIds: string[]) =>
    roleIds?.map((id) => roleMap[id]).filter(Boolean).join(", ") || "—";

  const inputClass = "w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";
  const selectClass = "px-3 py-2 rounded-lg border border-gray-300 text-gray-900 text-sm focus:ring-2 focus:ring-primary/20 focus:border-primary";

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
            placeholder="Search by email or name..."
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as "" | "active" | "inactive")}
          className={selectClass}
        >
          <option value="">All statuses</option>
          <option value="active">Active only</option>
          <option value="inactive">Inactive only</option>
        </select>
        <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className={selectClass}>
          <option value="">All roles</option>
          {roles.map((r) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
        </select>
        <select value={teamFilter} onChange={(e) => setTeamFilter(e.target.value)} className={selectClass}>
          <option value="">All teams</option>
          {teams.map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </select>
        <button
          onClick={openNew}
          className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover whitespace-nowrap"
        >
          Add user
        </button>
      </div>

      {canBulk && (
        <BulkActionsBar
          selectedCount={selectedIds.size}
          entityName="users"
          onClear={() => setSelectedIds(new Set())}
          onDelete={bulkDelete}
          loading={bulkDeleting}
        />
      )}

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600">
              <tr>
                {canBulk && (
                  <th className="px-4 py-3 w-10">
                    <input
                      type="checkbox"
                      checked={filteredItems.length > 0 && selectedIds.size === filteredItems.length}
                      onChange={toggleSelectAll}
                      className="rounded border-gray-300 text-primary focus:ring-primary/20"
                    />
                  </th>
                )}
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Phone</th>
                <th className="px-4 py-3">Job title</th>
                <th className="px-4 py-3">Active</th>
                <th className="px-4 py-3">Manager</th>
                <th className="px-4 py-3">Roles</th>
                <th className="px-4 py-3">Teams</th>
                <th className="px-4 py-3 w-24 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={canBulk ? 8 : 7} className="px-4 py-8 text-center text-gray-500">
                    {search || statusFilter || roleFilter || teamFilter
                      ? "No users match your filters."
                      : "No users yet."}
                  </td>
                </tr>
              ) : (
                filteredItems.map((u) => (
                  <tr key={u.id} className={`hover:bg-gray-50/80 ${selectedIds.has(u.id) ? "bg-primary/5" : ""}`}>
                    {canBulk && (
                      <td className="px-4 py-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.has(u.id)}
                          onChange={() => toggleSelect(u.id)}
                          className="rounded border-gray-300 text-primary focus:ring-primary/20"
                        />
                      </td>
                    )}
                    <td className="px-4 py-3 font-medium text-gray-900">{u.email}</td>
                    <td className="px-4 py-3 text-gray-600">{u.full_name || "—"}</td>
                    <td className="px-4 py-3 text-gray-600 text-sm">{u.phone || "—"}</td>
                    <td className="px-4 py-3 text-gray-600 text-sm">{u.job_title || "—"}</td>
                    <td className="px-4 py-3 text-gray-600">{u.is_active ? "Yes" : "No"}</td>
                    <td className="px-4 py-3 text-gray-600 text-sm">
                      {u.manager_id ? userMap[u.manager_id] || "—" : "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-sm">
                      {getRoleNames(u.role_ids || [])}
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-sm">
                      {u.team_ids?.length
                        ? u.team_ids.map((id) => teamMap[id]).filter(Boolean).join(", ") || `${u.team_ids.length} team(s)`
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => openEdit(u)}
                          title="Edit"
                          className="p-1.5 rounded-lg text-gray-500 hover:text-primary hover:bg-gray-100 transition-colors"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          onClick={() => remove(u.id)}
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
            className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              {modal === "new" ? "New user" : "Edit user"}
            </h2>
            <div className="space-y-3">
              <div>
                <label className={labelClass}>Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                  className={inputClass}
                  placeholder="user@example.com"
                  disabled={modal !== "new"}
                />
              </div>
              {modal === "new" && (
                <div>
                  <label className={labelClass}>Password</label>
                  <input
                    type="password"
                    value={form.password}
                    onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                    className={inputClass}
                    placeholder="Password"
                  />
                </div>
              )}
              <div>
                <label className={labelClass}>Full name</label>
                <input
                  value={form.full_name}
                  onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
                  className={inputClass}
                  placeholder="Full name"
                />
              </div>
              <div>
                <label className={labelClass}>Phone</label>
                <input
                  type="tel"
                  value={form.phone}
                  onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))}
                  className={inputClass}
                  placeholder="Phone number"
                />
              </div>
              <div>
                <label className={labelClass}>Job title</label>
                <input
                  value={form.job_title}
                  onChange={(e) => setForm((f) => ({ ...f, job_title: e.target.value }))}
                  className={inputClass}
                  placeholder="e.g. Developer, Project Manager"
                />
              </div>
              <label className="flex items-center gap-2 text-gray-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                  className="rounded border-gray-300 text-primary focus:ring-primary/20"
                />
                Active
              </label>
              <div>
                <label className={labelClass}>Manager</label>
                <select
                  value={form.manager_id ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, manager_id: e.target.value || null }))}
                  className={inputClass}
                >
                  <option value="">— None —</option>
                  {items
                    .filter((u) => modal === "new" || u.id !== modal.id)
                    .map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.full_name || u.email}
                      </option>
                    ))}
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Team members under this manager will show up in their Team activity.
                </p>
              </div>
              <div>
                <span className={labelClass}>Roles (select all that apply)</span>
                <p className="text-xs text-gray-500 mb-2">
                  Multiple roles are supported—e.g. one person can be both PM and Developer in small teams.
                </p>
                <div className="flex flex-wrap gap-x-4 gap-y-2">
                  {roles.map((r) => (
                    <label key={r.id} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.role_ids.includes(r.id)}
                        onChange={() => toggleRole(r.id)}
                        className="rounded border-gray-300 text-primary focus:ring-primary/20"
                      />
                      {r.name}
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <span className={labelClass}>Teams (select all that apply)</span>
                <div className="flex flex-wrap gap-x-4 gap-y-2">
                  {teams.map((t) => (
                    <label key={t.id} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={form.team_ids.includes(t.id)}
                        onChange={() => toggleTeam(t.id)}
                        className="rounded border-gray-300 text-primary focus:ring-primary/20"
                      />
                      {t.name}
                    </label>
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
