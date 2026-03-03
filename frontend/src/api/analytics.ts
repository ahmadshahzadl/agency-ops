import { apiFetch } from "./client";

export interface AnalyticsOverview {
  total_clients: number;
  active_projects: number;
  total_users: number;
  tasks_todo: number;
  tasks_in_progress: number;
  tasks_done: number;
  revenue_total: number | null;
  outstanding_total: number | null;
  revenue_this_month: number | null;
  expenses_this_month: number | null;
}

export interface ConversionOverTimePoint {
  month: string;
  converted_count: number;
}

export interface StatusCount {
  status: string;
  count: number;
}

export interface DashboardResponse extends AnalyticsOverview {
  leads_today: number;
  leads_this_week: number;
  leads_this_month: number;
  conversion_rate: number | null;
  conversion_over_time: ConversionOverTimePoint[];
  leads_by_status: StatusCount[];
  tasks_by_status: StatusCount[];
  projects_by_stage?: StatusCount[];
}

export async function getOverview(): Promise<AnalyticsOverview> {
  return apiFetch<AnalyticsOverview>("/api/v1/analytics/overview");
}

export async function getDashboard(): Promise<DashboardResponse> {
  return apiFetch<DashboardResponse>("/api/v1/analytics/dashboard");
}
