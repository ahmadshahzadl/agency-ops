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
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-white">Clients</h1>
        {canWrite && (
          <button
            onClick={openNew}
            className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover"
          >
            Add client
          </button>
        )}
      </div>

      {loading ? (
        <p className="text-slate-400">Loading...</p>
      ) : (
        <div className="rounded-xl border border-slate-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-slate-800 text-left text-sm text-slate-400">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Phone</th>
                {isAdmin && <th className="px-4 py-3">Team</th>}
                {canWrite && <th className="px-4 py-3 w-24"></th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {items.map((c) => (
                <tr key={c.id} className="hover:bg-slate-800/50">
                  <td className="px-4 py-3 text-white">{c.name}</td>
                  <td className="px-4 py-3 text-slate-300">{c.contact_email || "—"}</td>
                  <td className="px-4 py-3 text-slate-300">{c.contact_phone || "—"}</td>
                  {isAdmin && (
                    <td className="px-4 py-3 text-slate-300">
                      {c.team_id ? teams.find((t) => t.id === c.team_id)?.name ?? "—" : "—"}
                    </td>
                  )}
                  {canWrite && (
                    <td className="px-4 py-3">
                      <button onClick={() => openEdit(c)} className="text-primary hover:underline mr-2">
                        Edit
                      </button>
                      <button onClick={() => remove(c.id)} className="text-red-400 hover:underline">
                        Delete
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-10" onClick={() => setModal(null)}>
          <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-white mb-4">{modal === "new" ? "New client" : "Edit client"}</h2>
            <div className="space-y-3">
              <input
                placeholder="Name"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
              <input
                placeholder="Email"
                type="email"
                value={form.contact_email}
                onChange={(e) => setForm((f) => ({ ...f, contact_email: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
              <input
                placeholder="Phone"
                value={form.contact_phone}
                onChange={(e) => setForm((f) => ({ ...f, contact_phone: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
              <textarea
                placeholder="Address"
                value={form.address}
                onChange={(e) => setForm((f) => ({ ...f, address: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                rows={2}
              />
              {isAdmin && (
                <div>
                  <label className="text-sm text-slate-400 block mb-1">Team</label>
                  <select
                    value={form.team_id ?? ""}
                    onChange={(e) => setForm((f) => ({ ...f, team_id: e.target.value || null }))}
                    className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
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
