import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/store/auth";
import { useModal } from "@/contexts/ModalContext";
import { listClients, type Client } from "@/api/clients";
import { listLeads, type Lead } from "@/api/leads";
import {
  listQuotes, createQuote, updateQuote, deleteQuote,
  sendQuote, acceptQuote, rejectQuote, convertQuote, invoiceQuote, openQuotePdf,
  type Quote,
} from "@/api/quotes";

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  sent: "bg-blue-100 text-blue-700",
  accepted: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-600",
  expired: "bg-amber-100 text-amber-700",
};

interface ItemRow {
  description: string;
  quantity: string;
  unit_price: string;
}

const EMPTY_ITEM: ItemRow = { description: "", quantity: "1", unit_price: "" };

export default function Quotes() {
  const { hasPermission } = useAuth();
  const { showConfirm, showAlert } = useModal();
  const canWrite = hasPermission("quotes:write");
  const canInvoice = hasPermission("finance:write");

  const [items, setItems] = useState<Quote[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [modal, setModal] = useState<"new" | Quote | null>(null);
  const [form, setForm] = useState({ title: "", target: "", valid_until: "", terms: "", currency: "USD" });
  const [rows, setRows] = useState<ItemRow[]>([{ ...EMPTY_ITEM }]);

  const load = useCallback(() => {
    listQuotes(statusFilter ? { status_filter: statusFilter } : undefined).then(setItems).catch(() => setItems([]));
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    listClients().then(setClients).catch(() => setClients([]));
    listLeads().then(setLeads).catch(() => setLeads([]));
  }, []);

  const openNew = () => {
    setForm({ title: "", target: "", valid_until: "", terms: "", currency: "USD" });
    setRows([{ ...EMPTY_ITEM }]);
    setModal("new");
  };

  const openEdit = (q: Quote) => {
    setForm({
      title: q.title,
      target: q.client_id ? `c:${q.client_id}` : q.lead_id ? `l:${q.lead_id}` : "",
      valid_until: q.valid_until || "",
      terms: q.terms || "",
      currency: q.currency,
    });
    setRows(q.items.map((i) => ({ description: i.description, quantity: String(i.quantity), unit_price: String(i.unit_price) })));
    setModal(q);
  };

  const grandTotal = rows.reduce((sum, r) => sum + (Number(r.quantity) || 0) * (Number(r.unit_price) || 0), 0);

  const save = async () => {
    const [kind, targetId] = form.target ? [form.target[0], form.target.slice(2)] : ["", ""];
    const payload = {
      title: form.title,
      client_id: kind === "c" ? targetId : null,
      lead_id: kind === "l" ? targetId : null,
      currency: form.currency,
      valid_until: form.valid_until || null,
      terms: form.terms || null,
      items: rows
        .filter((r) => r.description.trim())
        .map((r) => ({ description: r.description.trim(), quantity: Number(r.quantity) || 1, unit_price: Number(r.unit_price) || 0 })),
    };
    try {
      if (modal === "new") await createQuote(payload);
      else if (modal) await updateQuote(modal.id, payload);
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
            New quote
          </button>
        )}
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-gray-400 border-b border-gray-100 dark:border-gray-700">
              <th className="px-4 py-2.5">Number</th>
              <th className="px-4 py-2.5">Title</th>
              <th className="px-4 py-2.5">For</th>
              <th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5 text-right">Total</th>
              <th className="px-4 py-2.5"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50 dark:divide-gray-700">
            {items.map((q) => (
              <tr key={q.id} className="text-gray-700 dark:text-gray-200 hover:bg-gray-50/70 dark:hover:bg-gray-700/40">
                <td className="px-4 py-2.5 whitespace-nowrap font-mono text-xs">{q.number}</td>
                <td className="px-4 py-2.5">
                  <button onClick={() => openEdit(q)} className="font-medium hover:text-primary text-left">{q.title}</button>
                </td>
                <td className="px-4 py-2.5 text-gray-500">{q.client_name ?? q.lead_company ?? "—"}</td>
                <td className="px-4 py-2.5">
                  <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${STATUS_STYLES[q.status] ?? ""}`}>{q.status}</span>
                  {q.project_id && <span className="ml-1.5 text-[11px] text-gray-400">→ project</span>}
                </td>
                <td className="px-4 py-2.5 text-right font-medium whitespace-nowrap">{Number(q.total).toFixed(2)} {q.currency}</td>
                <td className="px-4 py-2.5 text-right whitespace-nowrap space-x-2">
                  <button onClick={() => openQuotePdf(q.id).catch(() => showAlert({ title: "Error", message: "Could not load PDF" }))} className="text-xs font-medium text-gray-500 hover:text-primary hover:underline">PDF</button>
                  {canWrite && (q.status === "draft" || q.status === "sent") && (
                    <>
                      <button onClick={() => act(() => sendQuote(q.id), "Quote marked as sent (emailed if a contact email exists).")} className="text-xs font-medium text-primary hover:underline">Send</button>
                      <button onClick={() => act(() => acceptQuote(q.id))} className="text-xs font-medium text-green-600 hover:underline">Accept</button>
                      <button onClick={() => act(() => rejectQuote(q.id))} className="text-xs font-medium text-red-500 hover:underline">Reject</button>
                    </>
                  )}
                  {canWrite && q.status === "accepted" && !q.project_id && (
                    <button onClick={() => act(() => convertQuote(q.id), "Project created from quote.")} className="text-xs font-medium text-primary hover:underline">→ Project</button>
                  )}
                  {canInvoice && q.status === "accepted" && (
                    <button onClick={() => act(() => invoiceQuote(q.id), "Draft invoice created for the quote total.")} className="text-xs font-medium text-primary hover:underline">→ Invoice</button>
                  )}
                  {canWrite && q.status !== "accepted" && (
                    <button
                      onClick={() => showConfirm({
                        title: "Delete quote",
                        message: `Delete ${q.number}?`,
                        onConfirm: () => act(() => deleteQuote(q.id)),
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
              <tr><td colSpan={6} className="px-4 py-6 text-center text-gray-400">No quotes yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-2xl p-6 max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              {modal === "new" ? "New quote" : `Edit ${modal.number}`}
            </h2>
            {modal !== "new" && modal.status !== "draft" && modal.status !== "sent" ? (
              <p className="text-sm text-gray-500 mb-4">This quote is {modal.status} and read-only.</p>
            ) : null}
            <div className="space-y-3">
              <input className={inputClass} placeholder="Title (becomes the project name on conversion)" value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} />
              <div className="grid grid-cols-2 gap-3">
                <select className={inputClass} value={form.target} onChange={(e) => setForm((f) => ({ ...f, target: e.target.value }))}>
                  <option value="">For: select client or lead…</option>
                  <optgroup label="Clients">
                    {clients.map((c) => <option key={c.id} value={`c:${c.id}`}>{c.name}</option>)}
                  </optgroup>
                  <optgroup label="Leads">
                    {leads.map((l) => <option key={l.id} value={`l:${l.id}`}>{l.company_name}</option>)}
                  </optgroup>
                </select>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-[11px] uppercase tracking-wide text-gray-400 mb-1">Valid until</label>
                    <input type="date" className={inputClass} value={form.valid_until} onChange={(e) => setForm((f) => ({ ...f, valid_until: e.target.value }))} />
                  </div>
                  <div>
                    <label className="block text-[11px] uppercase tracking-wide text-gray-400 mb-1">Currency</label>
                    <select className={inputClass} value={form.currency} onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value }))}>
                      {["USD", "EUR", "GBP", "PKR", "AED", "SAR", "CAD", "AUD"].map((c) => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                </div>
              </div>

              {/* Line items */}
              <div className="rounded-xl border border-gray-200 dark:border-gray-600 p-3 space-y-2">
                <div className="grid grid-cols-[1fr_80px_110px_90px_28px] gap-2 text-[11px] uppercase tracking-wide text-gray-400 px-1">
                  <span>Item</span><span>Qty</span><span>Unit price</span><span className="text-right">Total</span><span />
                </div>
                {rows.map((r, i) => (
                  <div key={i} className="grid grid-cols-[1fr_80px_110px_90px_28px] gap-2 items-center">
                    <input className={inputClass} placeholder="Description" value={r.description} onChange={(e) => setRows((rs) => rs.map((x, j) => (j === i ? { ...x, description: e.target.value } : x)))} />
                    <input type="number" min="0" step="0.5" className={inputClass} value={r.quantity} onChange={(e) => setRows((rs) => rs.map((x, j) => (j === i ? { ...x, quantity: e.target.value } : x)))} />
                    <input type="number" min="0" step="0.01" className={inputClass} value={r.unit_price} onChange={(e) => setRows((rs) => rs.map((x, j) => (j === i ? { ...x, unit_price: e.target.value } : x)))} />
                    <span className="text-sm text-right text-gray-600 dark:text-gray-300">{((Number(r.quantity) || 0) * (Number(r.unit_price) || 0)).toFixed(2)}</span>
                    <button onClick={() => setRows((rs) => rs.filter((_, j) => j !== i))} className="text-red-400 hover:text-red-600 text-sm" title="Remove">✕</button>
                  </div>
                ))}
                <div className="flex items-center justify-between pt-1">
                  <button onClick={() => setRows((rs) => [...rs, { ...EMPTY_ITEM }])} className="text-xs font-medium text-primary hover:underline">+ Add line</button>
                  <span className="text-sm font-semibold text-gray-800 dark:text-gray-100">Total: {grandTotal.toFixed(2)} {form.currency}</span>
                </div>
              </div>

              <textarea rows={2} className={inputClass} placeholder="Terms / notes (shown in the emailed proposal)" value={form.terms} onChange={(e) => setForm((f) => ({ ...f, terms: e.target.value }))} />
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 font-medium">Cancel</button>
              {(modal === "new" || modal.status === "draft" || modal.status === "sent") && (
                <button onClick={save} disabled={!form.title.trim() || !form.target} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover disabled:opacity-50">
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
