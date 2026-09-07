import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/store/auth";
import { useModal } from "@/contexts/ModalContext";
import { listClients, type Client } from "@/api/clients";
import { listProjects, type Project } from "@/api/projects";
import { listQuotes, type Quote } from "@/api/quotes";
import {
  listAgreements, createAgreement, updateAgreement, deleteAgreement,
  sendAgreement, markAgreementSigned, terminateAgreement, duplicateAgreement,
  getAgreementTemplate, openAgreementPdf,
  type Agreement, type Clause,
} from "@/api/agreements";

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  sent: "bg-blue-100 text-blue-700",
  signed: "bg-green-100 text-green-700",
  declined: "bg-red-100 text-red-600",
  expired: "bg-amber-100 text-amber-700",
  terminated: "bg-red-50 text-red-500",
};

export default function Agreements() {
  const { hasPermission } = useAuth();
  const { showConfirm, showAlert } = useModal();
  const canWrite = hasPermission("agreements:write");
  const [prompt, setPrompt] = useState<{ kind: "sign" | "terminate"; agreement: Agreement; value: string } | null>(null);

  const [items, setItems] = useState<Agreement[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [modal, setModal] = useState<"new" | Agreement | null>(null);
  const [form, setForm] = useState({
    title: "", client_id: "", project_id: "", quote_id: "",
    effective_date: "", valid_until: "", contract_value: "", currency: "USD",
  });
  const [clauses, setClauses] = useState<Clause[]>([]);
  const [loadingTemplate, setLoadingTemplate] = useState(false);

  const load = useCallback(() => {
    listAgreements(statusFilter ? { status_filter: statusFilter } : undefined).then(setItems).catch(() => setItems([]));
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    listClients().then(setClients).catch(() => setClients([]));
    listProjects().then(setProjects).catch(() => setProjects([]));
    listQuotes().then(setQuotes).catch(() => setQuotes([]));
  }, []);

  const loadTemplate = async (overrides?: { client_id?: string; quote_id?: string; project_id?: string }) => {
    setLoadingTemplate(true);
    try {
      const t = await getAgreementTemplate({
        client_id: overrides?.client_id ?? (form.client_id || undefined),
        quote_id: overrides?.quote_id ?? (form.quote_id || undefined),
        project_id: overrides?.project_id ?? (form.project_id || undefined),
      });
      setClauses(t.clauses);
    } catch {
      showAlert({ title: "Error", message: "Could not load the template" });
    } finally {
      setLoadingTemplate(false);
    }
  };

  const openNew = async () => {
    setForm({ title: "", client_id: "", project_id: "", quote_id: "", effective_date: new Date().toISOString().slice(0, 10), valid_until: "", contract_value: "", currency: "USD" });
    setModal("new");
    setLoadingTemplate(true);
    try {
      const t = await getAgreementTemplate();
      setClauses(t.clauses);
    } catch {
      setClauses([]);
    } finally {
      setLoadingTemplate(false);
    }
  };

  const openEdit = (a: Agreement) => {
    setForm({
      title: a.title,
      client_id: a.client_id || "",
      project_id: a.project_id || "",
      quote_id: a.quote_id || "",
      effective_date: a.effective_date || "",
      valid_until: a.valid_until || "",
      contract_value: a.contract_value != null ? String(a.contract_value) : "",
      currency: a.currency,
    });
    setClauses(a.clauses.map((c) => ({ ...c })));
    setModal(a);
  };

  const save = async () => {
    const payload = {
      title: form.title,
      client_id: form.client_id,
      project_id: form.project_id || null,
      quote_id: form.quote_id || null,
      effective_date: form.effective_date || null,
      valid_until: form.valid_until || null,
      contract_value: form.contract_value ? Number(form.contract_value) : null,
      currency: form.currency,
      clauses: clauses.filter((c) => c.heading.trim() && c.body.trim()),
    };
    try {
      if (modal === "new") await createAgreement(payload);
      else if (modal) await updateAgreement(modal.id, payload);
      setModal(null);
      load();
    } catch (e) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    }
  };

  const act = async (fn: () => Promise<unknown>, successMsg?: string) => {
    try {
      await fn();
      load();
      if (successMsg) showAlert({ title: "Done", message: successMsg });
    } catch (e) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    }
  };

  const editable = modal === "new" || (modal !== null && ["draft", "sent", "expired"].includes(modal.status));
  const inputClass = "w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <select className={`${inputClass} !w-auto`} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          {Object.keys(STATUS_STYLES).map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        {canWrite && (
          <button onClick={openNew} className="ml-auto px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover">
            New agreement
          </button>
        )}
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-gray-400 border-b border-gray-100 dark:border-gray-700">
              <th className="px-4 py-2.5">Number</th>
              <th className="px-4 py-2.5">Title</th>
              <th className="px-4 py-2.5">Client</th>
              <th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5 text-right">Value</th>
              <th className="px-4 py-2.5"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50 dark:divide-gray-700">
            {items.map((a) => (
              <tr key={a.id} className="text-gray-700 dark:text-gray-200 hover:bg-gray-50/70 dark:hover:bg-gray-700/40">
                <td className="px-4 py-2.5 whitespace-nowrap font-mono text-xs">{a.number}</td>
                <td className="px-4 py-2.5">
                  <button onClick={() => openEdit(a)} className="font-medium hover:text-primary text-left">{a.title}</button>
                  {a.quote_number && <span className="block text-[11px] text-gray-400">from {a.quote_number}</span>}
                </td>
                <td className="px-4 py-2.5 text-gray-500">{a.client_name ?? "—"}</td>
                <td className="px-4 py-2.5">
                  <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${STATUS_STYLES[a.status] ?? ""}`}>{a.status}</span>
                  {a.status === "signed" && a.accepted_by_name && (
                    <span className="block text-[11px] text-gray-400 mt-0.5">by {a.accepted_by_name}{a.accepted_at ? ` · ${a.accepted_at.slice(0, 10)}` : ""}</span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-right font-medium whitespace-nowrap">
                  {a.contract_value != null ? `${Number(a.contract_value).toLocaleString()} ${a.currency}` : "—"}
                </td>
                <td className="px-4 py-2.5 text-right whitespace-nowrap space-x-2">
                  <button onClick={() => openAgreementPdf(a.id, a.number).catch(() => showAlert({ title: "Error", message: "Could not load PDF" }))} className="text-xs font-medium text-gray-500 hover:text-primary hover:underline">PDF</button>
                  {canWrite && (a.status === "draft" || a.status === "sent") && (
                    <>
                      <button onClick={() => act(() => sendAgreement(a.id), "Agreement marked as sent (emailed if the client has a contact email). The client can now sign it in their portal.")} className="text-xs font-medium text-primary hover:underline">Send</button>
                      <button
                        onClick={() => setPrompt({ kind: "sign", agreement: a, value: a.client_name || "" })}
                        className="text-xs font-medium text-green-600 hover:underline"
                      >
                        Mark signed
                      </button>
                    </>
                  )}
                  {canWrite && a.status === "signed" && (
                    <button
                      onClick={() => setPrompt({ kind: "terminate", agreement: a, value: "" })}
                      className="text-xs font-medium text-red-500 hover:underline"
                    >
                      Terminate
                    </button>
                  )}
                  {canWrite && (a.status === "signed" || a.status === "expired" || a.status === "terminated") && (
                    <button onClick={() => act(() => duplicateAgreement(a.id), "New draft created with the same terms.")} className="text-xs font-medium text-primary hover:underline">Renew</button>
                  )}
                  {canWrite && !["signed", "terminated"].includes(a.status) && (
                    <button
                      onClick={() => showConfirm({
                        title: "Delete agreement",
                        message: `Delete ${a.number}?`,
                        onConfirm: () => act(() => deleteAgreement(a.id)),
                      })}
                      className="text-xs font-medium text-red-400 hover:text-red-600"
                    >
                      ✕
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-400">No agreements yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {prompt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-sm p-5">
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">
              {prompt.kind === "sign" ? `Mark ${prompt.agreement.number} as signed` : `Terminate ${prompt.agreement.number}`}
            </h3>
            <p className="text-sm text-gray-500 mt-1 mb-3">
              {prompt.kind === "sign"
                ? "Who signed it (e.g. on paper or by email)? This goes on the permanent record — the agreement becomes immutable."
                : "A reason is required and becomes part of the permanent record."}
            </p>
            <input
              autoFocus
              className={inputClass}
              placeholder={prompt.kind === "sign" ? "Signer's name" : "Termination reason"}
              value={prompt.value}
              onChange={(e) => setPrompt((p) => (p ? { ...p, value: e.target.value } : p))}
            />
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setPrompt(null)} className="px-4 py-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 font-medium">Cancel</button>
              <button
                disabled={prompt.kind === "terminate" && !prompt.value.trim()}
                onClick={() => {
                  const { kind, agreement, value } = prompt;
                  setPrompt(null);
                  if (kind === "sign") act(() => markAgreementSigned(agreement.id, value.trim() || undefined), "Agreement recorded as signed. It is now a frozen record.");
                  else act(() => terminateAgreement(agreement.id, value.trim()));
                }}
                className={`px-4 py-2 rounded-lg text-white font-medium disabled:opacity-50 ${prompt.kind === "sign" ? "bg-green-600 hover:bg-green-700" : "bg-red-600 hover:bg-red-700"}`}
              >
                {prompt.kind === "sign" ? "Record signature" : "Terminate"}
              </button>
            </div>
          </div>
        </div>
      )}

      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-3xl p-6 max-h-[92vh] overflow-y-auto">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
              {modal === "new" ? "New service agreement" : `${editable ? "Edit" : "View"} ${modal.number}`}
            </h2>
            {modal !== "new" && !editable && (
              <p className="text-sm text-gray-500 mb-3">
                This agreement is {modal.status} and is a frozen record.
                {modal.status === "signed" && modal.accepted_by_name && (
                  <> Accepted by <b>{modal.accepted_by_name}</b>{modal.accepted_at ? ` on ${modal.accepted_at.slice(0, 16).replace("T", " ")} UTC` : ""}{modal.acceptance_method === "portal" ? " via the client portal" : ""}{modal.accepted_ip ? ` (IP ${modal.accepted_ip})` : ""}.</>
                )}
                {modal.status === "declined" && modal.decline_reason && <> Reason: {modal.decline_reason}</>}
                {modal.status === "terminated" && modal.termination_reason && <> Terminated: {modal.termination_reason}</>}
              </p>
            )}
            <div className="space-y-3">
              <input className={inputClass} placeholder="Title (e.g. Website development for Acme)" disabled={!editable} value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} />
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] uppercase tracking-wide text-gray-400 mb-1">Client *</label>
                  <select className={inputClass} disabled={!editable} value={form.client_id} onChange={(e) => { setForm((f) => ({ ...f, client_id: e.target.value })); if (editable && e.target.value) loadTemplate({ client_id: e.target.value }); }}>
                    <option value="">Select client…</option>
                    {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] uppercase tracking-wide text-gray-400 mb-1">Prefill from quote (scope + fees)</label>
                  <select className={inputClass} disabled={!editable} value={form.quote_id} onChange={(e) => { setForm((f) => ({ ...f, quote_id: e.target.value })); if (editable && e.target.value) loadTemplate({ quote_id: e.target.value }); }}>
                    <option value="">None</option>
                    {quotes.map((q) => <option key={q.id} value={q.id}>{q.number} — {q.title}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] uppercase tracking-wide text-gray-400 mb-1">Project (timeline from milestones)</label>
                  <select className={inputClass} disabled={!editable} value={form.project_id} onChange={(e) => { setForm((f) => ({ ...f, project_id: e.target.value })); if (editable && e.target.value) loadTemplate({ project_id: e.target.value }); }}>
                    <option value="">None</option>
                    {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[11px] uppercase tracking-wide text-gray-400 mb-1">Effective date</label>
                    <input type="date" className={inputClass} disabled={!editable} value={form.effective_date} onChange={(e) => setForm((f) => ({ ...f, effective_date: e.target.value }))} />
                  </div>
                  <div>
                    <label className="block text-[11px] uppercase tracking-wide text-gray-400 mb-1">Sign by</label>
                    <input type="date" className={inputClass} disabled={!editable} value={form.valid_until} onChange={(e) => setForm((f) => ({ ...f, valid_until: e.target.value }))} />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[11px] uppercase tracking-wide text-gray-400 mb-1">Contract value</label>
                    <input type="number" min="0" step="0.01" className={inputClass} disabled={!editable} value={form.contract_value} onChange={(e) => setForm((f) => ({ ...f, contract_value: e.target.value }))} />
                  </div>
                  <div>
                    <label className="block text-[11px] uppercase tracking-wide text-gray-400 mb-1">Currency</label>
                    <select className={inputClass} disabled={!editable} value={form.currency} onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value }))}>
                      {["USD", "EUR", "GBP", "PKR", "AED", "SAR", "CAD", "AUD"].map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                </div>
              </div>

              {/* Clauses */}
              <div className="rounded-xl border border-gray-200 dark:border-gray-600 p-3 space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-[11px] uppercase tracking-wide text-gray-400">Terms — {clauses.length} clauses</p>
                  {editable && (
                    <button onClick={() => loadTemplate()} disabled={loadingTemplate} className="text-xs font-medium text-primary hover:underline disabled:opacity-50">
                      {loadingTemplate ? "Loading…" : "↺ Reset to template (uses selections above)"}
                    </button>
                  )}
                </div>
                {clauses.map((c, i) => (
                  <div key={i} className="rounded-lg border border-gray-100 dark:border-gray-700 p-2 space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-gray-400 w-5">{i + 1}.</span>
                      <input className={inputClass} placeholder="Clause heading" disabled={!editable} value={c.heading} onChange={(e) => setClauses((cs) => cs.map((x, j) => (j === i ? { ...x, heading: e.target.value } : x)))} />
                      {editable && (
                        <button onClick={() => setClauses((cs) => cs.filter((_, j) => j !== i))} className="text-red-400 hover:text-red-600 text-sm shrink-0" title="Remove clause">✕</button>
                      )}
                    </div>
                    <textarea rows={3} className={`${inputClass} font-normal`} placeholder="Clause text" disabled={!editable} value={c.body} onChange={(e) => setClauses((cs) => cs.map((x, j) => (j === i ? { ...x, body: e.target.value } : x)))} />
                  </div>
                ))}
                {editable && (
                  <button onClick={() => setClauses((cs) => [...cs, { heading: "", body: "" }])} className="text-xs font-medium text-primary hover:underline">+ Add clause</button>
                )}
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 font-medium">Close</button>
              {editable && canWrite && (
                <button onClick={save} disabled={!form.title.trim() || !form.client_id || clauses.filter((c) => c.heading.trim() && c.body.trim()).length === 0} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover disabled:opacity-50">
                  Save
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
