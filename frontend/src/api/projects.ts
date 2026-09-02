import { apiFetch } from "./client";

export interface Project {
  id: string;
  client_id: string;
  name: string;
  description: string | null;
  status: string;
  pipeline_stage: string | null;
  assigned_team_id: string | null;
  start_date: string | null;
  end_date: string | null;
  hourly_rate: number | string | null;
  owner_id: string | null;
  created_at: string;
  updated_at: string;
  client_name?: string | null;
  task_count?: number | null;
  task_done_count?: number | null;
}

export async function listProjects(params?: {
  skip?: number;
  limit?: number;
  client_id?: string;
  status_filter?: string;
}): Promise<Project[]> {
  const sp = new URLSearchParams();
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  if (params?.client_id) sp.set("client_id", params.client_id);
  if (params?.status_filter) sp.set("status_filter", params.status_filter);
  const qs = sp.toString();
  return apiFetch<Project[]>(`/api/v1/projects${qs ? `?${qs}` : ""}`);
}

/** Project id and name only; allowed for all authenticated users (for display in meetings/tasks). */
export async function listProjectNames(params?: { skip?: number; limit?: number }): Promise<{ id: string; name: string }[]> {
  const sp = new URLSearchParams();
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return apiFetch<{ id: string; name: string }[]>(`/api/v1/projects/names${qs ? `?${qs}` : ""}`);
}

export async function getProject(id: string): Promise<Project> {
  return apiFetch<Project>(`/api/v1/projects/${id}`);
}

export async function createProject(data: Omit<Project, "id" | "created_at" | "updated_at">): Promise<Project> {
  return apiFetch<Project>("/api/v1/projects", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateProject(id: string, data: Partial<Project>): Promise<Project> {
  return apiFetch<Project>(`/api/v1/projects/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteProject(id: string): Promise<void> {
  return apiFetch(`/api/v1/projects/${id}`, { method: "DELETE" });
}
