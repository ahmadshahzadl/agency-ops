import { apiFetch } from "./client";

export interface Invoice {
  id: string;
  client_id: string;
  project_id: string | null;
  number: string;
  amount: number;
  currency: string;
  status: string;
  due_date: string | null;
  issued_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Payment {
  id: string;
  invoice_id: string;
  amount: number;
  paid_at: string;
  reference: string | null;
  created_at: string;
}

export interface Expense {
  id: string;
  project_id: string | null;
  description: string;
  amount: number;
  currency: string;
  expense_date: string | null;
  created_by: string | null;
  created_at: string;
}

export async function listInvoices(params?: {
  skip?: number;
  limit?: number;
  client_id?: string;
  status_filter?: string;
}): Promise<Invoice[]> {
  const sp = new URLSearchParams();
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  if (params?.client_id) sp.set("client_id", params.client_id);
  if (params?.status_filter) sp.set("status_filter", params.status_filter);
  const qs = sp.toString();
  return apiFetch<Invoice[]>(`/api/v1/invoices${qs ? `?${qs}` : ""}`);
}

export async function createInvoice(data: Omit<Invoice, "id" | "created_at" | "updated_at">): Promise<Invoice> {
  return apiFetch<Invoice>("/api/v1/invoices", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateInvoice(id: string, data: Partial<Invoice>): Promise<Invoice> {
  return apiFetch<Invoice>(`/api/v1/invoices/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteInvoice(id: string): Promise<void> {
  return apiFetch(`/api/v1/invoices/${id}`, { method: "DELETE" });
}

export async function listInvoicePayments(invoiceId: string): Promise<Payment[]> {
  return apiFetch<Payment[]>(`/api/v1/invoices/${invoiceId}/payments`);
}

export async function createPayment(data: Omit<Payment, "id" | "created_at">): Promise<Payment> {
  return apiFetch<Payment>("/api/v1/payments", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function listExpenses(params?: { skip?: number; limit?: number; project_id?: string }): Promise<Expense[]> {
  const sp = new URLSearchParams();
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  if (params?.project_id) sp.set("project_id", params.project_id);
  const qs = sp.toString();
  return apiFetch<Expense[]>(`/api/v1/expenses${qs ? `?${qs}` : ""}`);
}

export async function createExpense(data: Omit<Expense, "id" | "created_at" | "created_by">): Promise<Expense> {
  return apiFetch<Expense>("/api/v1/expenses", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateExpense(id: string, data: Partial<Expense>): Promise<Expense> {
  return apiFetch<Expense>(`/api/v1/expenses/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteExpense(id: string): Promise<void> {
  return apiFetch(`/api/v1/expenses/${id}`, { method: "DELETE" });
}
