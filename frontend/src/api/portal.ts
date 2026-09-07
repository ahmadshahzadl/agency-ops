import { apiFetch, API_BASE, getToken } from "./client";

export interface PortalProject {
  id: string;
  name: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
  total_tasks: number;
  percent_done: number;
}

export interface PortalProjectDetail extends PortalProject {
  milestones: { name: string; due_date: string | null; completed: boolean; task_total: number; task_done: number }[];
  tasks: { title: string; status: string; item_type: string; due_date: string | null }[];
}

export interface PortalOverview {
  client_name: string;
  projects: PortalProject[];
  open_invoices: number;
  pending_quotes: number;
}

export interface PortalInvoice {
  id: string;
  number: string;
  amount: string;
  currency: string;
  status: string;
  issued_at: string | null;
  due_date: string | null;
  paid_total: string;
}

export interface PortalQuote {
  id: string;
  number: string;
  title: string;
  status: string;
  currency: string;
  total: string;
  valid_until: string | null;
  terms: string | null;
  items: { description: string; quantity: string; unit_price: string; line_total: string }[];
}

export interface PortalAgreement {
  id: string;
  number: string;
  title: string;
  status: string;
  effective_date: string | null;
  valid_until: string | null;
  contract_value: string | null;
  currency: string;
  clauses: { heading: string; body: string }[];
  accepted_at: string | null;
  accepted_by_name: string | null;
}

export async function listPortalAgreements(): Promise<PortalAgreement[]> {
  return apiFetch<PortalAgreement[]>("/api/v1/portal/agreements");
}

export async function acceptPortalAgreement(id: string, signerName: string): Promise<PortalAgreement> {
  return apiFetch<PortalAgreement>(`/api/v1/portal/agreements/${id}/accept`, {
    method: "POST",
    body: JSON.stringify({ signer_name: signerName }),
  });
}

export async function declinePortalAgreement(id: string, reason?: string): Promise<PortalAgreement> {
  return apiFetch<PortalAgreement>(`/api/v1/portal/agreements/${id}/decline`, {
    method: "POST",
    body: JSON.stringify({ reason: reason || null }),
  });
}

export async function getPortalOverview(): Promise<PortalOverview> {
  return apiFetch<PortalOverview>("/api/v1/portal/overview");
}

export async function getPortalProject(id: string): Promise<PortalProjectDetail> {
  return apiFetch<PortalProjectDetail>(`/api/v1/portal/projects/${id}`);
}

export async function listPortalInvoices(): Promise<PortalInvoice[]> {
  return apiFetch<PortalInvoice[]>("/api/v1/portal/invoices");
}

export async function listPortalQuotes(): Promise<PortalQuote[]> {
  return apiFetch<PortalQuote[]>("/api/v1/portal/quotes");
}

export async function acceptPortalQuote(id: string): Promise<PortalQuote> {
  return apiFetch<PortalQuote>(`/api/v1/portal/quotes/${id}/accept`, { method: "POST" });
}

export async function declinePortalQuote(id: string): Promise<PortalQuote> {
  return apiFetch<PortalQuote>(`/api/v1/portal/quotes/${id}/decline`, { method: "POST" });
}

export async function reportPortalIssue(projectId: string, data: {
  title: string;
  description?: string;
  steps_to_reproduce?: string;
  severity?: string;
}): Promise<void> {
  await apiFetch(`/api/v1/portal/projects/${projectId}/issues`, { method: "POST", body: JSON.stringify(data) });
}

export async function openPortalPdf(path: "invoices" | "quotes" | "agreements", id: string, number: string): Promise<void> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/v1/portal/${path}/${id}/pdf`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!res.ok) throw new Error("Could not load PDF");
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = `${number}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
