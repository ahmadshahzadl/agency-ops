import { apiFetch } from "./client";

export interface Clause {
  heading: string;
  body: string;
}

export type AgreementTypeKey = "nda" | "service" | "retainer" | "maintenance";

export interface AgreementType {
  key: AgreementTypeKey;
  label: string;
  short_label: string;
  description: string;
  has_value: boolean;
}

export interface Agreement {
  id: string;
  number: string;
  title: string;
  agreement_type: AgreementTypeKey;
  type_label: string;
  sign_url: string | null;
  signer_email: string | null;
  signer_title: string | null;
  accepted_user_agent: string | null;
  acceptance_hash: string | null;
  countersigned_by_name: string | null;
  countersigned_at: string | null;
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
  agreement_type?: AgreementTypeKey;
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

export async function getAgreementTypes(): Promise<AgreementType[]> {
  return apiFetch<AgreementType[]>("/api/v1/agreements/types");
}

export async function getAgreementTemplate(params?: { agreement_type?: AgreementTypeKey; client_id?: string; quote_id?: string; project_id?: string }): Promise<{ agreement_type: AgreementTypeKey; title_suggestion: string; clauses: Clause[] }> {
  const sp = new URLSearchParams();
  if (params?.agreement_type) sp.set("agreement_type", params.agreement_type);
  if (params?.client_id) sp.set("client_id", params.client_id);
  if (params?.quote_id) sp.set("quote_id", params.quote_id);
  if (params?.project_id) sp.set("project_id", params.project_id);
  const qs = sp.toString();
  return apiFetch<{ agreement_type: AgreementTypeKey; title_suggestion: string; clauses: Clause[] }>(`/api/v1/agreements/template${qs ? `?${qs}` : ""}`);
}

export async function getSignLink(id: string): Promise<{ url: string; expires_at: string | null }> {
  return apiFetch<{ url: string; expires_at: string | null }>(`/api/v1/agreements/${id}/sign-link`);
}

export async function countersignAgreement(id: string, name?: string): Promise<Agreement> {
  return apiFetch<Agreement>(`/api/v1/agreements/${id}/countersign`, { method: "POST", body: JSON.stringify({ name: name || null }) });
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

export async function sendAgreement(id: string, to?: string, signForCompany = true): Promise<Agreement> {
  return apiFetch<Agreement>(`/api/v1/agreements/${id}/send`, { method: "POST", body: JSON.stringify({ to: to || null, sign_for_company: signForCompany }) });
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
