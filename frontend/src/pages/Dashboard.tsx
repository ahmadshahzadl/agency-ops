import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import Box from "@mui/material/Box";
import { PieChart as MuiPieChart } from "@mui/x-charts/PieChart";
import { BarChart as MuiBarChart } from "@mui/x-charts/BarChart";
import { getDashboard, type DashboardResponse } from "@/api/analytics";
import {
  listInvoices,
  listExpenses,
  type Invoice,
  type Expense,
} from "@/api/finance";
import {
  listTeamActivity,
  listMyReports,
  type ActivityLogWithUser,
  type ReportSummary,
} from "@/api/team_activity";
import { useAuth } from "@/store/auth";


const TASK_PIE_COLORS = [
  "#0ea5e9",
  "#8b5cf6",
  "#10b981",
  "#f59e0b",
  "#ec4899",
  "#6366f1",
];
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

function formatStage(stage: string) {
  return stage.charAt(0).toUpperCase() + stage.slice(1).replace(/_/g, " ");
}

const PIPELINE_STAGES_ORDER = [
  "lead",
  "discovery",
  "proposal",
  "scoping",
  "design",
  "development",
  "qa",
  "deployment",
  "handover",
  "support",
];
const PROJECTS_BAR_COLOR = "#3a7eb9";

type FinanceTab = "invoices" | "expenses";
type LeadsPeriod = "today" | "this_week" | "this_month";

type MetricCard = { label: string; value: string | number; to: string; highlight: boolean };

