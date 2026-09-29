import { useEffect, useMemo, useState } from "react";
import { listPayroll, updatePayroll, payRecurringExpense, recurringExpenseHistory, type PayrollRow, type EmploymentType, type RecurringFrequency, type Expense } from "@/api/finance";
import { useAuth } from "@/store/auth";
import { useModal } from "@/contexts/ModalContext";
import { StatusChip, fmtMoney, fmtDate, FREQUENCY_LABEL } from "@/components/RecurringExpenses";

const EMPLOYMENT_LABEL: Record<EmploymentType, string> = {
  full_time: "Full-time", part_time: "Part-time", contractor: "Contractor", intern: "Intern",
};

export default function PayrollPage() {
  const { hasPermission } = useAuth();
  const { showAlert } = useModal();
  const canWrite = hasPermission("finance:write") || hasPermission("expenses:write");
  const [rows, setRows] = useState<PayrollRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [search, setSearch] = useState("");
  const [edit, setEdit] = useState<PayrollRow | null>(null);
  const [form, setForm] = useState({ amount: "", currency: "PKR", due_day: "1", frequency: "monthly" as RecurringFrequency, salary_active: true, employment_type: "" as EmploymentType | "", joined_on: "", left_on: "", job_title: "" });
  const [pay, setPay] = useState<PayrollRow | null>(null);
  const [payForm, setPayForm] = useState({ paid_on: "", amount: "", note: "" });
  const [historyFor, setHistoryFor] = useState<PayrollRow | null>(null);
  const [history, setHistory] = useState<Expense[]>([]);
  const [busy, setBusy] = useState(false);

  const load = () => {
    setLoading(true);
    listPayroll(includeInactive).then(setRows).catch(() => setRows([])).finally(() => setLoading(false));
  };
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [includeInactive]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => (r.full_name ?? "").toLowerCase().includes(q) || r.email.toLowerCase().includes(q) || (r.job_title ?? "").toLowerCase().includes(q));
  }, [rows, search]);

  const totals = useMemo(() => {
    const byCur: Record<string, number> = {};
    for (const r of rows) {
      if (!r.salary_id || !r.salary_active || r.amount == null || !r.currency) continue;
      const monthly = r.frequency === "weekly" ? Number(r.amount) * 52 / 12 : r.frequency === "quarterly" ? Number(r.amount) / 3 : r.frequency === "yearly" ? Number(r.amount) / 12 : Number(r.amount);
      byCur[r.currency] = (byCur[r.currency] ?? 0) + monthly;
    }
    return byCur;
  }, [rows]);
  const withSalary = rows.filter((r) => r.salary_id && r.salary_active).length;
  const attention = rows.filter((r) => r.status === "overdue" || r.status === "due_today" || r.status === "due_soon").length;

  const openEdit = (r: PayrollRow) => {
    setForm({
      amount: r.amount != null ? String(r.amount) : "", currency: r.currency ?? "PKR", due_day: String(r.due_day ?? 1),
      frequency: r.frequency ?? "monthly", salary_active: r.salary_id ? r.salary_active : true,
      employment_type: r.employment_type ?? "", joined_on: r.joined_on ?? "", left_on: r.left_on ?? "", job_title: r.job_title ?? "",
    });
    setEdit(r);
  };

  const save = async () => {
    if (!edit) return;
    const hasSalary = form.amount.trim() !== "";
    if (hasSalary && !(Number(form.amount) > 0)) { showAlert({ title: "Check the form", message: "Salary must be above zero, or leave it empty to only update the employment record." }); return; }
    setBusy(true);
    try {
      await updatePayroll(edit.user_id, {
        ...(hasSalary ? { amount: Number(form.amount), currency: form.currency, due_day: Number(form.due_day) || 1, frequency: form.frequency, salary_active: form.salary_active } : {}),
        employment_type: form.employment_type || null,
        joined_on: form.joined_on || null,
        left_on: form.left_on || null,
        job_title: form.job_title || null,
      });
      setEdit(null);
      load();
    } catch (e) { showAlert({ title: "Error", message: e instanceof Error ? e.message : "Could not save" }); }
    finally { setBusy(false); }
  };

  const openPay = (r: PayrollRow) => {
    setPay(r);
    setPayForm({ paid_on: new Date().toISOString().slice(0, 10), amount: "", note: "" });
  };
  const confirmPay = async () => {
    if (!pay?.salary_id) return;
    setBusy(true);
    try {
      await payRecurringExpense(pay.salary_id, { paid_on: payForm.paid_on || undefined, amount: payForm.amount ? Number(payForm.amount) : undefined, note: payForm.note || undefined });
      setPay(null);
      load();
    } catch (e) { showAlert({ title: "Error", message: e instanceof Error ? e.message : "Could not record payment" }); }
    finally { setBusy(false); }
  };

  const openHistory = async (r: PayrollRow) => {
    if (!r.salary_id) return;
    setHistoryFor(r);
    setHistory(await recurringExpenseHistory(r.salary_id).catch(() => []));
  };

  const inputClass = "w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm";
  const labelClass = "block text-xs font-medium text-gray-500 mb-1";

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm p-4">
          <p className="text-xs uppercase tracking-wide text-gray-400">On payroll</p>
          <p className="text-2xl font-semibold text-gray-900 mt-1">{withSalary}<span className="text-base font-normal text-gray-400"> / {rows.length} staff</span></p>
          <p className="text-xs text-gray-500 mt-1">{rows.length - withSalary} without a salary set</p>
        </div>
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm p-4">
          <p className="text-xs uppercase tracking-wide text-gray-400">Monthly payroll</p>
          <div className="mt-1 space-y-0.5">
            {Object.keys(totals).length === 0 && <p className="text-2xl font-semibold text-gray-900">—</p>}
            {Object.entries(totals).map(([cur, v]) => <p key={cur} className="text-lg font-semibold text-gray-900">{fmtMoney(cur, v)}</p>)}
          </div>
        </div>
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm p-4">
          <p className="text-xs uppercase tracking-wide text-gray-400">Needs attention</p>
          <p className={`text-2xl font-semibold mt-1 ${attention ? "text-amber-700" : "text-gray-900"}`}>{attention}</p>
          <p className="text-xs text-gray-500 mt-1">Due within 7 days or overdue. Reminders go out 2 days and 1 day before pay day.</p>
        </div>
      </div>

      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3 flex-wrap">
          <input type="search" placeholder="Search staff..." value={search} onChange={(e) => setSearch(e.target.value)} className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[200px]" />
          <label className="inline-flex items-center gap-2 text-sm text-gray-600">
            <input type="checkbox" checked={includeInactive} onChange={(e) => setIncludeInactive(e.target.checked)} className="rounded border-gray-300 text-primary focus:ring-primary/20" />
            Include deactivated accounts
          </label>
        </div>
        <p className="text-xs text-gray-400">Add people on the Users page; set their salary here.</p>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-x-auto">
          <table className="w-full min-w-[820px]">
            <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600">
              <tr>
                <th className="px-4 py-3">Employee</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Salary</th>
                <th className="px-4 py-3">Pay day</th>
                <th className="px-4 py-3">Next pay</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Last paid</th>
                {canWrite && <th className="px-4 py-3 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filtered.map((r) => (
                <tr key={r.user_id} className={`hover:bg-gray-50/80 ${!r.is_active || r.left_on ? "opacity-60" : ""}`}>
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{r.full_name || r.email}</p>
                    <p className="text-xs text-gray-500">{r.job_title || r.email}{r.joined_on ? ` · since ${fmtDate(r.joined_on)}` : ""}{r.left_on ? ` · left ${fmtDate(r.left_on)}` : ""}</p>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{r.employment_type ? EMPLOYMENT_LABEL[r.employment_type] : "—"}</td>
                  <td className="px-4 py-3 text-gray-700 whitespace-nowrap">
                    {r.salary_id ? fmtMoney(r.currency, r.amount) : <span className="text-gray-400">Not set</span>}
                    {r.salary_id && r.frequency && r.frequency !== "monthly" && <span className="text-xs text-gray-400"> / {FREQUENCY_LABEL[r.frequency].toLowerCase()}</span>}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{r.salary_id && r.due_day ? `Day ${r.due_day}` : "—"}</td>
                  <td className="px-4 py-3 text-gray-700 whitespace-nowrap">{fmtDate(r.next_due_date)}</td>
                  <td className="px-4 py-3"><StatusChip status={r.status} days={r.days_until_due} /></td>
                  <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                    {r.salary_id ? <button onClick={() => openHistory(r)} className="hover:underline" title="Payment history">{fmtDate(r.last_paid_on)}</button> : "—"}
                  </td>
                  {canWrite && (
                    <td className="px-4 py-3 text-right whitespace-nowrap">
                      <div className="inline-flex items-center gap-1">
                        {r.salary_id && r.salary_active && (
                          <button onClick={() => openPay(r)} className="px-2.5 py-1 rounded-lg text-xs font-medium bg-green-600 text-white hover:bg-green-700">Mark paid</button>
                        )}
                        <button onClick={() => openEdit(r)} className="px-2.5 py-1 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-100">{r.salary_id ? "Edit" : "Set salary"}</button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={8} className="px-4 py-8 text-center text-sm text-gray-400">No staff match.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Edit modal */}
      {edit && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-10 p-4" onClick={() => setEdit(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-gray-900">{edit.full_name || edit.email}</h2>
            <p className="text-sm text-gray-500 mt-0.5">{edit.email}</p>

            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mt-5 mb-2">Employment</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass}>Job title</label>
                <input className={inputClass} value={form.job_title} onChange={(e) => setForm((f) => ({ ...f, job_title: e.target.value }))} />
              </div>
              <div>
                <label className={labelClass}>Type</label>
                <select className={inputClass} value={form.employment_type} onChange={(e) => setForm((f) => ({ ...f, employment_type: e.target.value as EmploymentType | "" }))}>
                  <option value="">—</option>
                  {Object.entries(EMPLOYMENT_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div>
                <label className={labelClass}>Joined on</label>
                <input type="date" className={inputClass} value={form.joined_on} onChange={(e) => setForm((f) => ({ ...f, joined_on: e.target.value }))} />
              </div>
              <div>
                <label className={labelClass}>Left on (if applicable)</label>
                <input type="date" className={inputClass} value={form.left_on} onChange={(e) => setForm((f) => ({ ...f, left_on: e.target.value }))} />
              </div>
            </div>

            <p className="text-xs font-semibold uppercase tracking-wide text-gray-400 mt-5 mb-2">Salary</p>
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <label className={labelClass}>Amount per period</label>
                <input type="number" step="0.01" min="0" className={inputClass} placeholder="Leave empty if unpaid" value={form.amount} onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} />
              </div>
              <div>
                <label className={labelClass}>Currency</label>
                <select className={inputClass} value={form.currency} onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value }))}>
                  {["PKR", "USD", "AED", "GBP", "EUR"].map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className={labelClass}>Paid</label>
                <select className={inputClass} value={form.frequency} onChange={(e) => setForm((f) => ({ ...f, frequency: e.target.value as RecurringFrequency }))}>
                  {Object.entries(FREQUENCY_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
              </div>
              <div>
                <label className={labelClass}>Pay day of month</label>
                <input type="number" min="1" max="31" className={inputClass} disabled={form.frequency === "weekly"} value={form.due_day} onChange={(e) => setForm((f) => ({ ...f, due_day: e.target.value }))} />
              </div>
              <div className="flex items-end pb-2">
                <label className="inline-flex items-center gap-2 text-sm text-gray-700">
                  <input type="checkbox" checked={form.salary_active} onChange={(e) => setForm((f) => ({ ...f, salary_active: e.target.checked }))} className="rounded border-gray-300 text-primary" />
                  Active
                </label>
              </div>
            </div>
            <p className="text-xs text-gray-400 mt-2">Reminders go to finance users 2 days before, 1 day before and on pay day. Marking paid records a salary expense against this person.</p>

            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setEdit(null)} className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">Cancel</button>
              <button disabled={busy} onClick={save} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover disabled:opacity-50">{busy ? "Saving…" : "Save"}</button>
            </div>
          </div>
        </div>
      )}

      {/* Mark paid modal */}
      {pay && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-10 p-4" onClick={() => setPay(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-gray-900">Pay {pay.full_name || pay.email}</h2>
            <p className="text-sm text-gray-500 mt-1">{fmtMoney(pay.currency, pay.amount)} · due {fmtDate(pay.next_due_date)}</p>
            <div className="space-y-3 mt-4">
              <div>
                <label className={labelClass}>Paid on</label>
                <input type="date" className={inputClass} value={payForm.paid_on} onChange={(e) => setPayForm((f) => ({ ...f, paid_on: e.target.value }))} />
              </div>
              <div>
                <label className={labelClass}>Amount actually paid (leave empty for {fmtMoney(pay.currency, pay.amount)})</label>
                <input type="number" step="0.01" min="0" className={inputClass} value={payForm.amount} onChange={(e) => setPayForm((f) => ({ ...f, amount: e.target.value }))} />
              </div>
              <div>
                <label className={labelClass}>Note (optional)</label>
                <input className={inputClass} placeholder="Bonus, deduction, bank reference" value={payForm.note} onChange={(e) => setPayForm((f) => ({ ...f, note: e.target.value }))} />
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button onClick={() => setPay(null)} className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">Cancel</button>
              <button disabled={busy} onClick={confirmPay} className="px-4 py-2 rounded-lg bg-green-600 text-white font-medium hover:bg-green-700 disabled:opacity-50">{busy ? "Saving…" : "Record payment"}</button>
            </div>
          </div>
        </div>
      )}

      {/* History modal */}
      {historyFor && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-10 p-4" onClick={() => setHistoryFor(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-md max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-gray-900">Salary history</h2>
            <p className="text-sm text-gray-500 mt-1">{historyFor.full_name || historyFor.email}</p>
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
