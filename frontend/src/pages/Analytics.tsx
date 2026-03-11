import { useCallback, useEffect, useState, useRef } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { LineChart as MuiLineChart } from "@mui/x-charts/LineChart";
import { PieChart as MuiPieChart } from "@mui/x-charts/PieChart";
import { BarChart as MuiBarChart } from "@mui/x-charts/BarChart";
import { getOverview } from "@/api/analytics";
import { getDashboard, type DashboardResponse } from "@/api/analytics";
import type { AnalyticsOverview } from "@/api/analytics";
import { listInvoices, type Invoice } from "@/api/finance";
import { listLeads, type Lead } from "@/api/leads";
import { useAuth } from "@/store/auth";

const TASK_PIE_COLORS = [
  "#0ea5e9",
  "#8b5cf6",
  "#10b981",
  "#f59e0b",
  "#ec4899",
  "#6366f1",
];
const CHART_COLORS = ["#3a7eb9", "#5791c4", "#347ab7", "#2d6a9a", "#8b5cf6", "#ec4899"];
// Easily differentiating hues (distinct, not chromatic)
const INVOICE_PIE_COLORS = ["#2563eb", "#059669", "#d97706", "#dc2626", "#7c3aed", "#0891b2"];
const LEADS_PIE_COLORS = ["#ea580c", "#16a34a", "#9333ea", "#0d9488", "#e11d48", "#ca8a04"];
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
const PROJECTS_BAR_COLOR = "#3a7eb9";

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

function groupByStatus(invoices: Invoice[]): { status: string; count: number }[] {
  const map = new Map<string, number>();
  for (const inv of invoices) {
    const s = inv.status || "unknown";
    map.set(s, (map.get(s) ?? 0) + 1);
  }
  return Array.from(map.entries()).map(([status, count]) => ({ status, count }));
}

function groupBySource(leads: Lead[]): { source: string; count: number }[] {
  const map = new Map<string, number>();
  for (const lead of leads) {
    const s = lead.source?.trim() || "Unknown";
    map.set(s, (map.get(s) ?? 0) + 1);
  }
  return Array.from(map.entries()).map(([source, count]) => ({ source, count }));
}

