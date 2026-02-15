import { useEffect, useState } from "react";
import {
  listTeams,
  createTeam,
  updateTeam,
  deleteTeam,
  addTeamMember,
  removeTeamMember,
  type TeamWithMembers,
} from "@/api/teams";
import { listUsers, type UserList } from "@/api/users";

export default function Teams() {
  const [items, setItems] = useState<TeamWithMembers[]>([]);
  const [users, setUsers] = useState<UserList[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<"new" | TeamWithMembers | null>(null);
  const [memberModal, setMemberModal] = useState<TeamWithMembers | null>(null);
  const [form, setForm] = useState({ name: "", description: "" });

  const load = async () => {
    setLoading(true);
    try {
      const [teamList, userList] = await Promise.all([listTeams(), listUsers()]);
      setItems(teamList);
      setUsers(userList);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openNew = () => {
    setForm({ name: "", description: "" });
    setModal("new");
  };

  const openEdit = (t: TeamWithMembers) => {
    setForm({ name: t.name, description: t.description || "" });
    setModal(t);
  };

  const save = async () => {
    if (modal === null) return;
    try {
      if (modal === "new") {
        await createTeam(form);
      } else {
        await updateTeam(modal.id, form);
      }
      setModal(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Delete this team?")) return;
    try {
      await deleteTeam(id);
      setModal(null);
      setMemberModal(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const addMember = async (teamId: string, userId: string) => {
    try {
      await addTeamMember(teamId, userId);
      load();
      setMemberModal((m) => (m && m.id === teamId ? { ...m, user_ids: [...m.user_ids, userId] } : m));
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const removeMember = async (teamId: string, userId: string) => {
    try {
      await removeTeamMember(teamId, userId);
      load();
      setMemberModal((m) =>
        m && m.id === teamId ? { ...m, user_ids: m.user_ids.filter((id) => id !== userId) } : m
      );
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-white">Teams</h1>
        <button
          onClick={openNew}
          className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover"
        >
          Add team
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
                <th className="px-4 py-3">Members</th>
                <th className="px-4 py-3 w-48"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {items.map((t) => (
                <tr key={t.id} className="hover:bg-slate-800/50">
                  <td className="px-4 py-3 text-white">{t.name}</td>
                  <td className="px-4 py-3 text-slate-300">{t.description || "—"}</td>
                  <td className="px-4 py-3 text-slate-300">
                    {t.user_ids?.length ?? 0} member(s)
                    <button
                      onClick={() => setMemberModal(t)}
                      className="ml-2 text-primary hover:underline text-sm"
                    >
                      Manage
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => openEdit(t)} className="text-primary hover:underline mr-2">
                      Edit
                    </button>
                    <button onClick={() => remove(t.id)} className="text-red-400 hover:underline">
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
            className="bg-slate-800 rounded-xl border border-slate-700 p-6 w-full max-w-md"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-white mb-4">
              {modal === "new" ? "New team" : "Edit team"}
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

      {memberModal && (
        <div
          className="fixed inset-0 bg-black/60 flex items-center justify-center z-10"
          onClick={() => setMemberModal(null)}
        >
          <div
            className="bg-slate-800 rounded-xl border border-slate-700 p-6 w-full max-w-md max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-white mb-2">Team: {memberModal.name}</h2>
            <p className="text-sm text-slate-400 mb-4">Add or remove members</p>
            <div className="space-y-2 mb-4">
              {users
                .filter((u) => !memberModal.user_ids.includes(u.id))
                .map((u) => (
                  <div key={u.id} className="flex items-center justify-between py-1">
                    <span className="text-slate-300">{u.email}</span>
                    <button
                      onClick={() => addMember(memberModal.id, u.id)}
                      className="text-primary hover:underline text-sm"
                    >
                      Add
                    </button>
                  </div>
                ))}
              {users.filter((u) => !memberModal.user_ids.includes(u.id)).length === 0 && (
                <p className="text-slate-500 text-sm">All users are in this team</p>
              )}
            </div>
            <div className="border-t border-slate-700 pt-4">
              <p className="text-sm text-slate-400 mb-2">Current members</p>
              {memberModal.user_ids.length === 0 ? (
                <p className="text-slate-500 text-sm">No members</p>
              ) : (
                <div className="space-y-2">
                  {memberModal.user_ids.map((uid) => {
                    const u = users.find((x) => x.id === uid);
                    return (
                      <div key={uid} className="flex items-center justify-between py-1">
                        <span className="text-slate-300">{u?.email ?? uid}</span>
                        <button
                          onClick={() => removeMember(memberModal.id, uid)}
                          className="text-red-400 hover:underline text-sm"
                        >
                          Remove
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
            <div className="flex justify-end mt-4">
              <button
                onClick={() => setMemberModal(null)}
                className="px-4 py-2 text-slate-400 hover:text-white"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
