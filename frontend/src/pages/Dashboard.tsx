import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getOverview } from "@/api/analytics";

export default function Dashboard() {
  const [data, setData] = useState<Awaited<ReturnType<typeof getOverview>> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getOverview()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-slate-400">Loading...</div>;
  if (!data) return <div className="text-red-400">Failed to load overview.</div>;

  const cards = [
    { label: "Clients", value: data.total_clients, to: "/clients" },
    { label: "Active projects", value: data.active_projects, to: "/projects" },
    { label: "Tasks (todo)", value: data.tasks_todo, to: "/tasks" },
    { label: "Tasks (in progress)", value: data.tasks_in_progress, to: "/tasks" },
    { label: "Tasks (done)", value: data.tasks_done, to: "/tasks" },
    {
      label: "Revenue",
      value: data.revenue_total != null ? `$${Number(data.revenue_total).toLocaleString()}` : "—",
      to: "/invoices",
    },
    {
      label: "Outstanding",
      value: data.outstanding_total != null ? `$${Number(data.outstanding_total).toLocaleString()}` : "—",
      to: "/invoices",
    },
  ];

  return (
    <div>
      <h1 className="text-2xl font-semibold text-white mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {cards.map((c) => (
          <Link
            key={c.label}
            to={c.to}
            className="rounded-xl border border-slate-700 bg-slate-800/50 p-4 hover:border-primary/50 transition-colors"
          >
            <p className="text-slate-400 text-sm">{c.label}</p>
            <p className="text-xl font-semibold text-white mt-1">{c.value}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
