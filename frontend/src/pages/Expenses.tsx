import { useEffect, useState } from "react";
import { listExpenses, createExpense, updateExpense, deleteExpense, type Expense } from "@/api/finance";
import { listProjects, type Project } from "@/api/projects";
import { useAuth } from "@/store/auth";

export default function ExpensesPage() {
  const [items, setItems] = useState<Expense[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<"new" | Expense | null>(null);
  const [form, setForm] = useState({
    project_id: "",
    description: "",
    amount: "",
    currency: "USD",
    expense_date: "",
  });
  const { hasPermission } = useAuth();

  const load = () => {
    Promise.all([listExpenses(), listProjects()]).then(([e, p]) => {
      setItems(e);
      setProjects(p);
    }).finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const openNew = () => {
    setForm({
      project_id: "",
      description: "",
      amount: "",
      currency: "USD",
      expense_date: new Date().toISOString().slice(0, 10),
    });
    setModal("new");
  };
  const openEdit = (e: Expense) => {
    setForm({
      project_id: e.project_id || "",
      description: e.description,
      amount: String(e.amount),
      currency: e.currency,
      expense_date: e.expense_date || "",
    });
    setModal(e);
  };

  const save = async () => {
    if (modal === null) return;
    const payload = {
      project_id: form.project_id || undefined,
      description: form.description,
      amount: Number(form.amount),
      currency: form.currency,
      expense_date: form.expense_date || undefined,
    };
    try {
      if (modal === "new") {
        await createExpense(payload as Expense);
      } else {
        await updateExpense(modal.id, payload);
      }
      setModal(null);
      load();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed");
    }
  };

  const remove = async (id: string) => {
    if (!confirm("Delete this expense?")) return;
    try {
      await deleteExpense(id);
      setModal(null);
      load();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed");
    }
  };

  const canWrite = hasPermission("finance:write");
  const projectMap = Object.fromEntries(projects.map((p) => [p.id, p.name]));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-white">Expenses</h1>
        {canWrite && (
          <button
            onClick={openNew}
            className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover"
          >
            Add expense
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
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3">Project</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Date</th>
                {canWrite && <th className="px-4 py-3 w-24"></th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {items.map((e) => (
                <tr key={e.id} className="hover:bg-slate-800/50">
                  <td className="px-4 py-3 text-white">{e.description}</td>
                  <td className="px-4 py-3 text-slate-300">{e.project_id ? projectMap[e.project_id] || e.project_id : "—"}</td>
                  <td className="px-4 py-3 text-slate-300">
                    {e.currency} {Number(e.amount).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-slate-300">{e.expense_date || "—"}</td>
                  {canWrite && (
                    <td className="px-4 py-3">
                      <button onClick={() => openEdit(e)} className="text-primary hover:underline mr-2">
                        Edit
                      </button>
                      <button onClick={() => remove(e.id)} className="text-red-400 hover:underline">
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
          <div className="bg-slate-800 rounded-xl border border-slate-700 p-6 w-full max-w-md" onClick={(ev) => ev.stopPropagation()}>
            <h2 className="text-lg font-semibold text-white mb-4">{modal === "new" ? "New expense" : "Edit expense"}</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-slate-400 mb-1">Project (optional)</label>
                <select
                  value={form.project_id}
                  onChange={(e) => setForm((f) => ({ ...f, project_id: e.target.value }))}
                  className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                >
                  <option value="">—</option>
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <input
                placeholder="Description"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
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
              <input
                type="date"
                value={form.expense_date}
                onChange={(e) => setForm((f) => ({ ...f, expense_date: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
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
    </div>
  );
}
