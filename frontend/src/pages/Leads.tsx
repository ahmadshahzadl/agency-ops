import { useEffect, useState } from "react";
import {
  listLeads,
  createLead,
  updateLead,
  convertLead,
  deleteLead,
  type Lead,
} from "@/api/leads";
import { listTeams, listMyTeams } from "@/api/teams";
import { useAuth } from "@/store/auth";

const PIPELINE_STAGES = [
  "lead",
  "discovery",
  "proposal",
  "scoping",
  "design",
  "development",
  "qa",
  "deployment",
  "handover",
  "support",
];

export default function Leads() {
  const [items, setItems] = useState<Lead[]>([]);
  const [teams, setTeams] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<"new" | Lead | null>(null);
  const [convertModal, setConvertModal] = useState<Lead | null>(null);
  const [form, setForm] = useState({
    company_name: "",
    contact_name: "",
    contact_email: "",
    contact_phone: "",
    source: "",
    status: "new",
    notes: "",
    assigned_team_id: "" as string | null,
  });
  const [convertForm, setConvertForm] = useState({
    client_team_id: "" as string | null,
    create_project: true,
    project_name: "",
    project_pipeline_stage: "discovery",
    project_assigned_team_id: "" as string | null,
  });
  const { hasPermission } = useAuth();
  const isAdmin = hasPermission("admin:all");

  const load = async () => {
    setLoading(true);
    try {
      const teamList = isAdmin ? await listTeams() : await listMyTeams();
      const leadList = await listLeads();
      setItems(leadList);
      setTeams(teamList);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [isAdmin]);

  const openNew = () => {
    setForm({
      company_name: "",
      contact_name: "",
      contact_email: "",
      contact_phone: "",
      source: "",
      status: "new",
      notes: "",
      assigned_team_id: null,
    });
    setModal("new");
  };

  const openEdit = (l: Lead) => {
    setForm({
      company_name: l.company_name,
      contact_name: l.contact_name || "",
      contact_email: l.contact_email || "",
      contact_phone: l.contact_phone || "",
      source: l.source || "",
      status: l.status,
      notes: l.notes || "",
      assigned_team_id: l.assigned_team_id || null,
    });
    setModal(l);
  };

  const openConvert = (l: Lead) => {
    setConvertForm({
      client_team_id: l.assigned_team_id || null,
      create_project: true,
      project_name: l.company_name,
      project_pipeline_stage: "discovery",
      project_assigned_team_id: null,
    });
    setConvertModal(l);
  };

  const save = async () => {
    if (modal === null) return;
    try {
      if (modal === "new") {
        await createLead({
          ...form,
          assigned_team_id: form.assigned_team_id || undefined,
        });
      } else {
        await updateLead(modal.id, {
          ...form,
          assigned_team_id: form.assigned_team_id,
        });
      }
      setModal(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const handleConvert = async () => {
    if (!convertModal) return;
    try {
      await convertLead(convertModal.id, {
        client_team_id: convertForm.client_team_id || undefined,
        create_project: convertForm.create_project,
        project_name: convertForm.project_name || undefined,
        project_pipeline_stage: convertForm.project_pipeline_stage,
        project_assigned_team_id: convertForm.project_assigned_team_id || undefined,
      });
      setConvertModal(null);
      load();
      alert("Lead converted to client. You can open Clients and Projects to see the new records.");
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Delete this lead?")) return;
    try {
      await deleteLead(id);
      setModal(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const canWrite = hasPermission("leads:write");
  const teamMap = Object.fromEntries(teams.map((t) => [t.id, t.name]));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-white">Leads</h1>
        {canWrite && (
          <button
            onClick={openNew}
            className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover"
          >
            Add lead
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
                <th className="px-4 py-3">Company</th>
                <th className="px-4 py-3">Contact</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Team</th>
                <th className="px-4 py-3">Converted</th>
                {canWrite && <th className="px-4 py-3 w-40"></th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {items.map((l) => (
                <tr key={l.id} className="hover:bg-slate-800/50">
                  <td className="px-4 py-3 text-white">{l.company_name}</td>
                  <td className="px-4 py-3 text-slate-300">
                    {l.contact_name || l.contact_email || "—"}
                  </td>
                  <td className="px-4 py-3 text-slate-300">{l.status}</td>
                  <td className="px-4 py-3 text-slate-300">
                    {l.assigned_team_id ? teamMap[l.assigned_team_id] || "—" : "—"}
                  </td>
                  <td className="px-4 py-3 text-slate-300">
                    {l.converted_to_client_id ? "Yes" : "—"}
                  </td>
                  {canWrite && (
                    <td className="px-4 py-3">
                      {!l.converted_to_client_id && (
                        <>
                          <button onClick={() => openEdit(l)} className="text-primary hover:underline mr-2">
                            Edit
                          </button>
                          <button onClick={() => openConvert(l)} className="text-green-400 hover:underline mr-2">
                            Convert
                          </button>
                        </>
                      )}
                      <button onClick={() => remove(l.id)} className="text-red-400 hover:underline">
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
        <div
          className="fixed inset-0 bg-black/60 flex items-center justify-center z-10"
          onClick={() => setModal(null)}
        >
          <div
            className="bg-slate-800 rounded-xl border border-slate-700 p-6 w-full max-w-md max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-white mb-4">
              {modal === "new" ? "New lead" : "Edit lead"}
            </h2>
            <div className="space-y-3">
              <input
                placeholder="Company name *"
                value={form.company_name}
                onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
              <input
                placeholder="Contact name"
                value={form.contact_name}
                onChange={(e) => setForm((f) => ({ ...f, contact_name: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
              <input
                placeholder="Contact email"
                type="email"
                value={form.contact_email}
                onChange={(e) => setForm((f) => ({ ...f, contact_email: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
              <input
                placeholder="Contact phone"
                value={form.contact_phone}
                onChange={(e) => setForm((f) => ({ ...f, contact_phone: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
              <input
                placeholder="Source (e.g. website, referral)"
                value={form.source}
                onChange={(e) => setForm((f) => ({ ...f, source: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
              <select
                value={form.status}
                onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              >
                <option value="new">New</option>
                <option value="contacted">Contacted</option>
                <option value="qualified">Qualified</option>
                <option value="lost">Lost</option>
              </select>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Assigned team</label>
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
              <textarea
                placeholder="Notes"
                value={form.notes}
                onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                rows={2}
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

      {convertModal && (
        <div
          className="fixed inset-0 bg-black/60 flex items-center justify-center z-10"
          onClick={() => setConvertModal(null)}
        >
          <div
            className="bg-slate-800 rounded-xl border border-slate-700 p-6 w-full max-w-md"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-white mb-2">Convert to client</h2>
            <p className="text-sm text-slate-400 mb-4">
              Create a client and optional project from &quot;{convertModal.company_name}&quot;.
            </p>
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-slate-400 mb-1">Client team</label>
                <select
                  value={convertForm.client_team_id ?? ""}
                  onChange={(e) => setConvertForm((f) => ({ ...f, client_team_id: e.target.value || null }))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                >
                  <option value="">— Use lead team —</option>
                  {teams.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>
              <label className="flex items-center gap-2 text-slate-300">
                <input
                  type="checkbox"
                  checked={convertForm.create_project}
                  onChange={(e) => setConvertForm((f) => ({ ...f, create_project: e.target.checked }))}
                  className="rounded"
                />
                Create project
              </label>
              {convertForm.create_project && (
                <>
                  <input
                    placeholder="Project name"
                    value={convertForm.project_name}
                    onChange={(e) => setConvertForm((f) => ({ ...f, project_name: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                  />
                  <div>
                    <label className="block text-sm text-slate-400 mb-1">Pipeline stage</label>
                    <select
                      value={convertForm.project_pipeline_stage}
                      onChange={(e) => setConvertForm((f) => ({ ...f, project_pipeline_stage: e.target.value }))}
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
                      value={convertForm.project_assigned_team_id ?? ""}
                      onChange={(e) => setConvertForm((f) => ({ ...f, project_assigned_team_id: e.target.value || null }))}
                      className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                    >
                      <option value="">— None —</option>
                      {teams.map((t) => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                      ))}
                    </select>
                  </div>
                </>
              )}
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setConvertModal(null)} className="px-4 py-2 text-slate-400 hover:text-white">
                Cancel
              </button>
              <button onClick={handleConvert} className="px-4 py-2 rounded-lg bg-primary text-white font-medium">
                Convert
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
