import { apiFetch, API_BASE, getToken } from "./client";

export interface InvoiceItem {
  id?: string;
  description: string;
  quantity: number | string;
  unit_price: number | string;
}

export interface Invoice {
  items?: InvoiceItem[];
  fx_currency?: string | null;
  fx_rate?: number | string | null;
  bank_name?: string | null;
  account_title?: string | null;
  account_number?: string | null;
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
  category?: string;
  recurring_expense_id?: string | null;
  related_invoice_id?: string | null;
  payee_user_id?: string | null;
  commission_percent?: number | string | null;
  payee_name?: string | null;
  invoice_number?: string | null;
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

export async function downloadNamedPdf(path: string, filename: string): Promise<void> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!res.ok) throw new Error("Could not load PDF");
  const url = URL.createObjectURL(await res.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

export async function openInvoicePdf(id: string, number: string): Promise<void> {
  return downloadNamedPdf(`/api/v1/invoices/${id}/pdf`, `${number}.pdf`);
}

export async function sendInvoice(id: string): Promise<Invoice> {
  return apiFetch<Invoice>(`/api/v1/invoices/${id}/send`, { method: "POST" });
}

/* ---------------- recurring bills, subscriptions, salaries ---------------- */

export type RecurringFrequency = "weekly" | "monthly" | "quarterly" | "yearly";
export type RecurringStatus = "scheduled" | "due_soon" | "due_today" | "overdue" | "paused";

export interface RecurringExpense {
  id: string;
  description: string;
  category: string;
  amount: number | string;
  currency: string;
  frequency: RecurringFrequency;
  due_day: number;
  next_due_date: string;
  last_paid_on: string | null;
  project_id: string | null;
  payee_user_id: string | null;
  notes: string | null;
  remind_days_before: number[];
  is_active: boolean;
  status: RecurringStatus;
  days_until_due: number;
  payee_name: string | null;
  project_name: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export type RecurringExpenseInput = {
  description: string;
  category: string;
  amount: number;
  currency: string;
  frequency: RecurringFrequency;
  due_day: number;
  next_due_date?: string | null;
  project_id?: string | null;
  payee_user_id?: string | null;
  notes?: string | null;
  remind_days_before?: number[];
  is_active?: boolean;
};

export async function listRecurringExpenses(params?: { include_inactive?: boolean; category?: string; due_within_days?: number }): Promise<RecurringExpense[]> {
  const sp = new URLSearchParams();
  if (params?.include_inactive) sp.set("include_inactive", "true");
  if (params?.category) sp.set("category", params.category);
  if (params?.due_within_days != null) sp.set("due_within_days", String(params.due_within_days));
  const qs = sp.toString();
  return apiFetch<RecurringExpense[]>(`/api/v1/recurring-expenses${qs ? `?${qs}` : ""}`);
}

export async function createRecurringExpense(data: RecurringExpenseInput): Promise<RecurringExpense> {
  return apiFetch<RecurringExpense>("/api/v1/recurring-expenses", { method: "POST", body: JSON.stringify(data) });
}

export async function updateRecurringExpense(id: string, data: Partial<RecurringExpenseInput>): Promise<RecurringExpense> {
  return apiFetch<RecurringExpense>(`/api/v1/recurring-expenses/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deleteRecurringExpense(id: string): Promise<void> {
  return apiFetch(`/api/v1/recurring-expenses/${id}`, { method: "DELETE" });
}

export async function payRecurringExpense(id: string, data: { paid_on?: string; amount?: number; note?: string }): Promise<Expense> {
  return apiFetch<Expense>(`/api/v1/recurring-expenses/${id}/pay`, { method: "POST", body: JSON.stringify(data) });
}

export async function skipRecurringExpense(id: string): Promise<RecurringExpense> {
  return apiFetch<RecurringExpense>(`/api/v1/recurring-expenses/${id}/skip`, { method: "POST", body: "{}" });
}

export async function recurringExpenseHistory(id: string): Promise<Expense[]> {
  return apiFetch<Expense[]>(`/api/v1/recurring-expenses/${id}/history`);
}

export async function runExpenseRemindersNow(): Promise<{ sent: number }> {
  return apiFetch<{ sent: number }>("/api/v1/recurring-expenses/run-reminders", { method: "POST", body: "{}" });
}

/* ---------------- payroll ---------------- */

export type EmploymentType = "full_time" | "part_time" | "contractor" | "intern";

export interface PayrollRow {
  user_id: string;
  full_name: string | null;
  email: string;
  job_title: string | null;
  employment_type: EmploymentType | null;
  joined_on: string | null;
  left_on: string | null;
  is_active: boolean;
  salary_id: string | null;
  amount: number | string | null;
  currency: string | null;
  frequency: RecurringFrequency | null;
  due_day: number | null;
  next_due_date: string | null;
  last_paid_on: string | null;
  salary_active: boolean;
  status: RecurringStatus | "not_set";
  days_until_due: number | null;
  paid_this_period: boolean;
}

export async function listPayroll(includeInactive = false): Promise<PayrollRow[]> {
  return apiFetch<PayrollRow[]>(`/api/v1/payroll${includeInactive ? "?include_inactive=true" : ""}`);
}

export async function updatePayroll(userId: string, data: {
  amount?: number; currency?: string; due_day?: number; frequency?: RecurringFrequency; salary_active?: boolean;
  employment_type?: EmploymentType | null; joined_on?: string | null; left_on?: string | null; job_title?: string | null;
}): Promise<PayrollRow> {
  return apiFetch<PayrollRow>(`/api/v1/payroll/${userId}`, { method: "PATCH", body: JSON.stringify(data) });
}