export default function Dashboard() {
  const { user, hasPermission } = useAuth();
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [financeTab, setFinanceTab] = useState<FinanceTab>("invoices");
  const [leadsPeriod, setLeadsPeriod] = useState<LeadsPeriod>("this_month");
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [financeLoading, setFinanceLoading] = useState(false);
  const [activities, setActivities] = useState<ActivityLogWithUser[]>([]);
  const [activitiesLoading, setActivitiesLoading] = useState(false);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const isAdminOrManager =
    hasPermission("admin:all") || user?.roles?.includes("manager");
  const canReadActivity = hasPermission("team_activity:read");

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!isAdminOrManager) return;
    setFinanceLoading(true);
    Promise.all([listInvoices({ limit: 8 }), listExpenses({ limit: 8 })])
      .then(([inv, exp]) => {
        setInvoices(inv);
        setExpenses(exp);
      })
      .catch(() => {})
      .finally(() => setFinanceLoading(false));
  }, [isAdminOrManager]);

  const fetchActivities = useCallback(() => {
    if (!canReadActivity) return;
    setActivitiesLoading(true);
    Promise.all([listTeamActivity({ limit: 10 }), listMyReports()])
      .then(([activityList, reportsList]) => {
        setActivities(activityList);
        setReports(reportsList);
      })
      .catch(() => {
        setActivities([]);
        setReports([]);
      })
      .finally(() => setActivitiesLoading(false));
  }, [canReadActivity]);

  useEffect(() => {
    fetchActivities();
  }, [fetchActivities]);

  useEffect(() => {
    if (!canReadActivity) return;
    const onActivityUpdated = () => fetchActivities();
    window.addEventListener("ws:activity_updated", onActivityUpdated);
    return () => window.removeEventListener("ws:activity_updated", onActivityUpdated);
  }, [canReadActivity, fetchActivities]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh] text-steel-blue">
        Loading...
      </div>
    );
  }
  if (!data) {
    return (
      <div className="rounded-xl bg-white p-6 shadow-sm text-red-600">
        Failed to load dashboard.
      </div>
    );
  }

  const isMemberView =
    data.total_clients === 0 &&
    data.active_projects === 0 &&
    (data.revenue_total == null || Number(data.revenue_total) === 0);

  const metricCards: MetricCard[] = [
    ...(data.total_clients > 0 || !isMemberView
      ? [
          {
            label: "Clients",
            value: data.total_clients,
            to: "/clients" as const,
            highlight: true,
          },
        ]
      : []),
    ...(data.active_projects > 0 || !isMemberView
      ? [
          {
            label: "Active projects",
            value: data.active_projects,
            to: "/projects" as const,
            highlight: true,
          },
        ]
      : []),
    {
      label: "Total users",
      value: data.total_users,
      to: "/users" as const,
      highlight: false,
    },
    {
      label: "Expenses (this month)",
      value: data.expenses_this_month != null ? `$${Number(data.expenses_this_month).toLocaleString()}` : "—",
      to: "/expenses" as const,
      highlight: false,
    },
    {
      label: "Revenue (this month)",
      value: data.revenue_this_month != null ? `$${Number(data.revenue_this_month).toLocaleString()}` : "—",
      to: "/invoices" as const,
      highlight: false,
    },
    ...(data.revenue_total != null && Number(data.revenue_total) > 0
      ? [
          {
            label: "Revenue",
            value: `$${Number(data.revenue_total).toLocaleString()}`,
            to: "/invoices" as const,
            highlight: true,
          },
        ]
      : []),
    ...(data.outstanding_total != null && Number(data.outstanding_total) > 0
      ? [
          {
            label: "Outstanding",
            value: `$${Number(data.outstanding_total).toLocaleString()}`,
            to: "/invoices" as const,
            highlight: false,
          },
        ]
      : []),
  ];

  if (data.conversion_rate != null && isMemberView) {
    metricCards.push({
      label: "Conversion rate",
      value: `${(data.conversion_rate * 100).toFixed(1)}%`,
      to: "/leads",
      highlight: true,
    });
  }

  const hasConversionLine = data.conversion_over_time.length > 0;
  const hasTasksCharts = data.tasks_by_status.some((s) => s.count > 0);
  const hasLeadsBar = data.leads_by_status.length > 0;
  const hasProjectsByStage = isAdminOrManager;

  return (
    <div className="space-y-6">
      {/* Key metrics - Clients #5791c4, Active projects #347ab7, rest white. Leads card (admin) before Expenses this month. */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {metricCards.slice(0, 3).map((c) => {
          const isClients = c.label === "Clients";
          const isActiveProjects = c.label === "Active projects";
          const isBlueCard = isClients || isActiveProjects;
          const bgStyle = isClients
            ? { backgroundColor: "#5791c4" }
            : isActiveProjects
              ? { backgroundColor: "#347ab7" }
              : undefined;
          return (
            <Link
              key={c.label}
              to={c.to}
              className={`rounded-xl min-h-[140px] flex flex-col items-start justify-start pt-4 pl-4 pr-7 pb-7 shadow-sm transition-shadow hover:shadow-md ${
                isBlueCard
                  ? "text-white"
                  : "bg-white text-gray-900 border border-gray-100"
              }`}
              style={bgStyle}
            >
              <p
                className={`text-base font-semibold ${isBlueCard ? "text-white/90" : "text-gray-500"}`}
              >
                {c.label}
              </p>
              <p
                className={`text-4xl font-bold mt-3 ${isBlueCard ? "text-white" : "text-gray-900"}`}
              >
                {c.value}
              </p>
            </Link>
          );
        })}
        {isAdminOrManager ? (
          <div className="rounded-xl min-h-[140px] flex flex-col items-start justify-start pt-4 pl-4 pr-4 pb-7 bg-white border border-gray-100 shadow-sm">
            <div className="flex justify-between items-start w-full gap-2 pr-2">
              <p className="text-base font-semibold text-gray-500 shrink-0">Leads</p>
              <div
                className="flex items-center gap-2 flex-wrap justify-end"
                onClick={(e) => e.stopPropagation()}
                role="group"
                aria-label="Leads period"
              >
                {(["today", "this_week", "this_month"] as const).map((p) => (
                  <label
                    key={p}
                    className="flex items-center gap-1 text-xs text-gray-600 cursor-pointer whitespace-nowrap"
                  >
                    <input
                      type="radio"
                      name="leadsPeriod"
                      checked={leadsPeriod === p}
                      onChange={() => setLeadsPeriod(p)}
                      className="rounded-full border-gray-300"
                    />
                    <span>{p === "today" ? "Today" : p === "this_week" ? "This week" : "This month"}</span>
                  </label>
                ))}
              </div>
            </div>
            <Link to="/leads" className="mt-3 block">
              <p className="text-4xl font-bold text-gray-900">
                {leadsPeriod === "today"
                  ? data.leads_today
                  : leadsPeriod === "this_week"
                    ? data.leads_this_week
                    : data.leads_this_month}
              </p>
            </Link>
          </div>
        ) : (
          metricCards.slice(3, 4).map((c) => (
            <Link
              key={c.label}
              to={c.to}
              className="rounded-xl min-h-[140px] flex flex-col items-start justify-start pt-4 pl-4 pr-7 pb-7 bg-white border border-gray-100 shadow-sm hover:shadow-md transition-shadow"
            >
              <p className="text-base font-semibold text-gray-500">{c.label}</p>
              <p className="text-4xl font-bold mt-3 text-gray-900">{c.value}</p>
            </Link>
          ))
        )}
      </div>

      {/* Extra metrics row */}
      {(metricCards.length > 4 || isAdminOrManager) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {(isAdminOrManager ? metricCards.slice(3) : metricCards.slice(4)).map((c) => (
            <Link
              key={c.label}
              to={c.to}
              className="rounded-xl min-h-[140px] flex flex-col items-start justify-start pt-4 pl-4 pr-7 pb-7 bg-white border border-gray-100 shadow-sm hover:shadow-md transition-shadow"
            >
              <p className="text-base font-semibold text-gray-500">{c.label}</p>
              <p className="text-4xl font-bold mt-3 text-gray-900">{c.value}</p>
            </Link>
          ))}
        </div>
      )}

      {/* Charts row - white cards */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {hasConversionLine && (
          <div className="rounded-xl bg-white border border-gray-100 p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Leads converted over time
            </h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={data.conversion_over_time}
                  margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="month" stroke="#6b7280" fontSize={12} />
                  <YAxis stroke="#6b7280" fontSize={12} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      background: "#fff",
                      border: "1px solid #e5e7eb",
                      borderRadius: "8px",
                      boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                    }}
                    formatter={(value: number) => [value, "Converted"]}
                    labelFormatter={(label) => `Month: ${label}`}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="converted_count"
                    name="Converted"
                    stroke="#347ab7"
                    strokeWidth={2}
                    dot={{ fill: "#347ab7" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {!hasProjectsByStage && hasTasksCharts ? (
          <div className="rounded-xl bg-white border border-gray-100 p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Tasks by status
            </h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data.tasks_by_status.map((s) => ({
                    ...s,
                    name: formatStatus(s.status, TASK_STATUS_LABELS),
                  }))}
                  margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="name" stroke="#6b7280" fontSize={12} />
                  <YAxis stroke="#6b7280" fontSize={12} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      background: "#fff",
                      border: "1px solid #e5e7eb",
                      borderRadius: "8px",
                      boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                    }}
                    formatter={(value: number) => [value, "Tasks"]}
                  />
                  <Bar
                    dataKey="count"
                    name="Tasks"
                    fill="#347ab7"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        ) : null}

        {hasLeadsBar && (
          <div className="rounded-xl bg-white border border-gray-100 p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Leads by status
            </h2>
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
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    type="number"
                    stroke="#6b7280"
                    fontSize={12}
                    allowDecimals={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    stroke="#6b7280"
                    fontSize={12}
                    width={90}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#fff",
                      border: "1px solid #e5e7eb",
                      borderRadius: "8px",
                      boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
                    }}
                    formatter={(value: number) => [value, "Leads"]}
                  />
                  <Bar
                    dataKey="count"
                    name="Leads"
                    fill="#5791c4"
                    radius={[0, 4, 4, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>

      {/* Projects by stage (2 cols) : Task distribution (1) : Finances (1) - same grid as metric cards */}
      {(hasProjectsByStage || hasTasksCharts || isAdminOrManager) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 xl:h-[420px]">
          <div className="min-w-0 h-full min-h-[320px] xl:min-h-0 lg:col-span-2">
            {hasProjectsByStage &&
              (() => {
                const stageCountMap = Object.fromEntries(
                  (data.projects_by_stage ?? []).map((s) => [
                    s.status,
                    s.count,
                  ]),
                );
                const xAxisData = PIPELINE_STAGES_ORDER.map(formatStage);
                const seriesData = PIPELINE_STAGES_ORDER.map(
                  (stage) => stageCountMap[stage] ?? 0,
                );
                return (
                  <div className="rounded-xl bg-white border border-gray-100 p-5 shadow-sm h-full flex flex-col min-h-0">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4 shrink-0">
                      Projects by stage
                    </h2>
                    <Box sx={{ width: "100%", minWidth: 0 }}>
                      <MuiBarChart
                        height={280}
                        xAxis={[
                          {
                            scaleType: "band",
                            data: xAxisData,
                            tickLabelStyle: {
                              fill: "#000",
                              color: "#000",
                              fontSize: 12,
                            },
                            tickLabelInterval: () => true,
                            tickLabelMinGap: 0,
                            colorMap: {
                              type: "ordinal",
                              values: xAxisData,
                              colors: xAxisData.map(() => PROJECTS_BAR_COLOR),
                            },
                          },
                        ]}
                        yAxis={[
                          {
                            valueFormatter: (value: number) =>
                              Number.isInteger(value) ? String(value) : "",
                          },
                        ]}
                        series={[
                          {
                            label: "Projects",
                            data: seriesData,
                            color: PROJECTS_BAR_COLOR,
                          },
                        ]}
                        colors={[PROJECTS_BAR_COLOR]}
                        margin={{ top: 20, right: 20, left: 40, bottom: 70 }}
                        slotProps={{}}
                      />
                    </Box>
                  </div>
                );
              })()}
          </div>

          <div className="min-w-0 h-full min-h-[320px] xl:min-h-0 lg:col-span-1">
            {hasTasksCharts &&
              (() => {
                const taskPieData = data.tasks_by_status.map((s, i) => ({
                  id: i,
                  value: s.count,
                  label: formatStatus(s.status, TASK_STATUS_LABELS),
                }));
                return (
                  <div className="rounded-xl bg-white border border-gray-100 p-5 shadow-sm h-full flex flex-col min-h-0">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4 shrink-0">
                      Task distribution
                    </h2>
                    <Box
                      sx={{
                        width: "100%",
                        display: "flex",
                        flexDirection: "column",
                        alignItems: "center",
                      }}
                    >
                      <MuiPieChart
                        height={280}
                        width={280}
                        series={[
                          {
                            data: taskPieData,
                            innerRadius: 55,
                            arcLabel: () => "",
                          },
                        ]}
                        colors={TASK_PIE_COLORS}
                        margin={{ top: 10, right: 10, left: 10, bottom: 60 }}
                        slotProps={{
                          legend: {
                            position: { vertical: "bottom", horizontal: "center" },
                            direction: "row" as never,
                            padding: 8,
                          } as any,
                        }}
                      />
                    </Box>
                  </div>
                );
              })()}
          </div>

          <div className="min-w-0 h-full min-h-[320px] xl:min-h-0 lg:col-span-1">
            {isAdminOrManager && (
              <div className="rounded-xl bg-white border border-gray-100 p-5 shadow-sm h-full flex flex-col min-h-0 overflow-hidden">
                <h2 className="text-lg font-semibold text-gray-900 mb-3 shrink-0">
                  Finances
                </h2>
                <div className="relative flex rounded-lg border border-gray-200 p-0.5 mb-4 bg-gray-100 shrink-0">
                  <div
                    className="absolute top-0.5 bottom-0.5 w-[calc(50%-2px)] rounded-md transition-all duration-300 ease-out"
                    style={{
                      left:
                        financeTab === "invoices" ? "2px" : "calc(50% + 2px)",
                      backgroundColor: "#5791c4",
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setFinanceTab("invoices")}
                    className={`relative z-10 flex-1 py-2 text-sm font-medium rounded-md transition-colors duration-300 ${
                      financeTab === "invoices"
                        ? "text-white"
                        : "text-gray-600 hover:text-gray-900"
                    }`}
                  >
                    Invoices
                  </button>
                  <button
                    type="button"
                    onClick={() => setFinanceTab("expenses")}
                    className={`relative z-10 flex-1 py-2 text-sm font-medium rounded-md transition-colors duration-300 ${
                      financeTab === "expenses"
                        ? "text-white"
                        : "text-gray-600 hover:text-gray-900"
                    }`}
                  >
                    Expenses
                  </button>
                </div>
                <div className="flex-1 flex flex-col min-h-0">
                  <div className="flex-1 flex flex-col min-h-[200px]">
                    {financeLoading ? (
                      <p className="text-gray-500 text-sm py-4">Loading…</p>
                    ) : financeTab === "invoices" ? (
                      invoices.length === 0 ? (
                        <p className="text-gray-500 text-sm py-2">
                          No invoices.
                        </p>
                      ) : (
                        <ul className="space-y-1 min-h-[200px] overflow-auto flex-1">
                          {invoices.map((inv) => (
                            <li key={inv.id}>
                              <Link
                                to="/invoices"
                                className="flex items-center justify-between gap-2 py-2.5 px-3 rounded-lg hover:bg-gray-50 border border-transparent hover:border-gray-100 transition-colors group"
                              >
                                <span className="text-sm font-medium text-gray-900 truncate group-hover:text-[#347ab7]">
                                  {inv.number}
                                </span>
                                <span className="text-sm text-gray-500 shrink-0">
                                  {inv.currency}{" "}
                                  {Number(inv.amount).toLocaleString()}
                                </span>
                              </Link>
                            </li>
                          ))}
                        </ul>
                      )
                    ) : expenses.length === 0 ? (
                      <p className="text-gray-500 text-sm py-2">No expenses.</p>
                    ) : (
                      <ul className="space-y-1 min-h-[200px] overflow-auto flex-1">
                        {expenses.map((exp) => (
                          <li key={exp.id}>
                            <Link
                              to="/expenses"
                              className="flex items-center justify-between gap-2 py-2.5 px-3 rounded-lg hover:bg-gray-50 border border-transparent hover:border-gray-100 transition-colors group"
                            >
                              <span className="text-sm font-medium text-gray-900 truncate group-hover:text-[#347ab7]">
                                {exp.description || "Expense"}
                              </span>
                              <span className="text-sm text-gray-500 shrink-0">
                                {exp.currency}{" "}
                                {Number(exp.amount).toLocaleString()}
                              </span>
                            </Link>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                  <div className="mt-auto pt-3 shrink-0 border-t border-gray-100">
                    {!financeLoading && (
                      <Link
                        to={
                          financeTab === "invoices" ? "/invoices" : "/expenses"
                        }
                        className="text-sm font-medium text-[#347ab7] hover:underline"
                      >
                        {financeTab === "invoices"
                          ? "View all invoices"
                          : "View all expenses"}
                      </Link>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Team members (direct reports) for managers */}
      {canReadActivity && reports.length > 0 ? (
        <div className="rounded-xl bg-white border border-gray-100 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold text-gray-900">
              Your team members
            </h2>
            <Link
              to="/team-activity"
              className="text-sm font-medium text-[#347ab7] hover:underline"
            >
              View activity
            </Link>
          </div>
          <p className="text-sm text-gray-600 mb-3">
            Employees and members who report to you.
          </p>
          <ul className="flex flex-wrap gap-2">
            {reports.map((r) => (
              <li
                key={r.id}
                className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-50 border border-gray-100"
              >
                <span className="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center text-primary font-semibold text-xs">
                  {(r.full_name || r.email || "?").charAt(0).toUpperCase()}
                </span>
                <span className="font-medium text-gray-900 text-sm">{r.full_name || r.email}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* Last 10 team activities (real-time) or Quick links */}
      {canReadActivity ? (
        <div className="rounded-xl bg-white border border-gray-100 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Team activity
            </h2>
            <Link
              to="/team-activity"
              className="text-sm font-medium text-[#347ab7] hover:underline"
            >
              View all
            </Link>
          </div>
          {activitiesLoading ? (
            <p className="text-gray-500 text-sm py-2">Loading…</p>
          ) : activities.length === 0 ? (
            <p className="text-gray-500 text-sm py-2">No recent activity.</p>
          ) : (
            <ul className="space-y-1">
              {activities.map((log) => (
                <li
                  key={log.id}
                  className="flex items-start gap-2 py-2.5 px-3 rounded-lg border border-transparent hover:bg-gray-50 hover:border-gray-100 transition-colors"
                >
                  <span className="text-sm text-gray-500 shrink-0">
                    {new Date(log.created_at).toLocaleString(undefined, {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                  <span className="text-sm text-gray-900 flex-1 min-w-0">
                    <span className="font-medium text-gray-700">
                      {log.user_full_name || log.user_email || "Someone"}
                    </span>{" "}
                    {log.details || `${log.action} (${log.entity_type})`}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <div className="rounded-xl bg-white border border-gray-100 p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Quick links
          </h2>
          <div className="flex flex-wrap gap-3">
            <Link
              to="/tasks"
              className="px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors hover:opacity-90"
              style={{ backgroundColor: "#5791c4" }}
            >
              View all tasks
            </Link>
            <Link
              to="/leads"
              className="px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors hover:opacity-90"
              style={{ backgroundColor: "#347ab7" }}
            >
              View leads
            </Link>
            <Link
              to="/projects"
              className="px-4 py-2 rounded-lg border border-gray-200 text-gray-700 text-sm font-medium hover:bg-gray-50 transition-colors"
            >
              View projects
            </Link>
          </div>
        </div>
      )}

      {!hasConversionLine && !hasTasksCharts && !hasLeadsBar && (
        <p className="text-gray-500 text-sm">
          Complete tasks and leads to see charts here.
        </p>
      )}
    </div>
  );
}
