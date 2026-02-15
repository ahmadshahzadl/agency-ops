import { useEffect, useState } from "react";
import { getOverview } from "@/api/analytics";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

const COLORS = ["#3379b7", "#10b981", "#5b9bd5", "#8b5cf6", "#ec4899"];

export default function AnalyticsPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof getOverview>> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getOverview()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-slate-400">Loading...</div>;
  if (!data) return <div className="text-red-400">Failed to load analytics.</div>;

  const taskChartData = [
    { name: "Todo", value: data.tasks_todo, color: COLORS[0] },
    { name: "In progress", value: data.tasks_in_progress, color: COLORS[1] },
    { name: "Done", value: data.tasks_done, color: COLORS[2] },
  ].filter((d) => d.value > 0);

  const barData = [
    { name: "Clients", value: data.total_clients },
    { name: "Active projects", value: data.active_projects },
    { name: "Tasks (todo)", value: data.tasks_todo },
    { name: "Tasks (in progress)", value: data.tasks_in_progress },
    { name: "Tasks (done)", value: data.tasks_done },
  ];

  return (
    <div>
      <h1 className="text-2xl font-semibold text-white mb-6">Analytics</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-4">
          <h2 className="text-lg font-medium text-slate-200 mb-4">Overview</h2>
          <div className="space-y-2 text-slate-300">
            <p>Clients: <span className="text-white font-medium">{data.total_clients}</span></p>
            <p>Active projects: <span className="text-white font-medium">{data.active_projects}</span></p>
            <p>Revenue (paid): <span className="text-emerald-400 font-medium">
              ${Number(data.revenue_total ?? 0).toLocaleString()}
            </span></p>
            <p>Outstanding: <span className="text-primary font-medium">
              ${Number(data.outstanding_total ?? 0).toLocaleString()}
            </span></p>
          </div>
        </div>

        <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-4">
          <h2 className="text-lg font-medium text-slate-200 mb-4">Tasks by status</h2>
          {taskChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={180}>
              <PieChart>
                <Pie
                  data={taskChartData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={60}
                  label={({ name, value }) => `${name}: ${value}`}
                >
                  {taskChartData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-slate-400">No task data yet.</p>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-4">
        <h2 className="text-lg font-medium text-slate-200 mb-4">Counts</h2>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={barData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
            <YAxis stroke="#94a3b8" fontSize={12} />
            <Tooltip
              contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155" }}
              labelStyle={{ color: "#e2e8f0" }}
            />
            <Bar dataKey="value" fill="#3379b7" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
