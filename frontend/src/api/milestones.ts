import { apiFetch } from "./client";

export interface Milestone {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  due_date: string | null;
  position: number;
  completed_at: string | null;
  state: "upcoming" | "overdue" | "completed";
  task_total: number;
  task_done: number;
  created_at: string | null;
}

export async function listMilestones(projectId: string): Promise<Milestone[]> {
  return apiFetch<Milestone[]>(`/api/v1/projects/${projectId}/milestones`);
}

export async function createMilestone(projectId: string, data: { name: string; due_date?: string | null; description?: string | null }): Promise<Milestone> {
  return apiFetch<Milestone>(`/api/v1/projects/${projectId}/milestones`, { method: "POST", body: JSON.stringify(data) });
}

export async function updateMilestone(id: string, data: { name?: string; due_date?: string | null; description?: string | null; position?: number }): Promise<Milestone> {
  return apiFetch<Milestone>(`/api/v1/milestones/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function completeMilestone(id: string): Promise<Milestone> {
  return apiFetch<Milestone>(`/api/v1/milestones/${id}/complete`, { method: "POST" });
}

export async function reopenMilestone(id: string): Promise<Milestone> {
  return apiFetch<Milestone>(`/api/v1/milestones/${id}/reopen`, { method: "POST" });
}

export async function deleteMilestone(id: string): Promise<void> {
  return apiFetch(`/api/v1/milestones/${id}`, { method: "DELETE" });
}
