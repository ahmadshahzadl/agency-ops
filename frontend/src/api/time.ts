import { apiFetch } from "./client";
import type { Invoice } from "./finance";

export interface TimeEntry {
  id: string;
  user_id: string;
  user_name: string | null;
  project_id: string;
  project_name: string | null;
  task_id: string | null;
  task_title: string | null;
  work_date: string;
  hours: string;
  description: string | null;
  billable: boolean;
  hourly_rate: string | null;
  invoice_id: string | null;
  created_at: string | null;
}

export interface TimeSummary {
  total_hours: string;
  billable_hours: string;
  unbilled_billable_hours: string;
  unbilled_amount: string;
  by_user: { user_id: string; user_name: string | null; hours: string }[];
}

export async function listTimeEntries(params?: {
  project_id?: string;
  task_id?: string;
  user_id?: string;
  date_from?: string;
  date_to?: string;
  unbilled?: boolean;
  limit?: number;
}): Promise<TimeEntry[]> {
  const sp = new URLSearchParams();
  if (params?.project_id) sp.set("project_id", params.project_id);
  if (params?.task_id) sp.set("task_id", params.task_id);
  if (params?.user_id) sp.set("user_id", params.user_id);
  if (params?.date_from) sp.set("date_from", params.date_from);
  if (params?.date_to) sp.set("date_to", params.date_to);
  if (params?.unbilled) sp.set("unbilled", "true");
  if (params?.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return apiFetch<TimeEntry[]>(`/api/v1/time-entries${qs ? `?${qs}` : ""}`);
}

export async function createTimeEntry(data: {
  project_id?: string;
  task_id?: string | null;
  work_date: string;
  hours: number;
  description?: string;
  billable?: boolean;
  user_id?: string;
}): Promise<TimeEntry> {
  return apiFetch<TimeEntry>("/api/v1/time-entries", { method: "POST", body: JSON.stringify(data) });
}

export async function deleteTimeEntry(id: string): Promise<void> {
  return apiFetch(`/api/v1/time-entries/${id}`, { method: "DELETE" });
}

export async function getTimeSummary(params?: {
  project_id?: string;
  date_from?: string;
  date_to?: string;
}): Promise<TimeSummary> {
  const sp = new URLSearchParams();
  if (params?.project_id) sp.set("project_id", params.project_id);
  if (params?.date_from) sp.set("date_from", params.date_from);
  if (params?.date_to) sp.set("date_to", params.date_to);
  const qs = sp.toString();
  return apiFetch<TimeSummary>(`/api/v1/time-entries/summary${qs ? `?${qs}` : ""}`);
}

export async function invoiceFromTime(data: {
  project_id: string;
  date_from?: string;
  date_to?: string;
  hourly_rate?: number;
  number?: string;
  currency?: string;
  due_date?: string;
}): Promise<Invoice> {
  return apiFetch<Invoice>("/api/v1/invoices/from-time", { method: "POST", body: JSON.stringify(data) });
}

export async function listInvoiceTimeEntries(invoiceId: string): Promise<TimeEntry[]> {
  return apiFetch<TimeEntry[]>(`/api/v1/invoices/${invoiceId}/time-entries`);
}
