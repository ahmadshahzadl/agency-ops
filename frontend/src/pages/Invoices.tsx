import { useEffect, useState } from "react";
import {
  listInvoices,
  createInvoice,
  updateInvoice,
  deleteInvoice,
  createPayment,
  type Invoice,
} from "@/api/finance";
import { listClients, type Client } from "@/api/clients";
import { listProjectNames } from "@/api/projects";
import { invoiceFromTime } from "@/api/time";
import { useAuth } from "@/store/auth";
import { NotesSection } from "@/components/NotesSection";
import { AttachmentsSection } from "@/components/AttachmentsSection";
import { useModal } from "@/contexts/ModalContext";
import { BulkActionsBar } from "@/components/BulkActionsBar";

const INVOICE_STATUS_OPTIONS = ["draft", "sent", "paid", "overdue"];

export default function InvoicesPage() {
  const { showConfirm, showAlert } = useModal();
  const { hasPermission } = useAuth();
  const canBulk = hasPermission("admin:all");
  const [items, setItems] = useState<Invoice[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [clientFilter, setClientFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [searchText, setSearchText] = useState("");
  const [modal, setModal] = useState<"new" | Invoice | null>(null);
  const [paymentModal, setPaymentModal] = useState<Invoice | null>(null);
  const [form, setForm] = useState({
    client_id: "",
    project_id: "",
    number: "",
    amount: "",
    currency: "USD",
    status: "draft",
    due_date: "",
    issued_at: "",
  });
  const [paymentForm, setPaymentForm] = useState({ amount: "", paid_at: "", reference: "" });
  const [fromTimeModal, setFromTimeModal] = useState(false);
  const [projectNames, setProjectNames] = useState<{ id: string; name: string }[]>([]);
  const [fromTimeForm, setFromTimeForm] = useState({ project_id: "", date_from: "", date_to: "", hourly_rate: "", number: "" });

  const load = () => {
    listClients().then(setClients).catch(() => setClients([]));
    const params: { client_id?: string; status_filter?: string } = {};
    if (clientFilter) params.client_id = clientFilter;
    if (statusFilter) params.status_filter = statusFilter;
    listInvoices(Object.keys(params).length ? params : undefined)
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [clientFilter, statusFilter]);

  const openNew = () => {
    setForm({
      client_id: clients[0]?.id || "",
      project_id: "",
      number: "",
      amount: "",
      currency: "USD",
      status: "draft",
      due_date: "",
      issued_at: "",
    });
    setModal("new");
  };
  const openEdit = (inv: Invoice) => {
    setForm({
      client_id: inv.client_id,
      project_id: inv.project_id || "",
      number: inv.number,
      amount: String(inv.amount),
      currency: inv.currency,
      status: inv.status,
      due_date: inv.due_date || "",
      issued_at: inv.issued_at || "",
    });
    setModal(inv);
  };

  const save = async () => {
    if (modal === null) return;
    const payload = {
      client_id: form.client_id,
      project_id: form.project_id || undefined,
      number: form.number,
      amount: Number(form.amount),
      currency: form.currency,
      status: form.status,
      due_date: form.due_date || undefined,
      issued_at: form.issued_at || undefined,
    };
    try {
      if (modal === "new") {
        await createInvoice(payload as Invoice);
      } else {
        await updateInvoice(modal.id, payload);
      }
      setModal(null);
      load();
    } catch (e: unknown) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    }
  };

  const remove = (id: string) => {
    showConfirm({
      title: "Delete invoice",
      message: "Delete this invoice?",
      confirmLabel: "Delete",
      variant: "danger",
      onConfirm: async () => {
        try {
          await deleteInvoice(id);
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
    else setSelectedIds(new Set(filteredItems.map((inv) => inv.id)));
  };
  const bulkDelete = () => {
    const ids = Array.from(selectedIds);
    showConfirm({
      title: "Delete invoices",
      message: `Delete ${ids.length} invoice(s)? This cannot be undone.`,
      confirmLabel: "Delete all",
      variant: "danger",
      onConfirm: async () => {
        setBulkDeleting(true);
        try {
          for (const id of ids) {
            try {
              await deleteInvoice(id);
            } catch (e) {
              showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed to delete invoice" });
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

  const submitPayment = async () => {
    if (!paymentModal) return;
    try {
      await createPayment({
        invoice_id: paymentModal.id,
        amount: Number(paymentForm.amount),
        paid_at: paymentForm.paid_at,
        reference: paymentForm.reference || null,
      });
      setPaymentModal(null);
      load();
    } catch (e: unknown) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    }
  };

  const canWrite = hasPermission("finance:write");
  const clientMap = Object.fromEntries(clients.map((c) => [c.id, c.name]));
  const searchLower = searchText.trim().toLowerCase();
  const filteredItems = searchLower
    ? items.filter(
        (inv) =>
          (inv.number ?? "").toLowerCase().includes(searchLower) ||
          String(inv.amount).includes(searchText.trim()) ||
          (clientMap[inv.client_id] ?? "").toLowerCase().includes(searchLower)
      )
    : items;
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
          <label className="text-sm font-medium text-gray-700 ml-2">Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[120px]"
          >
            <option value="">All statuses</option>
            {INVOICE_STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <label className="text-sm font-medium text-gray-700">Search</label>
          <input
            type="search"
            placeholder="Number, amount, client..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[180px]"
          />
        </div>
        {canWrite && (
          <div className="flex gap-2">
            <button
              onClick={async () => {
                setProjectNames(await listProjectNames({ limit: 500 }).catch(() => []));
                setFromTimeForm({ project_id: "", date_from: "", date_to: "", hourly_rate: "", number: "" });
                setFromTimeModal(true);
              }}
              className="px-4 py-2 rounded-lg bg-gray-100 text-gray-700 font-medium hover:bg-gray-200"
            >
              From time
            </button>
            <button
              onClick={openNew}
              className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover"
            >
              Add invoice
            </button>
          </div>
        )}
      </div>

      {fromTimeModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-1">Generate invoice from time</h2>
            <p className="text-sm text-gray-500 mb-4">Bills all unbilled billable hours on the project (optionally limited to a date range). Rate precedence: entry rate, then the rate below, then the project rate.</p>
            <div className="space-y-3">
              <select
                value={fromTimeForm.project_id}
                onChange={(e) => setFromTimeForm((f) => ({ ...f, project_id: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary"
              >
                <option value="">Select project…</option>
                {projectNames.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
              <div className="grid grid-cols-2 gap-2">
                <input type="date" value={fromTimeForm.date_from} onChange={(e) => setFromTimeForm((f) => ({ ...f, date_from: e.target.value }))} className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900" />
                <input type="date" value={fromTimeForm.date_to} onChange={(e) => setFromTimeForm((f) => ({ ...f, date_to: e.target.value }))} className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900" />
              </div>
              <input type="number" min="0" step="0.01" placeholder="Hourly rate override (optional)" value={fromTimeForm.hourly_rate} onChange={(e) => setFromTimeForm((f) => ({ ...f, hourly_rate: e.target.value }))} className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900" />
              <input placeholder="Invoice number (auto if empty)" value={fromTimeForm.number} onChange={(e) => setFromTimeForm((f) => ({ ...f, number: e.target.value }))} className="w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900" />
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setFromTimeModal(false)} className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">Cancel</button>
              <button
                disabled={!fromTimeForm.project_id}
                onClick={async () => {
                  try {
                    const inv = await invoiceFromTime({
                      project_id: fromTimeForm.project_id,
                      date_from: fromTimeForm.date_from || undefined,
                      date_to: fromTimeForm.date_to || undefined,
                      hourly_rate: fromTimeForm.hourly_rate ? Number(fromTimeForm.hourly_rate) : undefined,
                      number: fromTimeForm.number || undefined,
                    });
                    setFromTimeModal(false);
                    load();
                    showAlert({ title: "Invoice created", message: `${inv.number} for ${inv.amount} ${inv.currency} (draft)` });
                  } catch (e) {
                    showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
                  }
                }}
                className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover disabled:opacity-50"
              >
                Generate
              </button>
            </div>
          </div>
        </div>
      )}

      {canBulk && (
        <BulkActionsBar
          selectedCount={selectedIds.size}
          entityName="invoices"
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
                <th className="px-4 py-3">Number</th>
                <th className="px-4 py-3">Client</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Status</th>
                {canWrite && <th className="px-4 py-3 w-32 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredItems.map((inv) => (
                <tr key={inv.id} className={`hover:bg-gray-50/80 ${selectedIds.has(inv.id) ? "bg-primary/5" : ""}`}>
                  {canBulk && (
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(inv.id)}
                        onChange={() => toggleSelect(inv.id)}
                        className="rounded border-gray-300 text-primary focus:ring-primary/20"
                      />
                    </td>
                  )}
                  <td className="px-4 py-3 font-medium text-gray-900">{inv.number}</td>
                  <td className="px-4 py-3 text-gray-600">{clientMap[inv.client_id] || inv.client_id}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {inv.currency} {Number(inv.amount).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{inv.status}</td>
                  {canWrite && (
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button type="button" onClick={() => openEdit(inv)} title="Edit" className="p-1.5 rounded-lg text-gray-500 hover:text-primary hover:bg-gray-100 transition-colors">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setPaymentModal(inv);
                            setPaymentForm({
                              amount: String(inv.amount),
                              paid_at: new Date().toISOString().slice(0, 10),
                              reference: "",
                            });
                          }}
                          title="Record payment"
                          className="p-1.5 rounded-lg text-gray-500 hover:text-emerald-600 hover:bg-gray-100 transition-colors"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                          </svg>
                        </button>
                        <button type="button" onClick={() => remove(inv.id)} title="Delete" className="p-1.5 rounded-lg text-gray-500 hover:text-red-600 hover:bg-gray-100 transition-colors">
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
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">{modal === "new" ? "New invoice" : "Edit invoice"}</h2>
            <div className="space-y-3">
              <div>
                <label className={labelClass}>Client</label>
                <select
                  value={form.client_id}
                  onChange={(e) => setForm((f) => ({ ...f, client_id: e.target.value }))}
                  className={inputClass}
                >
                  {clients.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>
              <input
                placeholder="Number"
                value={form.number}
                onChange={(e) => setForm((f) => ({ ...f, number: e.target.value }))}
                className={inputClass}
              />
              <input
                placeholder="Amount"
                type="number"
                step="0.01"
                value={form.amount}
                onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                className={inputClass}
              />
              <div>
                <label className={labelClass}>Status</label>
                <select
                  value={form.status}
                  onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
                  className={inputClass}
                >
                  <option value="draft">Draft</option>
                  <option value="sent">Sent</option>
                  <option value="paid">Paid</option>
                  <option value="overdue">Overdue</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className={labelClass}>Due date</label>
                  <input
                    type="date"
                    value={form.due_date}
                    onChange={(e) => setForm((f) => ({ ...f, due_date: e.target.value }))}
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Issued</label>
                  <input
                    type="date"
                    value={form.issued_at}
                    onChange={(e) => setForm((f) => ({ ...f, issued_at: e.target.value }))}
                    className={inputClass}
                  />
                </div>
              </div>
            </div>
            <NotesSection entityType="invoice" entityId={modal !== "new" ? (modal as Invoice).id : undefined} />
            <AttachmentsSection entityType="invoice" entityId={modal !== "new" ? (modal as Invoice).id : undefined} />
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">Cancel</button>
              <button onClick={save} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover">Save</button>
            </div>
          </div>
        </div>
      )}

      {paymentModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-10" onClick={() => setPaymentModal(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Record payment</h2>
            <div className="space-y-3">
              <div>
                <label className={labelClass}>Amount</label>
                <input
                  placeholder="Amount"
                  type="number"
                  step="0.01"
                  value={paymentForm.amount}
                  onChange={(e) => setPaymentForm((f) => ({ ...f, amount: e.target.value }))}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Date</label>
                <input
                  type="date"
                  value={paymentForm.paid_at}
                  onChange={(e) => setPaymentForm((f) => ({ ...f, paid_at: e.target.value }))}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Reference (optional)</label>
                <input
                  placeholder="Reference"
                  value={paymentForm.reference}
                  onChange={(e) => setPaymentForm((f) => ({ ...f, reference: e.target.value }))}
                  className={inputClass}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setPaymentModal(null)} className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">Cancel</button>
              <button onClick={submitPayment} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover">Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
