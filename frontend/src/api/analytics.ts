import { apiFetch } from "./client";

export interface AnalyticsOverview {
  total_clients: number;
  active_projects: number;
  tasks_todo: number;
  tasks_in_progress: number;
  tasks_done: number;
  revenue_total: number | null;
  outstanding_total: number | null;
}

export async function getOverview(): Promise<AnalyticsOverview> {
  return apiFetch<AnalyticsOverview>("/api/v1/analytics/overview");
}
