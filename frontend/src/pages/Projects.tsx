import { useEffect, useState } from "react";
import { listProjects, createProject, updateProject, deleteProject, type Project } from "@/api/projects";
import { listClients, type Client } from "@/api/clients";
import { listTeams, listMyTeams } from "@/api/teams";
import { useAuth } from "@/store/auth";

const PIPELINE_STAGES = ["lead", "discovery", "proposal", "scoping", "design", "development", "qa", "deployment", "handover", "support"];

export default function Projects() {
  const [items, setItems] = useState<Project[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [teams, setTeams] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<"new" | Project | null>(null);
  const [form, setForm] = useState({
    client_id: "",
    name: "",
    description: "",
    status: "draft",
    pipeline_stage: "lead",
    assigned_team_id: "" as string | null,
    start_date: "",
    end_date: "",
  });
  const { hasPermission } = useAuth();
  const isAdmin = hasPermission("admin:all");

  const load = () => {
    const teamList = isAdmin ? listTeams() : listMyTeams();
    Promise.all([listProjects(), listClients(), teamList]).then(([p, c, t]) => {
      setItems(p);
      setClients(c);
      setTeams(t);
    }).finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [isAdmin]);

  const openNew = () => {
    setForm({
      client_id: clients[0]?.id || "",
      name: "",
      description: "",
      status: "draft",
      pipeline_stage: "lead",
      assigned_team_id: null,
      start_date: "",
      end_date: "",
    });
    setModal("new");
  };
  const openEdit = (p: Project) => {
    setForm({
      client_id: p.client_id,
      name: p.name,
      description: p.description || "",
      status: p.status,
      pipeline_stage: p.pipeline_stage || "lead",
      assigned_team_id: p.assigned_team_id || null,
      start_date: p.start_date || "",
      end_date: p.end_date || "",
    });
    setModal(p);
  };

  const save = async () => {
    if (modal === null) return;
    const payload = {
      client_id: form.client_id,
      name: form.name,
      description: form.description || null,
      status: form.status,
      pipeline_stage: form.pipeline_stage || null,
      assigned_team_id: form.assigned_team_id || null,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
    };
    try {
      if (modal === "new") {
        await createProject(payload as Project);
      } else {
        await updateProject(modal.id, payload);
      }
      setModal(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Delete this project?")) return;
    try {
      await deleteProject(id);
      setModal(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const canWrite = hasPermission("projects:write");
  const clientMap = Object.fromEntries(clients.map((c) => [c.id, c.name]));
  const teamMap = Object.fromEntries(teams.map((t) => [t.id, t.name]));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-white">Projects</h1>
        {canWrite && (
          <button
            onClick={openNew}
            className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover"
          >
            Add project
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
                <th className="px-4 py-3">Client</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Stage</th>
                <th className="px-4 py-3">Assigned team</th>
                {canWrite && <th className="px-4 py-3 w-24"></th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {items.map((p) => (
                <tr key={p.id} className="hover:bg-slate-800/50">
                  <td className="px-4 py-3 text-white">{p.name}</td>
                  <td className="px-4 py-3 text-slate-300">{clientMap[p.client_id] || p.client_id}</td>
                  <td className="px-4 py-3 text-slate-300">{p.status}</td>
                  <td className="px-4 py-3 text-slate-300">{p.pipeline_stage || "—"}</td>
                  <td className="px-4 py-3 text-slate-300">{p.assigned_team_id ? teamMap[p.assigned_team_id] || "—" : "—"}</td>
                  {canWrite && (
                    <td className="px-4 py-3">
                      <button onClick={() => openEdit(p)} className="text-primary hover:underline mr-2">
                        Edit
                      </button>
                      <button onClick={() => remove(p.id)} className="text-red-400 hover:underline">
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
            <h2 className="text-lg font-semibold text-white mb-4">{modal === "new" ? "New project" : "Edit project"}</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-slate-400 mb-1">Client</label>
                <select
                  value={form.client_id}
                  onChange={(e) => setForm((f) => ({ ...f, client_id: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                >
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
              <input
                placeholder="Name"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
              <textarea
                placeholder="Description"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                rows={2}
              />
              <select
                value={form.status}
                onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              >
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="on_hold">On hold</option>
                <option value="completed">Completed</option>
              </select>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Pipeline stage</label>
                <select
                  value={form.pipeline_stage}
                  onChange={(e) => setForm((f) => ({ ...f, pipeline_stage: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                >
                  {PIPELINE_STAGES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Assigned team (owner of this stage)</label>
                <select
                  value={form.assigned_team_id ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, assigned_team_id: e.target.value || null }))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                >
                  <option value="">— None —</option>
                  {teams.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="date"
                  placeholder="Start"
                  value={form.start_date}
                  onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))}
                  className="px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                />
                <input
                  type="date"
                  placeholder="End"
                  value={form.end_date}
                  onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))}
                  className="px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                />
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
