import { useEffect, useState } from "react";
import { listProjects, createProject, updateProject, deleteProject, type Project } from "@/api/projects";
import { listClients, type Client } from "@/api/clients";
import { listTeams, listMyTeams } from "@/api/teams";
import { useAuth } from "@/store/auth";
import { NotesSection } from "@/components/NotesSection";
import { AttachmentsSection } from "@/components/AttachmentsSection";
import { useModal } from "@/contexts/ModalContext";
import { BulkActionsBar } from "@/components/BulkActionsBar";

const PIPELINE_STAGES = ["lead", "discovery", "proposal", "scoping", "design", "development", "qa", "deployment", "handover", "support"];
const PROJECT_STATUS_OPTIONS = ["draft", "active", "on_hold", "completed"];

export default function Projects() {
  const { showConfirm, showAlert } = useModal();
  const [items, setItems] = useState<Project[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [teams, setTeams] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [clientFilter, setClientFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [searchText, setSearchText] = useState("");
  const [pipelineStageFilter, setPipelineStageFilter] = useState("");
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
  const canBulk = hasPermission("admin:all");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);

  const load = () => {
    const teamList = isAdmin ? listTeams() : listMyTeams();
    const needsClients = hasPermission("clients:read") || hasPermission("projects:write");
    const params: { client_id?: string; status_filter?: string } = {};
    if (clientFilter) params.client_id = clientFilter;
    if (statusFilter) params.status_filter = statusFilter;
    const projectPromise = listProjects(Object.keys(params).length ? params : undefined);
    if (needsClients) {
      Promise.all([projectPromise, listClients(), teamList]).then(([p, c, t]) => {
        setItems(p);
        setClients(c);
        setTeams(t);
      }).finally(() => setLoading(false));
    } else {
      Promise.all([projectPromise, teamList]).then(([p, t]) => {
        setItems(p);
        setTeams(t);
      }).finally(() => setLoading(false));
    }
  };

  useEffect(() => {
    load();
  }, [isAdmin, clientFilter, statusFilter]);

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
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    }
  };

  const remove = (id: string) => {
    showConfirm({
      title: "Delete project",
      message: "Delete this project?",
      confirmLabel: "Delete",
      variant: "danger",
      onConfirm: async () => {
        try {
          await deleteProject(id);
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
    else setSelectedIds(new Set(filteredItems.map((p) => p.id)));
  };
  const bulkDelete = () => {
    const ids = Array.from(selectedIds);
    showConfirm({
      title: "Delete projects",
      message: `Delete ${ids.length} project(s)? This cannot be undone.`,
      confirmLabel: "Delete all",
      variant: "danger",
      onConfirm: async () => {
        setBulkDeleting(true);
        try {
          for (const id of ids) {
            try {
              await deleteProject(id);
            } catch (e) {
              showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed to delete project" });
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

  const canWrite = hasPermission("projects:write");
  const clientMap = Object.fromEntries(clients.map((c) => [c.id, c.name]));
  const teamMap = Object.fromEntries(teams.map((t) => [t.id, t.name]));
  const searchLower = searchText.trim().toLowerCase();
  const filteredItems = items.filter((p) => {
    if (searchLower) {
      const nameMatch = (p.name ?? "").toLowerCase().includes(searchLower);
      const clientName = (p.client_name ?? clientMap[p.client_id] ?? "").toLowerCase();
      if (!nameMatch && !clientName.includes(searchLower)) return false;
    }
    if (pipelineStageFilter && (p.pipeline_stage || "") !== pipelineStageFilter) return false;
    return true;
  });
  const inputClass = "w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <label className="text-sm font-medium text-gray-700">Client</label>
          <select
            value={clientFilter}
            onChange={(e) => setClientFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[160px]"
          >
            <option value="">All clients</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <label className="text-sm font-medium text-gray-700">Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[120px]"
          >
            <option value="">All statuses</option>
            {PROJECT_STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>{s.replace("_", " ")}</option>
            ))}
          </select>
          <label className="text-sm font-medium text-gray-700">Stage</label>
          <select
            value={pipelineStageFilter}
            onChange={(e) => setPipelineStageFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[120px]"
          >
            <option value="">All stages</option>
            {PIPELINE_STAGES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <label className="text-sm font-medium text-gray-700">Search</label>
          <input
            type="search"
            placeholder="Project or client name..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[180px]"
          />
        </div>
        {canWrite && (
          <button
            onClick={openNew}
            className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover shadow-sm"
          >
            Add project
          </button>
        )}
      </div>

      {canBulk && (
        <BulkActionsBar
          selectedCount={selectedIds.size}
          entityName="projects"
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
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Client</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Stage</th>
                <th className="px-4 py-3">Progress</th>
                <th className="px-4 py-3">Assigned team</th>
                {canWrite && <th className="px-4 py-3 w-24 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredItems.map((p) => {
                const total = p.task_count ?? 0;
                const done = p.task_done_count ?? 0;
                const pct = total > 0 ? Math.round((done / total) * 100) : 0;
                return (
                <tr key={p.id} className={`hover:bg-gray-50/80 ${selectedIds.has(p.id) ? "bg-primary/5" : ""}`}>
                  {canBulk && (
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(p.id)}
                        onChange={() => toggleSelect(p.id)}
                        className="rounded border-gray-300 text-primary focus:ring-primary/20"
                      />
                    </td>
                  )}
                  <td className="px-4 py-3 font-medium text-gray-900">{p.name}</td>
                  <td className="px-4 py-3 text-gray-600">{p.client_name ?? clientMap[p.client_id] ?? p.client_id}</td>
                  <td className="px-4 py-3 text-gray-600">{p.status}</td>
                  <td className="px-4 py-3 text-gray-600">{p.pipeline_stage || "—"}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {total > 0 ? (
                      <span className="flex items-center gap-2">
                        <span className="w-16 bg-gray-200 rounded-full h-2 block overflow-hidden">
                          <span className="bg-primary h-full block rounded-full transition-all" style={{ width: `${pct}%` }} />
                        </span>
                        <span>{done}/{total} ({pct}%)</span>
                      </span>
                    ) : "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{p.assigned_team_id ? teamMap[p.assigned_team_id] || "—" : "—"}</td>
                  {canWrite && (
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button type="button" onClick={() => openEdit(p)} title="Edit" className="p-1.5 rounded-lg text-gray-500 hover:text-primary hover:bg-gray-100 transition-colors">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                        <button type="button" onClick={() => remove(p.id)} title="Delete" className="p-1.5 rounded-lg text-gray-500 hover:text-red-600 hover:bg-gray-100 transition-colors">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              );
              })}
            </tbody>
          </table>
        </div>
      )}

      {modal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-10" onClick={() => setModal(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">{modal === "new" ? "New project" : "Edit project"}</h2>
            <div className="space-y-3">
              <div>
                <label className={labelClass}>Client</label>
                <select value={form.client_id} onChange={(e) => setForm((f) => ({ ...f, client_id: e.target.value }))} className={inputClass}>
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
              <input placeholder="Name" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} className={inputClass} />
              <textarea placeholder="Description" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} className={inputClass} rows={2} />
              <select value={form.status} onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))} className={inputClass}>
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="on_hold">On hold</option>
                <option value="completed">Completed</option>
              </select>
              <div>
                <label className={labelClass}>Pipeline stage</label>
                <select value={form.pipeline_stage} onChange={(e) => setForm((f) => ({ ...f, pipeline_stage: e.target.value }))} className={inputClass}>
                  {PIPELINE_STAGES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelClass}>Assigned team (owner of this stage)</label>
                <select value={form.assigned_team_id ?? ""} onChange={(e) => setForm((f) => ({ ...f, assigned_team_id: e.target.value || null }))} className={inputClass}>
                  <option value="">— None —</option>
                  {teams.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input type="date" value={form.start_date} onChange={(e) => setForm((f) => ({ ...f, start_date: e.target.value }))} className={inputClass} />
                <input type="date" value={form.end_date} onChange={(e) => setForm((f) => ({ ...f, end_date: e.target.value }))} className={inputClass} />
              </div>
            </div>
            <NotesSection entityType="project" entityId={modal !== "new" ? (modal as Project).id : undefined} />
            <AttachmentsSection entityType="project" entityId={modal !== "new" ? (modal as Project).id : undefined} />
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">Cancel</button>
              <button onClick={save} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
