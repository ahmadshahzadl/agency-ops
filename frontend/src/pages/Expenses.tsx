import { useEffect, useState } from "react";
import { listExpenses, createExpense, updateExpense, deleteExpense, type Expense } from "@/api/finance";
import { listProjects, type Project } from "@/api/projects";
import { useAuth } from "@/store/auth";

export default function ExpensesPage() {
  const [items, setItems] = useState<Expense[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [projectFilter, setProjectFilter] = useState("");
  const [searchText, setSearchText] = useState("");
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
    listProjects().then(setProjects).catch(() => setProjects([]));
    const params = projectFilter ? { project_id: projectFilter } : undefined;
    listExpenses(params).then(setItems).catch(() => setItems([])).finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [projectFilter]);

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
  const searchLower = searchText.trim().toLowerCase();
  const filteredItems = searchLower
    ? items.filter(
        (e) =>
          (e.description ?? "").toLowerCase().includes(searchLower) ||
          String(e.amount).includes(searchText.trim()) ||
          (e.expense_date ?? "").toLowerCase().includes(searchLower) ||
          (e.project_id && (projectMap[e.project_id] ?? "").toLowerCase().includes(searchLower))
      )
    : items;
  const inputClass = "w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <label className="text-sm font-medium text-gray-700">Project</label>
          <select
            value={projectFilter}
            onChange={(e) => setProjectFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[180px]"
          >
            <option value="">All projects</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <label className="text-sm font-medium text-gray-700">Search</label>
          <input
            type="search"
            placeholder="Description, amount, date, project..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[200px]"
          />
        </div>
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
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600">
              <tr>
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3">Project</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Date</th>
                {canWrite && <th className="px-4 py-3 w-24 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredItems.map((e) => (
                <tr key={e.id} className="hover:bg-gray-50/80">
                  <td className="px-4 py-3 font-medium text-gray-900">{e.description}</td>
                  <td className="px-4 py-3 text-gray-600">{e.project_id ? projectMap[e.project_id] || e.project_id : "—"}</td>
                  <td className="px-4 py-3 text-gray-600">
                    {e.currency} {Number(e.amount).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{e.expense_date || "—"}</td>
                  {canWrite && (
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button type="button" onClick={() => openEdit(e)} title="Edit" className="p-1.5 rounded-lg text-gray-500 hover:text-primary hover:bg-gray-100 transition-colors">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                        <button type="button" onClick={() => remove(e.id)} title="Delete" className="p-1.5 rounded-lg text-gray-500 hover:text-red-600 hover:bg-gray-100 transition-colors">
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
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-md" onClick={(ev) => ev.stopPropagation()}>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">{modal === "new" ? "New expense" : "Edit expense"}</h2>
            <div className="space-y-3">
              <div>
                <label className={labelClass}>Project (optional)</label>
                <select
                  value={form.project_id}
                  onChange={(e) => setForm((f) => ({ ...f, project_id: e.target.value }))}
                  className={inputClass}
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
                <label className={labelClass}>Date</label>
                <input
                  type="date"
                  value={form.expense_date}
                  onChange={(e) => setForm((f) => ({ ...f, expense_date: e.target.value }))}
                  className={inputClass}
                />
              </div>
            </div>
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
