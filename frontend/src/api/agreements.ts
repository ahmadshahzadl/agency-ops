import { apiFetch } from "./client";

export interface Clause {
  heading: string;
  body: string;
}

export interface Agreement {
  id: string;
  number: string;
  title: string;
  client_id: string | null;
  client_name: string | null;
  project_id: string | null;
  project_name: string | null;
  quote_id: string | null;
  quote_number: string | null;
  status: string;
  effective_date: string | null;
  valid_until: string | null;
  contract_value: string | null;
  currency: string;
  clauses: Clause[];
  accepted_at: string | null;
  accepted_by_name: string | null;
  accepted_ip: string | null;
  acceptance_method: string | null;
  decline_reason: string | null;
  terminated_at: string | null;
  termination_reason: string | null;
  created_by: string | null;
  created_at: string | null;
}

export interface AgreementPayload {
  title: string;
  client_id: string;
  project_id?: string | null;
  quote_id?: string | null;
  effective_date?: string | null;
  valid_until?: string | null;
  contract_value?: number | null;
  currency?: string;
  clauses?: Clause[];
}

export async function listAgreements(params?: { status_filter?: string; client_id?: string }): Promise<Agreement[]> {
  const sp = new URLSearchParams();
  if (params?.status_filter) sp.set("status_filter", params.status_filter);
  if (params?.client_id) sp.set("client_id", params.client_id);
  const qs = sp.toString();
  return apiFetch<Agreement[]>(`/api/v1/agreements${qs ? `?${qs}` : ""}`);
}

export async function getAgreementTemplate(params?: { client_id?: string; quote_id?: string; project_id?: string }): Promise<{ clauses: Clause[] }> {
  const sp = new URLSearchParams();
  if (params?.client_id) sp.set("client_id", params.client_id);
  if (params?.quote_id) sp.set("quote_id", params.quote_id);
  if (params?.project_id) sp.set("project_id", params.project_id);
  const qs = sp.toString();
  return apiFetch<{ clauses: Clause[] }>(`/api/v1/agreements/template${qs ? `?${qs}` : ""}`);
}

export async function createAgreement(data: AgreementPayload): Promise<Agreement> {
  return apiFetch<Agreement>("/api/v1/agreements", { method: "POST", body: JSON.stringify(data) });
}

export async function updateAgreement(id: string, data: Partial<AgreementPayload>): Promise<Agreement> {
  return apiFetch<Agreement>(`/api/v1/agreements/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deleteAgreement(id: string): Promise<void> {
  return apiFetch(`/api/v1/agreements/${id}`, { method: "DELETE" });
}

export async function sendAgreement(id: string): Promise<Agreement> {
  return apiFetch<Agreement>(`/api/v1/agreements/${id}/send`, { method: "POST" });
}

export async function markAgreementSigned(id: string, signerName?: string): Promise<Agreement> {
  return apiFetch<Agreement>(`/api/v1/agreements/${id}/mark-signed`, {
    method: "POST",
    body: JSON.stringify({ signer_name: signerName || null }),
  });
}

export async function terminateAgreement(id: string, reason: string): Promise<Agreement> {
  return apiFetch<Agreement>(`/api/v1/agreements/${id}/terminate`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function duplicateAgreement(id: string): Promise<Agreement> {
  return apiFetch<Agreement>(`/api/v1/agreements/${id}/duplicate`, { method: "POST" });
}

export async function openAgreementPdf(id: string, number: string): Promise<void> {
  const { downloadNamedPdf } = await import("./finance");
  return downloadNamedPdf(`/api/v1/agreements/${id}/pdf`, `${number}.pdf`);
}
