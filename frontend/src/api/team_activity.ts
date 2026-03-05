import { apiFetch } from "./client";

export interface ReportSummary {
  id: string;
  email: string;
  full_name: string | null;
}

export interface ActivityLogWithUser {
  id: string;
  user_id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details: string | null;
  created_at: string;
  user_email: string;
  user_full_name: string | null;
}

export async function listMyReports(): Promise<ReportSummary[]> {
  return apiFetch<ReportSummary[]>("/api/v1/team-activity/my-reports");
}

export async function listTeamActivity(params?: {
  report_id?: string;
  action?: string;
  entity_type?: string;
  skip?: number;
  limit?: number;
}): Promise<ActivityLogWithUser[]> {
  const sp = new URLSearchParams();
  if (params?.report_id) sp.set("report_id", params.report_id);
  if (params?.action) sp.set("action", params.action);
  if (params?.entity_type) sp.set("entity_type", params.entity_type);
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return apiFetch<ActivityLogWithUser[]>(`/api/v1/team-activity/activity${qs ? `?${qs}` : ""}`);
}
