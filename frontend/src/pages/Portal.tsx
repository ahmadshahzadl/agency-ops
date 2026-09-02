import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/store/auth";
import { APP_NAME, getBrandMarkUrl } from "@/config";
import {
  getPortalOverview, getPortalProject, listPortalInvoices, listPortalQuotes,
  acceptPortalQuote, declinePortalQuote, reportPortalIssue, openPortalPdf,
  type PortalOverview, type PortalProjectDetail, type PortalInvoice, type PortalQuote,
} from "@/api/portal";

const TASK_LABELS: Record<string, string> = { todo: "Planned", in_progress: "In progress", review: "In review", done: "Completed" };
const INVOICE_BADGE: Record<string, string> = {
  sent: "bg-blue-100 text-blue-700",
  overdue: "bg-red-100 text-red-600",
  paid: "bg-green-100 text-green-700",
};
const QUOTE_BADGE: Record<string, string> = {
  sent: "bg-blue-100 text-blue-700",
  accepted: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-600",
  expired: "bg-amber-100 text-amber-700",
};

export default function Portal() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [overview, setOverview] = useState<PortalOverview | null>(null);
  const [invoices, setInvoices] = useState<PortalInvoice[]>([]);
  const [quotes, setQuotes] = useState<PortalQuote[]>([]);
  const [detail, setDetail] = useState<PortalProjectDetail | null>(null);
  const [issueFor, setIssueFor] = useState<string | null>(null);
  const [issue, setIssue] = useState({ title: "", description: "", steps_to_reproduce: "", severity: "medium" });
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(() => {
    getPortalOverview().then(setOverview).catch(() => {});
    listPortalInvoices().then(setInvoices).catch(() => {});
    listPortalQuotes().then(setQuotes).catch(() => {});
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const flash = (msg: string) => {
    setNotice(msg);
    window.setTimeout(() => setNotice(null), 4000);
  };

  const inputClass = "w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 text-sm focus:ring-2 focus:ring-[#01184e]/30 focus:border-[#01184e]";

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-[#01184e] text-white">
        <div className="max-w-4xl mx-auto px-6 py-5 flex items-center gap-3">
          <img src={getBrandMarkUrl()} alt="" className="w-9 h-9" />
          <div className="min-w-0">
            <p className="font-semibold leading-tight">{APP_NAME} · Client portal</p>
            <p className="text-white/60 text-sm truncate">{overview?.client_name ?? user?.client_name ?? ""}</p>
          </div>
          <button
            onClick={async () => { await logout(); navigate("/login"); }}
            className="ml-auto text-sm text-white/70 hover:text-white"
          >
            Sign out
          </button>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-10">
        {notice && <div className="rounded-lg bg-green-50 border border-green-200 text-green-700 text-sm px-4 py-2.5">{notice}</div>}

        {/* Projects */}
        <section>
          <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">Your projects</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            {overview?.projects.map((p) => (
              <button
                key={p.id}
                onClick={() => getPortalProject(p.id).then(setDetail).catch(() => {})}
                className="text-left bg-white rounded-xl shadow-sm border border-gray-100 p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="font-semibold text-gray-800">{p.name}</p>
                  <span className="text-xs text-gray-400 capitalize">{p.status}</span>
                </div>
                <div className="mt-3 h-2 rounded-full bg-gray-100 overflow-hidden">
                  <div className="h-full bg-[#01184e] rounded-full" style={{ width: `${p.percent_done}%` }} />
                </div>
                <p className="mt-1.5 text-xs text-gray-400">{p.percent_done}% · {p.total_tasks} tasks{p.end_date ? ` · target ${p.end_date}` : ""}</p>
              </button>
            ))}
            {overview && overview.projects.length === 0 && (
              <p className="text-sm text-gray-400">No projects yet.</p>
            )}
          </div>
        </section>

        {/* Quotes */}
        {quotes.length > 0 && (
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">Proposals</h2>
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 divide-y divide-gray-50">
              {quotes.map((q) => (
                <div key={q.id} className="px-4 py-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-gray-800">{q.title}</span>
                    <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${QUOTE_BADGE[q.status] ?? "bg-gray-100 text-gray-600"}`}>{q.status}</span>
                    <span className="ml-auto font-semibold text-gray-800">{Number(q.total).toFixed(2)} {q.currency}</span>
                  </div>
                  {q.valid_until && q.status === "sent" && <p className="text-xs text-gray-400 mt-0.5">Valid until {q.valid_until}</p>}
                  <div className="mt-2 flex gap-3">
                    <button onClick={() => openPortalPdf("quotes", q.id).catch(() => flash("Could not load PDF"))} className="text-xs font-medium text-gray-500 hover:text-[#01184e] underline-offset-2 hover:underline">View PDF</button>
                    {q.status === "sent" && (
                      <>
                        <button
                          onClick={() => acceptPortalQuote(q.id).then(() => { refresh(); flash("Proposal accepted — thank you! We'll be in touch shortly."); }).catch((e) => flash(e.message))}
                          className="text-xs font-semibold text-white bg-green-600 hover:bg-green-700 rounded-lg px-3 py-1"
                        >
                          Accept proposal
                        </button>
                        <button
                          onClick={() => declinePortalQuote(q.id).then(refresh).catch((e) => flash(e.message))}
                          className="text-xs font-medium text-red-500 hover:underline"
                        >
                          Decline
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Invoices */}
        {invoices.length > 0 && (
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">Invoices</h2>
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-x-auto">
              <table className="w-full text-sm">
                <tbody className="divide-y divide-gray-50">
                  {invoices.map((i) => (
                    <tr key={i.id}>
                      <td className="px-4 py-2.5 font-mono text-xs text-gray-500">{i.number}</td>
                      <td className="px-4 py-2.5">
                        <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${INVOICE_BADGE[i.status] ?? "bg-gray-100 text-gray-600"}`}>{i.status}</span>
                      </td>
                      <td className="px-4 py-2.5 text-gray-500 text-xs">{i.due_date ? `due ${i.due_date}` : ""}</td>
                      <td className="px-4 py-2.5 text-right font-medium text-gray-800 whitespace-nowrap">
                        {Number(i.amount).toFixed(2)} {i.currency}
                        {Number(i.paid_total) > 0 && Number(i.paid_total) < Number(i.amount) && (
                          <span className="block text-[11px] font-normal text-gray-400">paid {Number(i.paid_total).toFixed(2)}</span>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <button onClick={() => openPortalPdf("invoices", i.id).catch(() => flash("Could not load PDF"))} className="text-xs font-medium text-gray-500 hover:text-[#01184e] hover:underline">PDF</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </div>

      {/* Project detail */}
      {detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => { setDetail(null); setIssueFor(null); }}>
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 max-h-[88vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">{detail.name}</h3>
              <span className="text-sm font-semibold text-[#01184e]">{detail.percent_done}%</span>
            </div>

            {detail.milestones.length > 0 && (
              <div className="mt-4">
                <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">Milestones</h4>
                <ul className="space-y-1.5">
                  {detail.milestones.map((m, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm">
                      <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] shrink-0 ${m.completed ? "bg-green-500 text-white" : "bg-gray-200 text-gray-500"}`}>{m.completed ? "✓" : i + 1}</span>
                      <span className={m.completed ? "text-gray-400 line-through" : "text-gray-700"}>{m.name}</span>
                      {m.due_date && <span className="ml-auto text-xs text-gray-400">{m.due_date}</span>}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-4">
              <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">Work items</h4>
              <ul className="space-y-1">
                {detail.tasks.map((t, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm">
                    <span className={`w-2 h-2 rounded-full shrink-0 ${t.status === "done" ? "bg-green-500" : t.status === "in_progress" ? "bg-blue-500" : t.status === "review" ? "bg-amber-500" : "bg-gray-300"}`} />
                    <span className={t.status === "done" ? "text-gray-400 line-through" : "text-gray-700"}>{t.title}</span>
                    <span className="ml-auto text-[11px] text-gray-400">{TASK_LABELS[t.status] ?? t.status}</span>
                  </li>
                ))}
                {detail.tasks.length === 0 && <li className="text-xs text-gray-400">No work items yet.</li>}
              </ul>
            </div>

            {/* Report an issue */}
            {issueFor === detail.id ? (
              <div className="mt-5 rounded-xl border border-gray-200 p-3 space-y-2">
                <input autoFocus className={inputClass} placeholder="What's wrong? *" value={issue.title} onChange={(e) => setIssue({ ...issue, title: e.target.value })} />
                <textarea rows={2} className={inputClass} placeholder="Details (optional)" value={issue.description} onChange={(e) => setIssue({ ...issue, description: e.target.value })} />
                <textarea rows={2} className={inputClass} placeholder="Steps to reproduce (optional)" value={issue.steps_to_reproduce} onChange={(e) => setIssue({ ...issue, steps_to_reproduce: e.target.value })} />
                <div className="flex items-center gap-2">
                  <select className={`${inputClass} !w-auto`} value={issue.severity} onChange={(e) => setIssue({ ...issue, severity: e.target.value })}>
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="critical">Critical</option>
                  </select>
                  <button
                    disabled={!issue.title.trim()}
                    onClick={() =>
                      reportPortalIssue(detail.id, {
                        title: issue.title.trim(),
                        description: issue.description || undefined,
                        steps_to_reproduce: issue.steps_to_reproduce || undefined,
                        severity: issue.severity,
                      }).then(() => {
                        setIssueFor(null);
                        setIssue({ title: "", description: "", steps_to_reproduce: "", severity: "medium" });
                        setDetail(null);
                        flash("Issue reported — our team has been notified.");
                      }).catch((e) => flash(e.message))
                    }
                    className="ml-auto px-4 py-2 rounded-lg bg-[#01184e] text-white text-sm font-medium hover:bg-[#032a75] disabled:opacity-50"
                  >
                    Submit issue
                  </button>
                  <button onClick={() => setIssueFor(null)} className="text-sm text-gray-500">Cancel</button>
                </div>
              </div>
            ) : (
              <div className="mt-5 flex justify-between">
                <button onClick={() => setIssueFor(detail.id)} className="text-sm font-medium text-[#01184e] hover:underline">⚠ Report an issue</button>
                <button onClick={() => setDetail(null)} className="text-sm text-gray-500 hover:text-gray-800">Close</button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
