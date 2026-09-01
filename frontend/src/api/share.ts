import { apiFetch } from "./client";

export interface ShareLink {
  id: string;
  project_id: string;
  token: string;
  label: string | null;
  created_at: string | null;
}

export interface PublicStatus {
  project_name: string;
  project_status: string;
  start_date: string | null;
  end_date: string | null;
  total_tasks: number;
  counts: Record<string, number>;
  percent_done: number;
  tasks: { title: string; status: string; item_type: string; due_date: string | null }[];
  generated_at: string;
}

export async function createShareLink(projectId: string, label?: string): Promise<ShareLink> {
  return apiFetch<ShareLink>(`/api/v1/projects/${projectId}/share-links`, {
    method: "POST",
    body: JSON.stringify({ label: label || null }),
  });
}

export async function listShareLinks(projectId: string): Promise<ShareLink[]> {
  return apiFetch<ShareLink[]>(`/api/v1/projects/${projectId}/share-links`);
}

export async function revokeShareLink(id: string): Promise<void> {
  return apiFetch(`/api/v1/share-links/${id}`, { method: "DELETE" });
}

export async function getPublicStatus(token: string): Promise<PublicStatus> {
  return apiFetch<PublicStatus>(`/api/v1/public/status/${encodeURIComponent(token)}`);
}

export function shareUrlFor(token: string): string {
  return `${window.location.origin}/status/${token}`;
}
