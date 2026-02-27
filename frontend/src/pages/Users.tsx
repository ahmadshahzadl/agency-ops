import { useEffect, useState } from "react";
import { listUsers, createUser, updateUser, deleteUser, type UserList } from "@/api/users";
import { listRoles } from "@/api/roles";
import { listTeams } from "@/api/teams";

export default function Users() {
  const [items, setItems] = useState<UserList[]>([]);
  const [roles, setRoles] = useState<{ id: string; name: string }[]>([]);
  const [teams, setTeams] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<"new" | UserList | null>(null);
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    is_active: true,
    manager_id: null as string | null,
    role_ids: [] as string[],
    team_ids: [] as string[],
  });

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

  const openNew = () => {
    setForm({
      email: "",
      password: "",
      full_name: "",
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
          is_active: form.is_active,
          manager_id: form.manager_id,
          role_ids: form.role_ids.length ? form.role_ids : undefined,
          team_ids: form.team_ids.length ? form.team_ids : undefined,
        });
      } else {
        await updateUser(modal.id, {
          full_name: form.full_name || undefined,
          is_active: form.is_active,
          manager_id: form.manager_id,
          role_ids: form.role_ids,
          team_ids: form.team_ids,
        });
      }
      setModal(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Delete this user?")) return;
    try {
      await deleteUser(id);
      setModal(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const roleMap = Object.fromEntries(roles.map((r) => [r.id, r.name]));
  const teamMap = Object.fromEntries(teams.map((t) => [t.id, t.name]));
  const userMap = Object.fromEntries(items.map((u) => [u.id, u.full_name || u.email]));
  const getRoleNames = (roleIds: string[]) =>
    roleIds?.map((id) => roleMap[id]).filter(Boolean).join(", ") || "—";

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-white">Users</h1>
        <button
          onClick={openNew}
          className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover"
        >
          Add user
        </button>
      </div>

      {loading ? (
        <p className="text-slate-400">Loading...</p>
      ) : (
        <div className="rounded-xl border border-slate-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-800 text-left text-sm text-slate-400">
              <tr>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Active</th>
                <th className="px-4 py-3">Manager</th>
                <th className="px-4 py-3">Roles</th>
                <th className="px-4 py-3">Teams</th>
                <th className="px-4 py-3 w-24"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {items.map((u) => (
                <tr key={u.id} className="hover:bg-slate-800/50">
                  <td className="px-4 py-3 text-white">{u.email}</td>
                  <td className="px-4 py-3 text-slate-300">{u.full_name || "—"}</td>
                  <td className="px-4 py-3 text-slate-300">{u.is_active ? "Yes" : "No"}</td>
                  <td className="px-4 py-3 text-slate-300 text-sm">
                    {u.manager_id ? userMap[u.manager_id] || "—" : "—"}
                  </td>
                  <td className="px-4 py-3 text-slate-300 text-sm">
                    {getRoleNames(u.role_ids || [])}
                  </td>
                  <td className="px-4 py-3 text-slate-300 text-sm">
                    {u.team_ids?.length
                      ? u.team_ids.map((id) => teamMap[id]).filter(Boolean).join(", ") || `${u.team_ids.length} team(s)`
                      : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => openEdit(u)} className="text-primary hover:underline mr-2">
                      Edit
                    </button>
                    <button onClick={() => remove(u.id)} className="text-red-400 hover:underline">
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
            className="bg-slate-800 rounded-xl border border-slate-700 p-6 w-full max-w-md max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-white mb-4">
              {modal === "new" ? "New user" : "Edit user"}
            </h2>
            <div className="space-y-3">
              <input
                placeholder="Email"
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                disabled={modal !== "new"}
              />
              {modal === "new" && (
                <input
                  placeholder="Password"
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                />
              )}
              <input
                placeholder="Full name"
                value={form.full_name}
                onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
              <label className="flex items-center gap-2 text-slate-300">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))}
                  className="rounded"
                />
                Active
              </label>
              <div>
                <label className="text-sm text-slate-400 block mb-1">Manager</label>
                <select
                  value={form.manager_id ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, manager_id: e.target.value || null }))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
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
                <p className="text-xs text-slate-500 mt-1">
                  Team members under this manager will show up in their Team activity.
                </p>
              </div>
              <div>
                <span className="text-sm text-slate-400 block mb-1">Roles (select all that apply)</span>
                <p className="text-xs text-slate-500 mb-2">
                  Multiple roles are supported—e.g. one person can be both PM and Developer in small teams.
                </p>
                <div className="flex flex-wrap gap-2">
                  {roles.map((r) => (
                    <label key={r.id} className="flex items-center gap-1 text-sm text-slate-300">
                      <input
                        type="checkbox"
                        checked={form.role_ids.includes(r.id)}
                        onChange={() => toggleRole(r.id)}
                        className="rounded"
                      />
                      {r.name}
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <span className="text-sm text-slate-400 block mb-1">Teams (select all that apply)</span>
                <div className="flex flex-wrap gap-2">
                  {teams.map((t) => (
                    <label key={t.id} className="flex items-center gap-1 text-sm text-slate-300">
                      <input
                        type="checkbox"
                        checked={form.team_ids.includes(t.id)}
                        onChange={() => toggleTeam(t.id)}
                        className="rounded"
                      />
                      {t.name}
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
