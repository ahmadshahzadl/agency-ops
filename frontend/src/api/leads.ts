import { apiFetch } from "./client";

export interface Lead {
  id: string;
  company_name: string;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  source: string | null;
  status: string;
  notes: string | null;
  assigned_team_id: string | null;
  assigned_to: string | null;
  assigned_to_name?: string | null;
  created_by: string | null;
  created_by_name?: string | null;
  converted_to_client_id: string | null;
  converted_at: string | null;
  created_at: string;
  updated_at: string;
}

export async function listLeads(params?: {
  skip?: number;
  limit?: number;
  q?: string;
  status?: string;
}): Promise<Lead[]> {
  const sp = new URLSearchParams();
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  if (params?.q) sp.set("q", params.q);
  if (params?.status) sp.set("status", params.status);
  const qs = sp.toString();
  return apiFetch<Lead[]>(`/api/v1/leads${qs ? `?${qs}` : ""}`);
}

export async function createLead(data: {
  company_name: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  source?: string;
  status?: string;
  notes?: string;
  assigned_team_id?: string;
  assigned_to?: string;
}): Promise<Lead> {
  return apiFetch<Lead>("/api/v1/leads", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateLead(
  id: string,
  data: Partial<{
    company_name: string;
    contact_name: string;
    contact_email: string;
    contact_phone: string;
    source: string;
    status: string;
    notes: string;
    assigned_team_id: string | null;
    assigned_to: string | null;
  }>
): Promise<Lead> {
  return apiFetch<Lead>(`/api/v1/leads/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function convertLead(
  id: string,
  data: {
    client_team_id?: string;
    create_project?: boolean;
    project_name?: string;
    project_pipeline_stage?: string;
    project_assigned_team_id?: string;
  }
): Promise<{ message: string; client_id: string; project_id: string | null }> {
  return apiFetch(`/api/v1/leads/${id}/convert`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteLead(id: string): Promise<void> {
  return apiFetch(`/api/v1/leads/${id}`, { method: "DELETE" });
}
