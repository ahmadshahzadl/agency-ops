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
import { useAuth } from "@/store/auth";

export default function InvoicesPage() {
  const [items, setItems] = useState<Invoice[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
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
  const { hasPermission } = useAuth();

  const load = () => {
    Promise.all([listInvoices(), listClients()]).then(([i, c]) => {
      setItems(i);
      setClients(c);
    }).finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

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
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Delete this invoice?")) return;
    try {
      await deleteInvoice(id);
      setModal(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const submitPayment = async () => {
    if (!paymentModal) return;
    try {
      await createPayment({
        invoice_id: paymentModal.id,
        amount: Number(paymentForm.amount),
        paid_at: paymentForm.paid_at,
        reference: paymentForm.reference || undefined,
      });
      setPaymentModal(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  };

  const canWrite = hasPermission("finance:write");
  const clientMap = Object.fromEntries(clients.map((c) => [c.id, c.name]));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-white">Invoices</h1>
        {canWrite && (
          <button
            onClick={openNew}
            className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover"
          >
            Add invoice
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
                <th className="px-4 py-3">Number</th>
                <th className="px-4 py-3">Client</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Status</th>
                {canWrite && <th className="px-4 py-3 w-32"></th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {items.map((inv) => (
                <tr key={inv.id} className="hover:bg-slate-800/50">
                  <td className="px-4 py-3 text-white">{inv.number}</td>
                  <td className="px-4 py-3 text-slate-300">{clientMap[inv.client_id] || inv.client_id}</td>
                  <td className="px-4 py-3 text-slate-300">
                    {inv.currency} {Number(inv.amount).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-slate-300">{inv.status}</td>
                  {canWrite && (
                    <td className="px-4 py-3">
                      <button onClick={() => openEdit(inv)} className="text-primary hover:underline mr-2">
                        Edit
                      </button>
                      <button
                        onClick={() => {
                          setPaymentModal(inv);
                          setPaymentForm({
                            amount: String(inv.amount),
                            paid_at: new Date().toISOString().slice(0, 10),
                            reference: "",
                          });
                        }}
                        className="text-emerald-400 hover:underline mr-2"
                      >
                        Payment
                      </button>
                      <button onClick={() => remove(inv.id)} className="text-red-400 hover:underline">
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
            <h2 className="text-lg font-semibold text-white mb-4">{modal === "new" ? "New invoice" : "Edit invoice"}</h2>
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
                placeholder="Number"
                value={form.number}
                onChange={(e) => setForm((f) => ({ ...f, number: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
              <input
                placeholder="Amount"
                type="number"
                step="0.01"
                value={form.amount}
                onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
              <select
                value={form.status}
                onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              >
                <option value="draft">Draft</option>
                <option value="sent">Sent</option>
                <option value="paid">Paid</option>
                <option value="overdue">Overdue</option>
              </select>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="date"
                  placeholder="Due date"
                  value={form.due_date}
                  onChange={(e) => setForm((f) => ({ ...f, due_date: e.target.value }))}
                  className="px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                />
                <input
                  type="date"
                  placeholder="Issued"
                  value={form.issued_at}
                  onChange={(e) => setForm((f) => ({ ...f, issued_at: e.target.value }))}
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

      {paymentModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-10" onClick={() => setPaymentModal(null)}>
          <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-white mb-4">Record payment</h2>
            <div className="space-y-3">
              <input
                placeholder="Amount"
                type="number"
                step="0.01"
                value={paymentForm.amount}
                onChange={(e) => setPaymentForm((f) => ({ ...f, amount: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
              <input
                type="date"
                value={paymentForm.paid_at}
                onChange={(e) => setPaymentForm((f) => ({ ...f, paid_at: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
              <input
                placeholder="Reference"
                value={paymentForm.reference}
                onChange={(e) => setPaymentForm((f) => ({ ...f, reference: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setPaymentModal(null)} className="px-4 py-2 text-slate-400 hover:text-white">
                Cancel
              </button>
              <button onClick={submitPayment} className="px-4 py-2 rounded-lg bg-primary text-white font-medium">
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
