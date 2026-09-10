import { apiFetch } from "./client";

export interface Credential {
  id: string;
  project_id: string;
  project_name: string | null;
  label: string;
  username: string | null;
  url: string | null;
  notes: string | null;
  created_by: string | null;
  created_at: string | null;
}

export interface CredentialPayload {
  project_id: string;
  label: string;
  secret: string;
  username?: string | null;
  url?: string | null;
  notes?: string | null;
}

export async function listCredentials(projectId: string): Promise<Credential[]> {
  return apiFetch<Credential[]>(`/api/v1/credentials?project_id=${projectId}`);
}

export async function createCredential(data: CredentialPayload): Promise<Credential> {
  return apiFetch<Credential>("/api/v1/credentials", { method: "POST", body: JSON.stringify(data) });
}

export async function updateCredential(id: string, data: Partial<Omit<CredentialPayload, "project_id">>): Promise<Credential> {
  return apiFetch<Credential>(`/api/v1/credentials/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deleteCredential(id: string): Promise<void> {
  return apiFetch(`/api/v1/credentials/${id}`, { method: "DELETE" });
}

export async function revealCredential(id: string): Promise<{ id: string; secret: string }> {
  return apiFetch<{ id: string; secret: string }>(`/api/v1/credentials/${id}/reveal`, { method: "POST" });
}
