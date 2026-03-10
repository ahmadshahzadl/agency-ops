import { useEffect, useState } from "react";
import { listClients, createClient, updateClient, deleteClient, type Client } from "@/api/clients";
import { listTeams } from "@/api/teams";
import { useAuth } from "@/store/auth";

export default function Clients() {
  const [items, setItems] = useState<Client[]>([]);
  const [teams, setTeams] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<"new" | Client | null>(null);
  const [form, setForm] = useState({
    name: "",
    contact_email: "",
    contact_phone: "",
    address: "",
    team_id: "" as string | null,
  });
  const { hasPermission } = useAuth();
  const isAdmin = hasPermission("admin:all");

  const load = async () => {
    setLoading(true);
    try {
      const [clientList, teamList] = await Promise.all([
        listClients(),
        isAdmin ? listTeams() : Promise.resolve([]),
      ]);
      setItems(clientList);
      setTeams(teamList);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [isAdmin]);

  const openNew = () => {
    setForm({ name: "", contact_email: "", contact_phone: "", address: "", team_id: null });
    setModal("new");
  };
  const openEdit = (c: Client) => {
    setForm({
      name: c.name,
      contact_email: c.contact_email || "",
      contact_phone: c.contact_phone || "",
      address: c.address || "",
      team_id: c.team_id || null,
    });
    setModal(c);
  };

  const save = async () => {
    if (modal === null) return;
    const payload = {
      name: form.name,
      contact_email: form.contact_email || null,
      contact_phone: form.contact_phone || null,
      address: form.address || null,
      ...(isAdmin && form.team_id ? { team_id: form.team_id } : {}),
    };
    try {
      if (modal === "new") {
        await createClient(payload);
      } else {
        await updateClient(modal.id, payload);
      }
      setModal(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Delete this client?")) return;
    try {
      await deleteClient(id);
      setModal(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const canWrite = hasPermission("clients:write");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-end">
        {canWrite && (
          <button
            onClick={openNew}
            className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover shadow-sm"
          >
            Add client
          </button>
        )}
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Phone</th>
                {isAdmin && <th className="px-4 py-3">Team</th>}
                {canWrite && <th className="px-4 py-3 w-24 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50/80">
                  <td className="px-4 py-3 font-medium text-gray-900">{c.name}</td>
                  <td className="px-4 py-3 text-gray-600">{c.contact_email || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{c.contact_phone || "—"}</td>
                  {isAdmin && (
                    <td className="px-4 py-3 text-gray-600">
                      {c.team_id ? teams.find((t) => t.id === c.team_id)?.name ?? "—" : "—"}
                    </td>
                  )}
                  {canWrite && (
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => openEdit(c)}
                          title="Edit"
                          className="p-1.5 rounded-lg text-gray-500 hover:text-primary hover:bg-gray-100 transition-colors"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          onClick={() => remove(c.id)}
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
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-10" onClick={() => setModal(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">{modal === "new" ? "New client" : "Edit client"}</h2>
            <div className="space-y-3">
              <input
                placeholder="Name"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
              <input
                placeholder="Email"
                type="email"
                value={form.contact_email}
                onChange={(e) => setForm((f) => ({ ...f, contact_email: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
              <input
                placeholder="Phone"
                value={form.contact_phone}
                onChange={(e) => setForm((f) => ({ ...f, contact_phone: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
              <textarea
                placeholder="Address"
                value={form.address}
                onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary/20 focus:border-primary"
                rows={2}
              />
              {isAdmin && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Team</label>
                  <select
                    value={form.team_id ?? ""}
                    onChange={(e) => setForm((f) => ({ ...f, team_id: e.target.value || null }))}
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  >
                    <option value="">— No team —</option>
                    {teams.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
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
