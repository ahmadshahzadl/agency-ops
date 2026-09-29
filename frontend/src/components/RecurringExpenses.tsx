import { useEffect, useMemo, useState } from "react";
import {
  listRecurringExpenses, createRecurringExpense, updateRecurringExpense, deleteRecurringExpense,
  payRecurringExpense, skipRecurringExpense, recurringExpenseHistory,
  type RecurringExpense, type RecurringExpenseInput, type RecurringFrequency, type Expense,
} from "@/api/finance";
import { listAssignableUsers, type UserList } from "@/api/users";
import type { Project } from "@/api/projects";
import { useModal } from "@/contexts/ModalContext";

export const FREQUENCY_LABEL: Record<RecurringFrequency, string> = {
  weekly: "Weekly", monthly: "Monthly", quarterly: "Quarterly", yearly: "Yearly",
};

export const CATEGORY_LABEL: Record<string, string> = {
  office: "Office", commission: "Commission", salary: "Salary", software: "Software / subscription", travel: "Travel", other: "Other",
};

export function StatusChip({ status, days }: { status: RecurringExpense["status"] | "not_set"; days?: number | null }) {
  const map: Record<string, { cls: string; label: string }> = {
    overdue: { cls: "bg-red-50 text-red-700 border-red-200", label: days != null ? `Overdue ${Math.abs(days)}d` : "Overdue" },
    due_today: { cls: "bg-amber-50 text-amber-800 border-amber-200", label: "Due today" },
    due_soon: { cls: "bg-amber-50 text-amber-700 border-amber-200", label: days != null ? `Due in ${days}d` : "Due soon" },
    scheduled: { cls: "bg-gray-50 text-gray-600 border-gray-200", label: days != null ? `In ${days}d` : "Scheduled" },
    paused: { cls: "bg-gray-100 text-gray-500 border-gray-200", label: "Paused" },
    not_set: { cls: "bg-gray-50 text-gray-400 border-dashed border-gray-300", label: "Not set" },
  };
  const m = map[status] ?? map.scheduled;
  return <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${m.cls}`}>{m.label}</span>;
}

export function fmtMoney(currency: string | null | undefined, amount: number | string | null | undefined): string {
  if (amount == null) return "—";
  return `${currency ?? ""} ${Number(amount).toLocaleString(undefined, { maximumFractionDigits: 2 })}`.trim();
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

const EMPTY_FORM = {
  description: "", category: "office", amount: "", currency: "PKR", frequency: "monthly" as RecurringFrequency,
  due_day: "1", next_due_date: "", project_id: "", payee_user_id: "", notes: "", remind_2: true, remind_1: true, remind_0: true,
};

export function RecurringExpensesPanel({ projects, canWrite }: { projects: Project[]; canWrite: boolean }) {
  const { showConfirm, showAlert } = useModal();
  const [rows, setRows] = useState<RecurringExpense[]>([]);
  const [loading, setLoading] = useState(true);
  const [showPaused, setShowPaused] = useState(false);
  const [users, setUsers] = useState<UserList[]>([]);
  const [modal, setModal] = useState<"new" | RecurringExpense | null>(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [payTarget, setPayTarget] = useState<RecurringExpense | null>(null);
  const [payForm, setPayForm] = useState({ paid_on: "", amount: "", note: "" });
  const [historyFor, setHistoryFor] = useState<RecurringExpense | null>(null);
  const [history, setHistory] = useState<Expense[]>([]);
  const [busy, setBusy] = useState(false);

  const load = () => {
    setLoading(true);
    listRecurringExpenses({ include_inactive: showPaused }).then(setRows).catch(() => setRows([])).finally(() => setLoading(false));
  };
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [showPaused]);
  useEffect(() => { listAssignableUsers().then(setUsers).catch(() => setUsers([])); }, []);

  const totals = useMemo(() => {
    const byCur: Record<string, number> = {};
    for (const r of rows) {
      if (!r.is_active) continue;
      const monthly = r.frequency === "weekly" ? Number(r.amount) * 52 / 12 : r.frequency === "quarterly" ? Number(r.amount) / 3 : r.frequency === "yearly" ? Number(r.amount) / 12 : Number(r.amount);
      byCur[r.currency] = (byCur[r.currency] ?? 0) + monthly;
    }
    return byCur;
  }, [rows]);
  const attention = rows.filter((r) => r.status === "overdue" || r.status === "due_today" || r.status === "due_soon");

  const openNew = () => { setForm({ ...EMPTY_FORM }); setModal("new"); };
  const openEdit = (r: RecurringExpense) => {
    setForm({
      description: r.description, category: r.category, amount: String(r.amount), currency: r.currency, frequency: r.frequency,
      due_day: String(r.due_day), next_due_date: r.next_due_date, project_id: r.project_id ?? "", payee_user_id: r.payee_user_id ?? "",
      notes: r.notes ?? "", remind_2: r.remind_days_before.includes(2), remind_1: r.remind_days_before.includes(1), remind_0: r.remind_days_before.includes(0),
    });
    setModal(r);
  };

  const save = async () => {
    if (!modal) return;
    const remind = [form.remind_2 && 2, form.remind_1 && 1, form.remind_0 && 0].filter((x): x is number => x !== false);
    const payload: RecurringExpenseInput = {
      description: form.description.trim(), category: form.category, amount: Number(form.amount), currency: form.currency,
      frequency: form.frequency, due_day: Number(form.due_day) || 1,
      next_due_date: form.next_due_date || null,
      project_id: form.project_id || null, payee_user_id: form.payee_user_id || null, notes: form.notes || null, remind_days_before: remind,
    };
    if (!payload.description || !(payload.amount > 0)) { showAlert({ title: "Check the form", message: "A description and an amount above zero are required." }); return; }
    setBusy(true);
    try {
      if (modal === "new") await createRecurringExpense(payload);
      else await updateRecurringExpense(modal.id, payload);
      setModal(null);
      load();
    } catch (e) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Could not save" });
    } finally { setBusy(false); }
  };

  const togglePaused = async (r: RecurringExpense) => {
    try { await updateRecurringExpense(r.id, { is_active: !r.is_active }); load(); }
    catch (e) { showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" }); }
  };

  const remove = (r: RecurringExpense) => {
    showConfirm({
      title: "Delete recurring bill",
      message: `Delete "${r.description}"? Past payments stay in Expenses; only the schedule and reminders go.`,
      confirmLabel: "Delete", variant: "danger",
      onConfirm: async () => { await deleteRecurringExpense(r.id); setModal(null); load(); },
    });
  };

  const openPay = (r: RecurringExpense) => {
    setPayTarget(r);
    setPayForm({ paid_on: new Date().toISOString().slice(0, 10), amount: "", note: "" });
  };
  const confirmPay = async () => {
    if (!payTarget) return;
    setBusy(true);
    try {
      await payRecurringExpense(payTarget.id, {
        paid_on: payForm.paid_on || undefined,
        amount: payForm.amount ? Number(payForm.amount) : undefined,
        note: payForm.note || undefined,
      });
      setPayTarget(null);
      load();
    } catch (e) { showAlert({ title: "Error", message: e instanceof Error ? e.message : "Could not record payment" }); }
    finally { setBusy(false); }
  };

  const skip = (r: RecurringExpense) => {
    showConfirm({
      title: "Skip this period",
      message: `Skip ${r.description} for the period due ${fmtDate(r.next_due_date)}? No expense is recorded and the next due date moves forward.`,
      confirmLabel: "Skip",
      onConfirm: async () => { await skipRecurringExpense(r.id); load(); },
    });
  };

  const openHistory = async (r: RecurringExpense) => {
    setHistoryFor(r);
    setHistory(await recurringExpenseHistory(r.id).catch(() => []));
  };

  const inputClass = "w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm";
  const labelClass = "block text-xs font-medium text-gray-500 mb-1";

  return (
    <div className="space-y-4">
      {/* Summary strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm p-4">
          <p className="text-xs uppercase tracking-wide text-gray-400">Needs attention</p>
          <p className={`text-2xl font-semibold mt-1 ${attention.length ? "text-amber-700" : "text-gray-900"}`}>{attention.length}</p>
          <p className="text-xs text-gray-500 mt-1">{attention.filter((r) => r.status === "overdue").length} overdue · {attention.filter((r) => r.status !== "overdue").length} due within 7 days</p>
        </div>
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm p-4">
          <p className="text-xs uppercase tracking-wide text-gray-400">Monthly commitment</p>
          <div className="mt-1 space-y-0.5">
            {Object.keys(totals).length === 0 && <p className="text-2xl font-semibold text-gray-900">—</p>}
            {Object.entries(totals).map(([cur, v]) => <p key={cur} className="text-lg font-semibold text-gray-900">{fmtMoney(cur, v)}</p>)}
          </div>
          <p className="text-xs text-gray-500 mt-1">Active bills, normalised to a month</p>
        </div>
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm p-4">
          <p className="text-xs uppercase tracking-wide text-gray-400">Reminders</p>
          <p className="text-sm text-gray-700 mt-1">Finance users are notified in the app and by email 2 days before, 1 day before, on the day, and once when overdue.</p>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 flex-wrap">
        <label className="inline-flex items-center gap-2 text-sm text-gray-600">
          <input type="checkbox" checked={showPaused} onChange={(e) => setShowPaused(e.target.checked)} className="rounded border-gray-300 text-primary focus:ring-primary/20" />
          Show paused
        </label>
        {canWrite && (
          <button onClick={openNew} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover">Add recurring bill</button>
        )}
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : rows.length === 0 ? (
        <div className="rounded-xl bg-white border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">
          No recurring bills yet. Add rent, subscriptions and other monthly costs here to get reminders before they are due. Salaries live on the <a href="/payroll" className="text-primary hover:underline">Payroll</a> page.
        </div>
      ) : (
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-x-auto">
          <table className="w-full min-w-[760px]">
            <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600">
              <tr>
                <th className="px-4 py-3">Bill</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Every</th>
                <th className="px-4 py-3">Next due</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Last paid</th>
                {canWrite && <th className="px-4 py-3 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((r) => (
                <tr key={r.id} className={`hover:bg-gray-50/80 ${!r.is_active ? "opacity-60" : ""}`}>
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{r.description}</p>
                    <p className="text-xs text-gray-500">{CATEGORY_LABEL[r.category] ?? r.category}{r.payee_name ? ` · ${r.payee_name}` : ""}{r.project_name ? ` · ${r.project_name}` : ""}</p>
                  </td>
                  <td className="px-4 py-3 text-gray-700 whitespace-nowrap">{fmtMoney(r.currency, r.amount)}</td>
                  <td className="px-4 py-3 text-gray-600 text-sm">{FREQUENCY_LABEL[r.frequency]}{r.frequency !== "weekly" ? `, day ${r.due_day}` : ""}</td>
                  <td className="px-4 py-3 text-gray-700 whitespace-nowrap">{fmtDate(r.next_due_date)}</td>
                  <td className="px-4 py-3"><StatusChip status={r.status} days={r.days_until_due} /></td>
                  <td className="px-4 py-3 text-gray-600 text-sm whitespace-nowrap">
                    <button onClick={() => openHistory(r)} className="hover:underline" title="Payment history">{fmtDate(r.last_paid_on)}</button>
                  </td>
                  {canWrite && (
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <div className="inline-flex items-center gap-1">
                        {r.is_active && (
                          <button onClick={() => openPay(r)} className="px-2.5 py-1 rounded-lg text-xs font-medium bg-green-600 text-white hover:bg-green-700">Mark paid</button>
                        )}
                        {r.is_active && (
                          <button onClick={() => skip(r)} className="px-2.5 py-1 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-100">Skip</button>
                        )}
                        <button onClick={() => openEdit(r)} className="px-2.5 py-1 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-100">Edit</button>
                        <button onClick={() => togglePaused(r)} className="px-2.5 py-1 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-100">{r.is_active ? "Pause" : "Resume"}</button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* New / edit modal */}
      {modal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-10 p-4" onClick={() => setModal(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">{modal === "new" ? "New recurring bill" : "Edit recurring bill"}</h2>
            <div className="space-y-3">
              <div>
                <label className={labelClass}>Description</label>
                <input className={inputClass} placeholder="e.g. Office rent, Google Workspace, Internet" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className={labelClass}>Category</label>
                  <select className={inputClass} value={form.category} onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}>
                    {Object.entries(CATEGORY_LABEL).filter(([k]) => k !== "commission").map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
                <div>
                  <label className={labelClass}>Project (optional)</label>
                  <select className={inputClass} value={form.project_id} onChange={(e) => setForm((f) => ({ ...f, project_id: e.target.value }))}>
                    <option value="">—</option>
                    {projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="col-span-2">
                  <label className={labelClass}>Amount</label>
                  <input type="number" step="0.01" min="0" className={inputClass} value={form.amount} onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} />
                </div>
                <div>
                  <label className={labelClass}>Currency</label>
                  <select className={inputClass} value={form.currency} onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value }))}>
                    {["PKR", "USD", "AED", "GBP", "EUR"].map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className={labelClass}>Repeats</label>
                  <select className={inputClass} value={form.frequency} onChange={(e) => setForm((f) => ({ ...f, frequency: e.target.value as RecurringFrequency }))}>
                    {Object.entries(FREQUENCY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                </div>
                <div>
                  <label className={labelClass}>Due day of month</label>
                  <input type="number" min="1" max="31" className={inputClass} disabled={form.frequency === "weekly"} value={form.due_day} onChange={(e) => setForm((f) => ({ ...f, due_day: e.target.value }))} />
                </div>
                <div>
                  <label className={labelClass}>{modal === "new" ? "First due (optional)" : "Next due"}</label>
                  <input type="date" className={inputClass} value={form.next_due_date} onChange={(e) => setForm((f) => ({ ...f, next_due_date: e.target.value }))} />
                </div>
              </div>
              {form.category === "salary" && (
                <div>
                  <label className={labelClass}>Paid to</label>
                  <select className={inputClass} value={form.payee_user_id} onChange={(e) => setForm((f) => ({ ...f, payee_user_id: e.target.value }))}>
                    <option value="">—</option>
                    {users.map((u) => <option key={u.id} value={u.id}>{u.full_name || u.email}</option>)}
                  </select>
                  <p className="text-xs text-gray-400 mt-1">Tip: manage salaries from the Payroll page so each employee has exactly one.</p>
                </div>
              )}
              <div>
                <label className={labelClass}>Remind me</label>
                <div className="flex flex-wrap gap-4 text-sm text-gray-700">
                  <label className="inline-flex items-center gap-1.5"><input type="checkbox" checked={form.remind_2} onChange={(e) => setForm((f) => ({ ...f, remind_2: e.target.checked }))} className="rounded border-gray-300 text-primary" /> 2 days before</label>
                  <label className="inline-flex items-center gap-1.5"><input type="checkbox" checked={form.remind_1} onChange={(e) => setForm((f) => ({ ...f, remind_1: e.target.checked }))} className="rounded border-gray-300 text-primary" /> 1 day before</label>
                  <label className="inline-flex items-center gap-1.5"><input type="checkbox" checked={form.remind_0} onChange={(e) => setForm((f) => ({ ...f, remind_0: e.target.checked }))} className="rounded border-gray-300 text-primary" /> On the day</label>
                </div>
                <p className="text-xs text-gray-400 mt-1">An overdue notice always goes out once if a bill is not marked paid.</p>
              </div>
              <div>
                <label className={labelClass}>Notes (optional)</label>
                <textarea rows={2} className={inputClass} placeholder="Account number, who to pay, how" value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} />
              </div>
            </div>
            <div className="flex items-center justify-between gap-2 mt-5">
              {modal !== "new" ? (
                <button onClick={() => remove(modal)} className="px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg">Delete</button>
              ) : <span />}
              <div className="flex gap-2">
                <button onClick={() => setModal(null)} className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">Cancel</button>
                <button disabled={busy} onClick={save} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover disabled:opacity-50">{busy ? "Saving…" : "Save"}</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Mark paid modal */}
      {payTarget && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-10 p-4" onClick={() => setPayTarget(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-gray-900">Mark paid</h2>
            <p className="text-sm text-gray-500 mt-1">{payTarget.description} · {fmtMoney(payTarget.currency, payTarget.amount)} · due {fmtDate(payTarget.next_due_date)}</p>
            <div className="space-y-3 mt-4">
              <div>
                <label className={labelClass}>Paid on</label>
                <input type="date" className={inputClass} value={payForm.paid_on} onChange={(e) => setPayForm((f) => ({ ...f, paid_on: e.target.value }))} />
              </div>
              <div>
                <label className={labelClass}>Amount actually paid (leave empty for {fmtMoney(payTarget.currency, payTarget.amount)})</label>
                <input type="number" step="0.01" min="0" className={inputClass} value={payForm.amount} onChange={(e) => setPayForm((f) => ({ ...f, amount: e.target.value }))} />
              </div>
              <div>
                <label className={labelClass}>Note (optional)</label>
                <input className={inputClass} placeholder="Reference, bank, anything worth remembering" value={payForm.note} onChange={(e) => setPayForm((f) => ({ ...f, note: e.target.value }))} />
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-3">This writes an expense for the period and moves the next due date forward.</p>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setPayTarget(null)} className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">Cancel</button>
              <button disabled={busy} onClick={confirmPay} className="px-4 py-2 rounded-lg bg-green-600 text-white font-medium hover:bg-green-700 disabled:opacity-50">{busy ? "Saving…" : "Record payment"}</button>
            </div>
          </div>
        </div>
      )}

      {/* History modal */}
      {historyFor && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-10 p-4" onClick={() => setHistoryFor(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-md max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-gray-900">Payment history</h2>
            <p className="text-sm text-gray-500 mt-1">{historyFor.description}</p>
            <ul className="mt-4 divide-y divide-gray-100">
              {history.length === 0 && <li className="py-3 text-sm text-gray-400">No payments recorded yet.</li>}
              {history.map((e) => (
                <li key={e.id} className="py-2.5 flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm text-gray-800 truncate">{e.description}</p>
                    <p className="text-xs text-gray-400">{fmtDate(e.expense_date)}</p>
                  </div>
                  <span className="text-sm font-medium text-gray-900 whitespace-nowrap">{fmtMoney(e.currency, e.amount)}</span>
                </li>
              ))}
            </ul>
            <div className="flex justify-end mt-4">
              <button onClick={() => setHistoryFor(null)} className="px-4 py-2 rounded-lg bg-gray-100 text-gray-700 font-medium hover:bg-gray-200">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
