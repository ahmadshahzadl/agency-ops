import { apiFetch } from "./client";

export interface Task {
  id: string;
  project_id: string | null;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  assignee_id: string | null;
  due_date: string | null;
  order_index: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export async function listTasks(params?: {
  skip?: number;
  limit?: number;
  project_id?: string;
  assignee_id?: string;
  status_filter?: string;
}): Promise<Task[]> {
  const sp = new URLSearchParams();
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  if (params?.project_id) sp.set("project_id", params.project_id);
  if (params?.assignee_id) sp.set("assignee_id", params.assignee_id);
  if (params?.status_filter) sp.set("status_filter", params.status_filter);
  const qs = sp.toString();
  return apiFetch<Task[]>(`/api/v1/tasks${qs ? `?${qs}` : ""}`);
}

export async function createTask(data: Omit<Task, "id" | "created_at" | "updated_at" | "created_by">): Promise<Task> {
  return apiFetch<Task>("/api/v1/tasks", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateTask(id: string, data: Partial<Task>): Promise<Task> {
  return apiFetch<Task>(`/api/v1/tasks/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteTask(id: string): Promise<void> {
  return apiFetch(`/api/v1/tasks/${id}`, { method: "DELETE" });
}
