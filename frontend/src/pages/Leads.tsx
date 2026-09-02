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
import { NotesSection } from "@/components/NotesSection";
import { AttachmentsSection } from "@/components/AttachmentsSection";
import { useModal } from "@/contexts/ModalContext";
import { BulkActionsBar } from "@/components/BulkActionsBar";

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
const LEAD_STATUS_OPTIONS = ["new", "contacted", "qualified", "converted", "lost", "closed", "dead"];

export default function Leads() {
  const [items, setItems] = useState<Lead[]>([]);
  const [teams, setTeams] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [localSearch, setLocalSearch] = useState("");
  const [modal, setModal] = useState<"new" | Lead | null>(null);
  const [convertModal, setConvertModal] = useState<Lead | null>(null);
  const [markLostModal, setMarkLostModal] = useState<Lead | null>(null);
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
  const { hasPermission, user } = useAuth();
  const { showConfirm, showAlert } = useModal();
  const isAdmin = hasPermission("admin:all");
  const canBulk = hasPermission("admin:all");
  const canManageLeads = user?.can_manage_leads ?? false; // manager or admin: create client/project, edit converted/closed
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const teamList = isAdmin ? await listTeams() : await listMyTeams();
      const params: { q?: string; status?: string } = {};
      if (searchQuery.trim()) params.q = searchQuery.trim();
      if (statusFilter) params.status = statusFilter;
      const leadList = await listLeads(Object.keys(params).length ? params : undefined);
      setItems(leadList);
      setTeams(teamList);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const t = setTimeout(() => setSearchQuery(searchInput), 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  useEffect(() => {
    load();
  }, [isAdmin, searchQuery, statusFilter]);

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
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
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
      showAlert({ title: "Success", message: "Lead converted to client. You can open Clients and Projects to see the new records." });
    } catch (e: unknown) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
      load(); // refresh so any backend "marked as lost" is visible
    }
  };

  const handleMarkLost = async (status: "lost" | "closed" | "dead") => {
    if (!markLostModal) return;
    try {
      await updateLead(markLostModal.id, { status });
      setMarkLostModal(null);
      load();
    } catch (e: unknown) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    }
  };

  const handleMarkAsConverted = async (l: Lead) => {
    try {
      await updateLead(l.id, { status: "converted" });
      load();
      showAlert({ title: "Success", message: "Lead marked as converted. Management will create the client and project." });
    } catch (e: unknown) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    }
  };

  const canWrite = hasPermission("leads:write");
  const lockedForMember = (l: Lead) => l.status === "converted" || l.status === "closed";
  const memberCanEdit = (l: Lead) => canWrite && !canManageLeads && !lockedForMember(l);
  const managementCanEdit = (_lead: Lead) => canWrite && canManageLeads;

  const remove = (id: string) => {
    showConfirm({
      title: "Delete lead",
      message: "Delete this lead?",
      confirmLabel: "Delete",
      variant: "danger",
      onConfirm: async () => {
        try {
          await deleteLead(id);
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
    else setSelectedIds(new Set(filteredItems.map((l) => l.id)));
  };
  const bulkDelete = () => {
    const ids = Array.from(selectedIds);
    showConfirm({
      title: "Delete leads",
      message: `Delete ${ids.length} lead(s)? This cannot be undone.`,
      confirmLabel: "Delete all",
      variant: "danger",
      onConfirm: async () => {
        setBulkDeleting(true);
        try {
          for (const id of ids) {
            try {
              await deleteLead(id);
            } catch (e) {
              showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed to delete lead" });
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

  const teamMap = Object.fromEntries(teams.map((t) => [t.id, t.name]));
  const sourceOptions = Array.from(new Set(items.map((l) => l.source?.trim() || "Unknown").filter(Boolean))).sort();
  const localLower = localSearch.trim().toLowerCase();
  const filteredItems = items.filter((l) => {
    if (sourceFilter && (l.source?.trim() || "Unknown") !== sourceFilter) return false;
    if (localLower) {
      const company = (l.company_name ?? "").toLowerCase();
      const contact = (l.contact_name ?? "").toLowerCase();
      const email = (l.contact_email ?? "").toLowerCase();
      const notes = (l.notes ?? "").toLowerCase();
      if (!company.includes(localLower) && !contact.includes(localLower) && !email.includes(localLower) && !notes.includes(localLower))
        return false;
    }
    return true;
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <label className="text-sm font-medium text-gray-700">Search</label>
          <input
            type="search"
            placeholder="Company, contact, email..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[200px]"
          />
          <label className="text-sm font-medium text-gray-700">Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[120px]"
          >
            <option value="">All statuses</option>
            {LEAD_STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <label className="text-sm font-medium text-gray-700">Source</label>
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[120px]"
          >
            <option value="">All sources</option>
            {sourceOptions.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <label className="text-sm font-medium text-gray-700">Filter list</label>
          <input
            type="search"
            placeholder="Company, contact, email, notes..."
            value={localSearch}
            onChange={(e) => setLocalSearch(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[180px]"
          />
        </div>
        {canWrite && (
          <button
            onClick={openNew}
            className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover shadow-sm"
          >
            Add lead
          </button>
        )}
      </div>

      {canBulk && (
        <BulkActionsBar
          selectedCount={selectedIds.size}
          entityName="leads"
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
                <th className="px-4 py-3">Company</th>
                <th className="px-4 py-3">Contact</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Team</th>
                <th className="px-4 py-3">Submitted by</th>
                <th className="px-4 py-3">Assigned to</th>
                <th className="px-4 py-3">Converted</th>
                {canWrite && <th className="px-4 py-3 w-32 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredItems.map((l) => (
                <tr key={l.id} className={`hover:bg-gray-50/80 ${selectedIds.has(l.id) ? "bg-primary/5" : ""}`}>
                  {canBulk && (
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(l.id)}
                        onChange={() => toggleSelect(l.id)}
                        className="rounded border-gray-300 text-primary focus:ring-primary/20"
                      />
                    </td>
                  )}
                  <td className="px-4 py-3 font-medium text-gray-900">{l.company_name}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {l.contact_name || l.contact_email || "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{l.status}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {l.assigned_team_id ? teamMap[l.assigned_team_id] || "—" : "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {l.created_by_name ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {l.assigned_to_name ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {l.converted_to_client_id ? "Yes" : "—"}
                  </td>
                  {(memberCanEdit(l) || managementCanEdit(l)) && (
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => openEdit(l)}
                          title="Edit"
                          className="p-1.5 rounded-lg text-gray-500 hover:text-primary hover:bg-gray-100 transition-colors"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                        {!l.converted_to_client_id && (
                          <>
                            {memberCanEdit(l) && (
                              <button
                                type="button"
                                onClick={() => handleMarkAsConverted(l)}
                                title="Mark as converted"
                                className="p-1.5 rounded-lg text-gray-500 hover:text-emerald-600 hover:bg-gray-100 transition-colors"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                              </button>
                            )}
                            {managementCanEdit(l) && (
                              <button
                                type="button"
                                onClick={() => openConvert(l)}
                                title="Create client & project"
                                className="p-1.5 rounded-lg text-gray-500 hover:text-emerald-600 hover:bg-gray-100 transition-colors"
                              >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                                </svg>
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => setMarkLostModal(l)}
                              title="Mark lost/closed"
                              className="p-1.5 rounded-lg text-gray-500 hover:text-amber-600 hover:bg-gray-100 transition-colors"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
                              </svg>
                            </button>
                          </>
                        )}
                        <button
                          type="button"
                          onClick={() => remove(l.id)}
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
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-10"
          onClick={() => setModal(null)}
        >
          <div
            className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              {modal === "new" ? "New lead" : "Edit lead"}
            </h2>
            {modal !== "new" && (
              <div className="flex flex-wrap gap-4 text-sm text-gray-500 mb-3">
                {(modal as Lead).created_by_name && (
                  <span>Submitted by: {(modal as Lead).created_by_name}</span>
                )}
                {(modal as Lead).assigned_to_name && (
                  <span>Assigned to: {(modal as Lead).assigned_to_name}</span>
                )}
              </div>
            )}
            <div className="space-y-3">
              <input
                placeholder="Company name *"
                value={form.company_name}
                onChange={(e) => setForm((f) => ({ ...f, company_name: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
              <input
                placeholder="Contact name"
                value={form.contact_name}
                onChange={(e) => setForm((f) => ({ ...f, contact_name: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
              <input
                placeholder="Contact email"
                type="email"
                value={form.contact_email}
                onChange={(e) => setForm((f) => ({ ...f, contact_email: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
              <input
                placeholder="Contact phone"
                value={form.contact_phone}
                onChange={(e) => setForm((f) => ({ ...f, contact_phone: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
              <input
                placeholder="Source (e.g. website, referral)"
                value={form.source}
                onChange={(e) => setForm((f) => ({ ...f, source: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary/20 focus:border-primary"
              />
              <select
                value={form.status}
                onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary"
              >
                <option value="new">New</option>
                <option value="contacted">Contacted</option>
                <option value="qualified">Qualified</option>
                <option value="converted">Converted</option>
                <option value="lost">Lost</option>
                <option value="closed">Closed</option>
                <option value="dead">Dead</option>
              </select>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Assigned team</label>
                <select
                  value={form.assigned_team_id ?? ""}
                  onChange={(e) => setForm((f) => ({ ...f, assigned_team_id: e.target.value || null }))}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary"
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
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary/20 focus:border-primary"
                rows={2}
              />
            </div>
            <NotesSection
              entityType="lead"
              entityId={modal !== "new" ? (modal as Lead).id : undefined}
            />
            <AttachmentsSection
              entityType="lead"
              entityId={modal !== "new" ? (modal as Lead).id : undefined}
            />
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

      {convertModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-10"
          onClick={() => setConvertModal(null)}
        >
          <div
            className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-md"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Convert to client</h2>
            <p className="text-sm text-gray-600 mb-4">
              Create a client and optional project from &quot;{convertModal.company_name}&quot;.
            </p>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Client team</label>
                <select
                  value={convertForm.client_team_id ?? ""}
                  onChange={(e) => setConvertForm((f) => ({ ...f, client_team_id: e.target.value || null }))}
                  className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary"
                >
                  <option value="">— Use lead team —</option>
                  {teams.map((t) => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>
              <label className="flex items-center gap-2 text-gray-700">
                <input
                  type="checkbox"
                  checked={convertForm.create_project}
                  onChange={(e) => setConvertForm((f) => ({ ...f, create_project: e.target.checked }))}
                  className="rounded border-gray-300 text-primary focus:ring-primary/20"
                />
                Create project
              </label>
              {convertForm.create_project && (
                <>
                  <input
                    placeholder="Project name"
                    value={convertForm.project_name}
                    onChange={(e) => setConvertForm((f) => ({ ...f, project_name: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Pipeline stage</label>
                    <select
                      value={convertForm.project_pipeline_stage}
                      onChange={(e) => setConvertForm((f) => ({ ...f, project_pipeline_stage: e.target.value }))}
                      className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary"
                    >
                      {PIPELINE_STAGES.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Assigned team (owner of this stage)</label>
                    <select
                      value={convertForm.project_assigned_team_id ?? ""}
                      onChange={(e) => setConvertForm((f) => ({ ...f, project_assigned_team_id: e.target.value || null }))}
                      className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary"
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
              <button onClick={() => setConvertModal(null)} className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">
                Cancel
              </button>
              <button onClick={handleConvert} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover">
                Convert
              </button>
            </div>
          </div>
        </div>
      )}

      {markLostModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-10"
          onClick={() => setMarkLostModal(null)}
        >
          <div
            className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-sm"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-lg font-semibold text-gray-900 mb-2">Mark lead as not won</h2>
            <p className="text-sm text-gray-600 mb-4">
              &quot;{markLostModal.company_name}&quot; — choose outcome:
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => handleMarkLost("lost")}
                className="px-4 py-2 rounded-lg bg-gray-100 text-gray-800 hover:bg-gray-200 font-medium"
              >
                Lost
              </button>
              <button
                onClick={() => handleMarkLost("closed")}
                className="px-4 py-2 rounded-lg bg-gray-100 text-gray-800 hover:bg-gray-200 font-medium"
              >
                Closed
              </button>
              <button
                onClick={() => handleMarkLost("dead")}
                className="px-4 py-2 rounded-lg bg-gray-100 text-gray-800 hover:bg-gray-200 font-medium"
              >
                Dead
              </button>
            </div>
            <div className="mt-4">
              <button onClick={() => setMarkLostModal(null)} className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
