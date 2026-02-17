import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { getDashboard, type DashboardResponse } from "@/api/analytics";

const CHART_COLORS = ["#6366f1", "#22c55e", "#eab308", "#ef4444", "#8b5cf6", "#06b6d4"];
const TASK_STATUS_LABELS: Record<string, string> = {
  todo: "To do",
  in_progress: "In progress",
  done: "Done",
};
const LEAD_STATUS_LABELS: Record<string, string> = {
  new: "New",
  contacted: "Contacted",
  qualified: "Qualified",
  converted: "Converted",
  lost: "Lost",
  closed: "Closed",
  dead: "Dead",
};

function formatStatus(s: string, labels: Record<string, string>) {
  return labels[s] ?? s;
}

export default function Dashboard() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-slate-400">Loading...</div>;
  if (!data) return <div className="text-red-400">Failed to load dashboard.</div>;

  const isMemberView =
    data.total_clients === 0 &&
    data.active_projects === 0 &&
    (data.revenue_total == null || Number(data.revenue_total) === 0);

  const cards = [
    ...(data.total_clients > 0 || !isMemberView
      ? [{ label: "Clients", value: data.total_clients, to: "/clients" as const }]
      : []),
    ...(data.active_projects > 0 || !isMemberView
      ? [{ label: "Active projects", value: data.active_projects, to: "/projects" as const }]
      : []),
    { label: "Tasks (todo)", value: data.tasks_todo, to: "/tasks" as const },
    { label: "Tasks (in progress)", value: data.tasks_in_progress, to: "/tasks" as const },
    { label: "Tasks (done)", value: data.tasks_done, to: "/tasks" as const },
    ...(data.revenue_total != null && Number(data.revenue_total) > 0
      ? [
          {
            label: "Revenue",
            value: `$${Number(data.revenue_total).toLocaleString()}`,
            to: "/invoices" as const,
          },
        ]
      : []),
    ...(data.outstanding_total != null && Number(data.outstanding_total) > 0
      ? [
          {
            label: "Outstanding",
            value: `$${Number(data.outstanding_total).toLocaleString()}`,
            to: "/invoices" as const,
          },
        ]
      : []),
  ];

  if (data.conversion_rate != null && isMemberView) {
    cards.push({
      label: "Conversion rate",
      value: `${(data.conversion_rate * 100).toFixed(1)}%`,
      to: "/leads" as const,
    });
  }

  const hasConversionLine = data.conversion_over_time.length > 0;
  const hasTasksCharts = data.tasks_by_status.some((s) => s.count > 0);
  const hasLeadsBar = data.leads_by_status.length > 0;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-semibold text-white">Dashboard</h1>

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

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {hasConversionLine && (
          <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-4">
            <h2 className="text-lg font-medium text-white mb-4">Leads converted over time</h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.conversion_over_time} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                  <XAxis dataKey="month" stroke="#94a3b8" fontSize={12} />
                  <YAxis stroke="#94a3b8" fontSize={12} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ background: "#1e293b", border: "1px solid #475569", borderRadius: "8px" }}
                    labelStyle={{ color: "#e2e8f0" }}
                    formatter={(value: number) => [value, "Converted"]}
                    labelFormatter={(label) => `Month: ${label}`}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="converted_count"
                    name="Converted"
                    stroke={CHART_COLORS[0]}
                    strokeWidth={2}
                    dot={{ fill: CHART_COLORS[0] }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {hasTasksCharts && (
          <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-4">
            <h2 className="text-lg font-medium text-white mb-4">Tasks by status</h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data.tasks_by_status.map((s) => ({
                    ...s,
                    name: formatStatus(s.status, TASK_STATUS_LABELS),
                  }))}
                  margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                  <XAxis dataKey="name" stroke="#94a3b8" fontSize={12} />
                  <YAxis stroke="#94a3b8" fontSize={12} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ background: "#1e293b", border: "1px solid #475569", borderRadius: "8px" }}
                    formatter={(value: number) => [value, "Tasks"]}
                  />
                  <Bar dataKey="count" name="Tasks" fill={CHART_COLORS[0]} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {hasLeadsBar && (
          <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-4">
            <h2 className="text-lg font-medium text-white mb-4">Leads by status</h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data.leads_by_status.map((s) => ({
                    ...s,
                    name: formatStatus(s.status, LEAD_STATUS_LABELS),
                  }))}
                  margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
                  layout="vertical"
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#475569" />
                  <XAxis type="number" stroke="#94a3b8" fontSize={12} allowDecimals={false} />
                  <YAxis type="category" dataKey="name" stroke="#94a3b8" fontSize={12} width={90} />
                  <Tooltip
                    contentStyle={{ background: "#1e293b", border: "1px solid #475569", borderRadius: "8px" }}
                    formatter={(value: number) => [value, "Leads"]}
                  />
                  <Bar dataKey="count" name="Leads" fill={CHART_COLORS[1]} radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {hasTasksCharts && (
          <div className="rounded-xl border border-slate-700 bg-slate-800/50 p-4">
            <h2 className="text-lg font-medium text-white mb-4">Task distribution</h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.tasks_by_status.map((s) => ({
                      ...s,
                      name: formatStatus(s.status, TASK_STATUS_LABELS),
                    }))}
                    dataKey="count"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    labelLine={{ stroke: "#94a3b8" }}
                  >
                    {data.tasks_by_status.map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: "#1e293b", border: "1px solid #475569", borderRadius: "8px" }}
                    formatter={(value: number, name: string) => [value, name]}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>

      {!hasConversionLine && !hasTasksCharts && !hasLeadsBar && (
        <p className="text-slate-400 text-sm">Complete tasks and leads to see charts here.</p>
      )}
    </div>
  );
}
