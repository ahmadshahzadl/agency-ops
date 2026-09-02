import { apiFetch } from "./client";
import type { Invoice } from "./finance";
import type { Project } from "./projects";

export interface QuoteItem {
  id?: string;
  description: string;
  quantity: number | string;
  unit_price: number | string;
  line_total?: string;
}

export interface Quote {
  id: string;
  number: string;
  title: string;
  client_id: string | null;
  client_name: string | null;
  lead_id: string | null;
  lead_company: string | null;
  status: string;
  currency: string;
  total: string;
  valid_until: string | null;
  terms: string | null;
  project_id: string | null;
  accepted_at: string | null;
  created_by: string | null;
  created_at: string | null;
  items: QuoteItem[];
}

export interface QuotePayload {
  title: string;
  client_id?: string | null;
  lead_id?: string | null;
  currency?: string;
  valid_until?: string | null;
  terms?: string | null;
  items?: { description: string; quantity: number; unit_price: number }[];
}

export async function listQuotes(params?: { status_filter?: string; client_id?: string; lead_id?: string }): Promise<Quote[]> {
  const sp = new URLSearchParams();
  if (params?.status_filter) sp.set("status_filter", params.status_filter);
  if (params?.client_id) sp.set("client_id", params.client_id);
  if (params?.lead_id) sp.set("lead_id", params.lead_id);
  const qs = sp.toString();
  return apiFetch<Quote[]>(`/api/v1/quotes${qs ? `?${qs}` : ""}`);
}

export async function createQuote(data: QuotePayload): Promise<Quote> {
  return apiFetch<Quote>("/api/v1/quotes", { method: "POST", body: JSON.stringify(data) });
}

export async function updateQuote(id: string, data: Partial<QuotePayload>): Promise<Quote> {
  return apiFetch<Quote>(`/api/v1/quotes/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deleteQuote(id: string): Promise<void> {
  return apiFetch(`/api/v1/quotes/${id}`, { method: "DELETE" });
}

export async function sendQuote(id: string): Promise<Quote> {
  return apiFetch<Quote>(`/api/v1/quotes/${id}/send`, { method: "POST" });
}

export async function acceptQuote(id: string): Promise<Quote> {
  return apiFetch<Quote>(`/api/v1/quotes/${id}/accept`, { method: "POST" });
}

export async function rejectQuote(id: string): Promise<Quote> {
  return apiFetch<Quote>(`/api/v1/quotes/${id}/reject`, { method: "POST" });
}

export async function convertQuote(id: string): Promise<Project> {
  return apiFetch<Project>(`/api/v1/quotes/${id}/convert`, { method: "POST" });
}

export async function invoiceQuote(id: string): Promise<Invoice> {
  return apiFetch<Invoice>(`/api/v1/quotes/${id}/invoice`, { method: "POST" });
}