export default function AnalyticsPage() {
  const { hasPermission } = useAuth();
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [invoicesLoading, setInvoicesLoading] = useState(false);
  const [leadsLoading, setLeadsLoading] = useState(false);
  const conversionChartRef = useRef<HTMLDivElement>(null);
  const [conversionChartWidth, setConversionChartWidth] = useState(400);

  const loadReports = useCallback(() => {
    setLoading(true);
    Promise.all([getOverview(), getDashboard().catch(() => null)])
      .then(([ov, dash]) => {
        setOverview(ov);
        setDashboard(dash);
      })
      .catch(() => setOverview(null))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  useEffect(() => {
    const el = conversionChartRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (typeof w === "number" && w > 0) setConversionChartWidth(w);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    setInvoicesLoading(true);
    listInvoices({ limit: 100 })
      .then(setInvoices)
      .catch(() => setInvoices([]))
      .finally(() => setInvoicesLoading(false));
  }, []);

  useEffect(() => {
    setLeadsLoading(true);
    listLeads({ limit: 100 })
      .then(setLeads)
      .catch(() => setLeads([]))
      .finally(() => setLeadsLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[40vh] text-gray-500">
        Loading reports…
      </div>
    );
  }
  if (!overview) {
    return (
      <div className="rounded-xl bg-white border border-gray-100 p-6 shadow-sm text-red-600">
        Failed to load reports.
      </div>
    );
  }

  const revMonth = Number(overview.revenue_this_month ?? 0);
  const expMonth = Number(overview.expenses_this_month ?? 0);
  const profitMonth = revMonth - expMonth;
  const totalTasks =
    overview.tasks_todo + overview.tasks_in_progress + overview.tasks_done;
  const completionRate =
    totalTasks > 0 ? (overview.tasks_done / totalTasks) * 100 : 0;

  const invoiceByStatus = groupByStatus(invoices);
  const leadsBySource = groupBySource(leads);

  const hasConversionLine =
    dashboard && dashboard.conversion_over_time.length > 0;
  const hasLeadsByStatus =
    dashboard && dashboard.leads_by_status.length > 0;
  const hasProjectsByStage =
    dashboard && (dashboard.projects_by_stage ?? []).length > 0;
  const taskPieData =
    dashboard?.tasks_by_status.map((s, i) => ({
      id: i,
      value: s.count,
      label: formatStatus(s.status, TASK_STATUS_LABELS),
    })) ??
    [
      { id: 0, value: overview.tasks_todo, label: "To do" },
      { id: 1, value: overview.tasks_in_progress, label: "In progress" },
      { id: 2, value: overview.tasks_done, label: "Done" },
    ].filter((d) => d.value > 0);

  const overviewBarData = [
    { name: "Clients", count: overview.total_clients },
    { name: "Active projects", count: overview.active_projects },
    { name: "Total users", count: overview.total_users },
    { name: "Leads (this month)", count: dashboard?.leads_this_month ?? 0 },
    { name: "Invoices", count: invoices.length },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Reports
        </h1>
        <p className="text-gray-500 dark:text-gray-400 mt-1">
          Analytics and key metrics across clients, projects, tasks, and finance.
        </p>
      </div>

      {/* Executive summary KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
        <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-4 shadow-sm">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
            Revenue (paid)
          </p>
          <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">
            ${Number(overview.revenue_total ?? 0).toLocaleString()}
          </p>
        </div>
        <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-4 shadow-sm">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
            Outstanding
          </p>
          <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">
            ${Number(overview.outstanding_total ?? 0).toLocaleString()}
          </p>
        </div>
        <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-4 shadow-sm">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
            Active projects
          </p>
          <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">
            {overview.active_projects}
          </p>
        </div>
        <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-4 shadow-sm">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
            Tasks done
          </p>
          <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">
            {overview.tasks_done}
            {totalTasks > 0 && (
              <span className="text-sm font-normal text-gray-500 dark:text-gray-400 ml-1">
                ({completionRate.toFixed(0)}%)
              </span>
            )}
          </p>
        </div>
        <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-4 shadow-sm">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
            Total users
          </p>
          <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">
            {overview.total_users}
          </p>
        </div>
        <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-4 shadow-sm">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
            Profit (this month)
          </p>
          <p
            className={`text-xl font-bold mt-1 ${
              profitMonth >= 0
                ? "text-emerald-600 dark:text-emerald-400"
                : "text-red-600 dark:text-red-400"
            }`}
          >
            ${profitMonth.toLocaleString()}
          </p>
        </div>
      </div>

      {dashboard && (
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-4 shadow-sm">
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Conversion rate
            </p>
            <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">
              {dashboard.conversion_rate != null
                ? `${(dashboard.conversion_rate * 100).toFixed(1)}%`
                : "—"}
            </p>
          </div>
          <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-4 shadow-sm">
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Leads today
            </p>
            <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">
              {dashboard.leads_today}
            </p>
          </div>
          <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-4 shadow-sm">
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
              Leads this month
            </p>
            <p className="text-xl font-bold text-gray-900 dark:text-white mt-1">
              {dashboard.leads_this_month}
            </p>
          </div>
        </div>
      )}

      {/* First row: Overview counts (wider), Tasks by status, Leads by status - flex so no empty space when Leads hidden */}
      <div className="flex flex-col lg:flex-row gap-4 xl:h-[420px]">
        {/* Overview counts - MUI BarChart (flex-[2] = double width of each pie) */}
        <div className="min-w-0 flex-[2] min-h-[320px] xl:min-h-0 flex">
          <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-5 shadow-sm h-full flex flex-col min-h-0 w-full">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 shrink-0">
              Overview counts
            </h2>
            <Box sx={{ width: "100%", flex: 1, minHeight: 280 }}>
              <MuiBarChart
                height={280}
                xAxis={[
                  {
                    scaleType: "band",
                    data: overviewBarData.map((d) => d.name),
                  },
                ]}
                series={[
                  {
                    data: overviewBarData.map((d) => d.count),
                    label: "Count",
                    color: PROJECTS_BAR_COLOR,
                  },
                ]}
                colors={[PROJECTS_BAR_COLOR]}
                margin={{ top: 20, right: 20, left: 50, bottom: 70 }}
              />
            </Box>
          </div>
        </div>

        {/* Tasks by status - MUI Pie (donut) */}
        <div className="min-w-0 flex-1 h-full min-h-[320px] xl:min-h-0 flex">
          <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-5 shadow-sm h-full flex flex-col min-h-0 w-full">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 shrink-0">
              Tasks by status
            </h2>
            {taskPieData.length > 0 ? (
              <Box sx={{ display: "flex", justifyContent: "center", flex: 1, minHeight: 280 }}>
                <MuiPieChart
                  height={280}
                  width={280}
                series={[
                  {
                    data: taskPieData,
                    innerRadius: 50,
                    arcLabel: () => "",
                  },
                ]}
                colors={TASK_PIE_COLORS}
                margin={{ top: 10, right: 10, left: 10, bottom: 60 }}
                slotProps={{
                  legend: {
                    position: { vertical: "bottom", horizontal: "center" },
                  },
                }}
              />
            </Box>
          ) : (
            <p className="text-gray-500 dark:text-gray-400 py-8 text-center flex-1 flex items-center justify-center">
              No task data yet.
            </p>
          )}
          </div>
        </div>

        {/* Leads by status - MUI Pie */}
        {hasLeadsByStatus && dashboard && (
          <div className="min-w-0 flex-1 h-full min-h-[320px] xl:min-h-0 flex">
            <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-5 shadow-sm h-full flex flex-col min-h-0 w-full">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 shrink-0">
                Leads by status
              </h2>
              <Box sx={{ display: "flex", justifyContent: "center", flex: 1, minHeight: 280 }}>
                <MuiPieChart
                  height={280}
                  width={280}
                series={[
                  {
                    data: dashboard.leads_by_status.map((s, i) => ({
                      id: i,
                      value: s.count,
                      label: formatStatus(s.status, LEAD_STATUS_LABELS),
                    })),
                    innerRadius: 50,
                    arcLabel: () => "",
                  },
                ]}
                colors={CHART_COLORS}
                margin={{ top: 10, right: 10, left: 10, bottom: 60 }}
                slotProps={{
                  legend: {
                    position: { vertical: "bottom", horizontal: "center" },
                  },
                }}
              />
            </Box>
            </div>
          </div>
        )}
      </div>

      {/* Row: Projects by stage (half width) | Invoices by status + Leads by source (half width, stacked) */}
      <div className="flex flex-col lg:flex-row gap-4 min-h-[320px] xl:h-[420px]">
        {/* Left half: Projects by stage */}
        <div className="min-w-0 flex-1 flex">
          {hasProjectsByStage && dashboard ? (
            <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-5 shadow-sm h-full flex flex-col min-h-0 w-full">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 shrink-0">
                Projects by stage
              </h2>
              <Box sx={{ width: "100%", minWidth: 0, flex: 1, minHeight: 280 }}>
                <MuiBarChart
                  height={280}
                  xAxis={[
                    {
                      scaleType: "band",
                      data: PIPELINE_STAGES_ORDER.map(formatStage),
                      tickLabelStyle: { fontSize: 10 },
                      tickLabelInterval: () => true,
                    },
                  ]}
                  series={[
                    {
                      data: PIPELINE_STAGES_ORDER.map(
                        (stage) =>
                          (dashboard.projects_by_stage ?? []).find(
                            (s) => s.status === stage
                          )?.count ?? 0
                      ),
                      label: "Projects",
                      color: PROJECTS_BAR_COLOR,
                    },
                  ]}
                  colors={[PROJECTS_BAR_COLOR]}
                  margin={{ top: 20, right: 20, left: 40, bottom: 70 }}
                />
              </Box>
            </div>
          ) : null}
        </div>

        {/* Right half: Invoices by status + Leads by source in one row */}
        <div className="min-w-0 flex-1 flex flex-row gap-4">
          <div className="min-w-0 flex-1 min-h-[360px] flex">
            <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-5 shadow-sm h-full flex flex-col min-h-0 w-full">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 shrink-0">
                Invoices by status
              </h2>
              {invoicesLoading ? (
                <p className="text-gray-500 dark:text-gray-400 py-6 text-center">Loading…</p>
              ) : invoiceByStatus.length > 0 ? (
                <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1, minHeight: 320, width: "100%", "& .MuiChartsLegend-root": { flexWrap: "nowrap", justifyContent: "center" } }}>
                  <MuiPieChart
                    height={280}
                    width={280}
                    series={[
                      {
                        data: invoiceByStatus.map((s, i) => ({
                          id: i,
                          value: s.count,
                          label: formatStage(s.status),
                        })),
                        innerRadius: 56,
                        arcLabel: () => "",
                      },
                    ]}
                    colors={INVOICE_PIE_COLORS}
                    margin={{ top: 0, right: 0, left: 0, bottom: 64 }}
                    slotProps={{
                      legend: {
                        direction: "row",
                        position: { vertical: "bottom", horizontal: "middle" },
                        padding: 8,
                        itemGap: 16,
                        sx: { flexWrap: "nowrap", justifyContent: "center" },
                      },
                    }}
                  />
                </Box>
              ) : (
                <p className="text-gray-500 dark:text-gray-400 py-6 text-center flex-1 flex items-center justify-center text-sm">
                  No invoices to report.
                </p>
              )}
            </div>
          </div>
          <div className="min-w-0 flex-1 min-h-[360px] flex">
            <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-5 shadow-sm h-full flex flex-col min-h-0 w-full">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4 shrink-0">
                Leads by source
              </h2>
              {leadsLoading ? (
                <p className="text-gray-500 dark:text-gray-400 py-6 text-center">Loading…</p>
              ) : leadsBySource.length > 0 ? (
                <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1, minHeight: 320, width: "100%", "& .MuiChartsLegend-root": { flexWrap: "nowrap", justifyContent: "center" } }}>
                  <MuiPieChart
                    height={280}
                    width={280}
                    series={[
                      {
                        data: leadsBySource.map((s, i) => ({
                          id: i,
                          value: s.count,
                          label: s.source,
                        })),
                        innerRadius: 56,
                        arcLabel: () => "",
                      },
                    ]}
                    colors={LEADS_PIE_COLORS}
                    margin={{ top: 0, right: 0, left: 0, bottom: 64 }}
                    slotProps={{
                      legend: {
                        direction: "row",
                        position: { vertical: "bottom", horizontal: "middle" },
                        padding: 8,
                        itemGap: 16,
                        sx: { flexWrap: "nowrap", justifyContent: "center" },
                      },
                    }}
                  />
                </Box>
              ) : (
                <p className="text-gray-500 dark:text-gray-400 py-6 text-center flex-1 flex items-center justify-center text-sm">
                  No leads to report.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Conversion over time - MUI LineChart */}
      {hasConversionLine && dashboard && (
        <div className="min-h-[320px] xl:h-[420px] flex">
          <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 p-5 shadow-sm h-full flex flex-col min-h-0 w-full">
            <Typography component="h2" className="text-lg font-semibold text-gray-900 dark:text-white mb-4 shrink-0">
              Leads converted over time
            </Typography>
            <Box sx={{ width: "100%", flex: 1, minHeight: 280 }} ref={conversionChartRef}>
              <MuiLineChart
                height={280}
                width={conversionChartWidth}
                series={[
                  {
                    data: dashboard.conversion_over_time.map((d) => d.converted_count),
                    label: "Converted",
                    color: "#3a7eb9",
                  },
                ]}
                xAxis={[
                  {
                    scaleType: "point",
                    data: dashboard.conversion_over_time.map((d) => d.month),
                  },
                ]}
                margin={{ top: 20, right: 20, left: 50, bottom: 50 }}
                grid={{ vertical: false, horizontal: true }}
              />
            </Box>
          </div>
        </div>
      )}
    </div>
  );
}
