import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getPublicStatus, type PublicStatus as Status } from "@/api/share";
import { APP_NAME, getLogoUrl } from "@/config";

const STAGE_LABELS: Record<string, string> = {
  todo: "Planned",
  in_progress: "In progress",
  review: "In review",
  done: "Completed",
};
const STAGE_ORDER = ["in_progress", "review", "todo", "done"];

export default function PublicStatus() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<Status | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!token) return;
    getPublicStatus(token).then(setData).catch(() => setError(true));
  }, [token]);

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[#01184e] text-white p-6">
        <img src={getLogoUrl()} alt="" className="w-16 h-16 mb-4 opacity-90" />
        <h1 className="text-xl font-semibold">This link is no longer active</h1>
        <p className="text-white/60 mt-2 text-sm">Ask your project contact for a new progress link.</p>
      </div>
    );
  }

  if (!data) {
    return <div className="min-h-screen flex items-center justify-center bg-[#01184e] text-white">Loading…</div>;
  }

  const grouped = STAGE_ORDER.map((s) => ({
    key: s,
    label: STAGE_LABELS[s] ?? s,
    tasks: data.tasks.filter((t) => t.status === s),
  })).filter((g) => g.tasks.length > 0);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-[#01184e] text-white">
        <div className="max-w-3xl mx-auto px-6 py-8">
          <div className="flex items-center gap-3">
            <img src={getLogoUrl()} alt="" className="w-10 h-10" />
            <span className="font-semibold tracking-wide">{APP_NAME}</span>
          </div>
          <h1 className="mt-6 text-2xl sm:text-3xl font-bold">{data.project_name}</h1>
          <p className="text-white/60 mt-1 text-sm capitalize">
            {data.project_status}
            {data.end_date && <> · target: {data.end_date}</>}
          </p>
          {/* Progress bar */}
          <div className="mt-6">
            <div className="flex justify-between text-sm mb-1.5">
              <span className="text-white/70">Overall progress</span>
              <span className="font-semibold">{data.percent_done}%</span>
            </div>
            <div className="h-3 rounded-full bg-white/15 overflow-hidden">
              <div className="h-full rounded-full bg-white transition-all" style={{ width: `${data.percent_done}%` }} />
            </div>
            <p className="text-white/50 text-xs mt-1.5">
              {data.counts["done"] ?? 0} of {data.total_tasks} tasks completed
            </p>
          </div>
        </div>
      </div>

      {/* Stage summary */}
      <div className="max-w-3xl mx-auto px-6 -mt-5">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {STAGE_ORDER.map((s) => (
            <div key={s} className="bg-white rounded-xl shadow-sm border border-gray-100 px-4 py-3">
              <p className="text-2xl font-bold text-[#01184e]">{data.counts[s] ?? (s === "review" ? (data.counts["review"] ?? 0) + (data.counts["qa_failed"] ?? 0) : 0)}</p>
              <p className="text-xs text-gray-500 mt-0.5">{STAGE_LABELS[s]}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Task list */}
      <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
        {grouped.map((g) => (
          <div key={g.key}>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">{g.label}</h2>
            <ul className="bg-white rounded-xl shadow-sm border border-gray-100 divide-y divide-gray-50">
              {g.tasks.map((t, i) => (
                <li key={i} className="flex items-center gap-3 px-4 py-3">
                  <span
                    className={`w-2 h-2 rounded-full shrink-0 ${
                      g.key === "done" ? "bg-green-500" : g.key === "in_progress" ? "bg-blue-500" : g.key === "review" ? "bg-amber-500" : "bg-gray-300"
                    }`}
                  />
                  <span className={`text-sm ${g.key === "done" ? "text-gray-400 line-through" : "text-gray-700"}`}>{t.title}</span>
                  {t.due_date && g.key !== "done" && <span className="ml-auto text-xs text-gray-400">{t.due_date}</span>}
                </li>
              ))}
            </ul>
          </div>
        ))}
        <p className="text-center text-xs text-gray-400 pt-4">
          Updated {new Date(data.generated_at + "Z").toLocaleString()} · Powered by {APP_NAME}
        </p>
      </div>
    </div>
  );
}
