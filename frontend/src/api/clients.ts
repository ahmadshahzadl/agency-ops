import { apiFetch } from "./client";

export interface Client {
  id: string;
  name: string;
  contact_email: string | null;
  contact_phone: string | null;
  address: string | null;
  team_id: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export async function listClients(params?: { skip?: number; limit?: number; q?: string }): Promise<Client[]> {
  const sp = new URLSearchParams();
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  if (params?.q) sp.set("q", params.q);
  const qs = sp.toString();
  return apiFetch<Client[]>(`/api/v1/clients${qs ? `?${qs}` : ""}`);
}

export async function getClient(id: string): Promise<Client> {
  return apiFetch<Client>(`/api/v1/clients/${id}`);
}

export async function createClient(data: Omit<Client, "id" | "created_at" | "updated_at" | "created_by">): Promise<Client> {
  return apiFetch<Client>("/api/v1/clients", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateClient(id: string, data: Partial<Client>): Promise<Client> {
  return apiFetch<Client>(`/api/v1/clients/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteClient(id: string): Promise<void> {
  return apiFetch(`/api/v1/clients/${id}`, { method: "DELETE" });
}
