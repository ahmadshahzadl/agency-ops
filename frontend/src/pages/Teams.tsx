import { useEffect, useMemo, useState } from "react";
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
  const [memberSearch, setMemberSearch] = useState("");
  const [form, setForm] = useState({ name: "", description: "" });
  const [search, setSearch] = useState("");

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

  const filteredItems = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (t) =>
        (t.name || "").toLowerCase().includes(q) ||
        (t.description || "").toLowerCase().includes(q)
    );
  }, [items, search]);

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
      const team = items.find((x) => x.id === teamId);
      if (memberModal && team && teamId === memberModal.id) {
        setMemberModal({ ...memberModal, user_ids: [...(memberModal.user_ids ?? []), userId] });
      }
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const removeMember = async (teamId: string, userId: string) => {
    try {
      await removeTeamMember(teamId, userId);
      load();
      if (memberModal && memberModal.id === teamId) {
        setMemberModal({
          ...memberModal,
          user_ids: (memberModal.user_ids ?? []).filter((id) => id !== userId),
        });
      }
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const memberIds = memberModal ? (memberModal.user_ids ?? []) : [];
  const memberSearchLower = memberSearch.trim().toLowerCase();
  const usersToAdd = useMemo(
    () =>
      users.filter((u) => {
        if (memberIds.includes(u.id)) return false;
        if (!memberSearchLower) return true;
        const name = (u.full_name || "").toLowerCase();
        const email = (u.email || "").toLowerCase();
        return name.includes(memberSearchLower) || email.includes(memberSearchLower);
      }),
    [users, memberIds, memberSearchLower]
  );
  const currentMembersFiltered = useMemo(() => {
    if (!memberSearchLower) return memberIds;
    return memberIds.filter((uid) => {
      const u = users.find((x) => x.id === uid);
      const name = (u?.full_name || "").toLowerCase();
      const email = (u?.email || "").toLowerCase();
      return name.includes(memberSearchLower) || email.includes(memberSearchLower);
    });
  }, [memberIds, users, memberSearchLower]);

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
            placeholder="Search teams by name or description..."
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>
        <button
          onClick={openNew}
          className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover whitespace-nowrap"
        >
          Add team
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
                <th className="px-4 py-3">Members</th>
                <th className="px-4 py-3 w-40 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-gray-500">
                    {search ? "No teams match your search." : "No teams yet."}
                  </td>
                </tr>
              ) : (
                filteredItems.map((t) => {
                  const count = t.user_ids?.length ?? 0;
                  return (
                    <tr key={t.id} className="hover:bg-gray-50/80">
                      <td className="px-4 py-3 font-medium text-gray-900">{t.name}</td>
                      <td className="px-4 py-3 text-gray-600">{t.description || "—"}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center justify-center min-w-[1.75rem] h-7 px-2 rounded-full bg-gray-100 text-gray-700 text-sm font-medium">
                            {count}
                          </span>
                          <button
                            type="button"
                            onClick={() => {
                              setMemberSearch("");
                              setMemberModal(t);
                            }}
                            title="Manage members"
                            className="text-sm font-medium text-primary hover:underline"
                          >
                            Manage
                          </button>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            type="button"
                            onClick={() => openEdit(t)}
                            title="Edit"
                            className="p-1.5 rounded-lg text-gray-500 hover:text-primary hover:bg-gray-100 transition-colors"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                            </svg>
                          </button>
                          <button
                            type="button"
                            onClick={() => remove(t.id)}
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
                  );
                })
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
            className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-md"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              {modal === "new" ? "New team" : "Edit team"}
            </h2>
            <div className="space-y-3">
              <div>
                <label className={labelClass}>Name</label>
                <input
                  placeholder="Team name"
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

      {memberModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-10"
          onClick={() => { setMemberModal(null); setMemberSearch(""); }}
        >
          <div
            className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-gray-900 mb-1">Team: {memberModal.name}</h2>
            <p className="text-sm text-gray-600 mb-4">Add or remove members</p>

            <div className="mb-4">
              <input
                type="text"
                value={memberSearch}
                onChange={(e) => setMemberSearch(e.target.value)}
                placeholder="Search users by name or email..."
                className={inputClass}
              />
            </div>

            <div className="space-y-2 mb-4">
              <p className={labelClass}>Add member</p>
              {usersToAdd.length === 0 ? (
                <p className="text-gray-500 text-sm py-2">
                  {memberSearch ? "No users match your search." : "All users are in this team."}
                </p>
              ) : (
                usersToAdd.map((u) => (
                  <div key={u.id} className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-gray-50">
                    <span className="text-gray-700">{u.full_name || u.email}</span>
                    <button
                      type="button"
                      onClick={() => addMember(memberModal.id, u.id)}
                      className="text-sm font-medium text-primary hover:underline"
                    >
                      Add
                    </button>
                  </div>
                ))
              )}
            </div>
            <div className="border-t border-gray-200 pt-4">
              <p className={labelClass}>Current members ({memberIds.length})</p>
              {memberIds.length === 0 ? (
                <p className="text-gray-500 text-sm">No members</p>
              ) : (
                <div className="space-y-2">
                  {currentMembersFiltered.length === 0 ? (
                    <p className="text-gray-500 text-sm">
                      {memberSearch ? "No current members match your search." : "No members."}
                    </p>
                  ) : (
                    currentMembersFiltered.map((uid) => {
                      const u = users.find((x) => x.id === uid);
                      return (
                        <div key={uid} className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-gray-50">
                          <span className="text-gray-700">{(u?.full_name || u?.email) ?? uid}</span>
                          <button
                            type="button"
                            onClick={() => removeMember(memberModal.id, uid)}
                            className="text-sm font-medium text-red-600 hover:underline"
                          >
                            Remove
                          </button>
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </div>
            <div className="flex justify-end mt-4">
              <button
                onClick={() => { setMemberModal(null); setMemberSearch(""); }}
                className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium"
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
