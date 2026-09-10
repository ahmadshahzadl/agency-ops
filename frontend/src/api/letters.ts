import { apiFetch } from "./client";

export interface Letter {
  id: string;
  number: string;
  letter_type: string;
  subject: string;
  recipient_name: string | null;
  recipient_address: string | null;
  recipient_email: string | null;
  client_id: string | null;
  client_name: string | null;
  body: string;
  letter_date: string | null;
  signatory_name: string | null;
  signatory_title: string | null;
  status: string;
  issued_at: string | null;
  created_by: string | null;
  created_at: string | null;
}

export interface LetterPayload {
  letter_type?: string;
  subject: string;
  body: string;
  recipient_name?: string | null;
  recipient_address?: string | null;
  recipient_email?: string | null;
  client_id?: string | null;
  letter_date?: string | null;
  signatory_name?: string | null;
  signatory_title?: string | null;
}

export async function listLetterTypes(): Promise<{ value: string; label: string }[]> {
  return apiFetch<{ value: string; label: string }[]>("/api/v1/letters/types");
}

export async function getLetterTemplate(params: { letter_type: string; recipient_name?: string; client_id?: string }): Promise<{ letter_type: string; subject: string; body: string }> {
  const sp = new URLSearchParams({ letter_type: params.letter_type });
  if (params.recipient_name) sp.set("recipient_name", params.recipient_name);
  if (params.client_id) sp.set("client_id", params.client_id);
  return apiFetch(`/api/v1/letters/template?${sp.toString()}`);
}

export async function listLetters(params?: { status_filter?: string; letter_type?: string }): Promise<Letter[]> {
  const sp = new URLSearchParams();
  if (params?.status_filter) sp.set("status_filter", params.status_filter);
  if (params?.letter_type) sp.set("letter_type", params.letter_type);
  const qs = sp.toString();
  return apiFetch<Letter[]>(`/api/v1/letters${qs ? `?${qs}` : ""}`);
}

export async function createLetter(data: LetterPayload): Promise<Letter> {
  return apiFetch<Letter>("/api/v1/letters", { method: "POST", body: JSON.stringify(data) });
}

export async function updateLetter(id: string, data: Partial<LetterPayload>): Promise<Letter> {
  return apiFetch<Letter>(`/api/v1/letters/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deleteLetter(id: string): Promise<void> {
  return apiFetch(`/api/v1/letters/${id}`, { method: "DELETE" });
}

export async function issueLetter(id: string): Promise<Letter> {
  return apiFetch<Letter>(`/api/v1/letters/${id}/issue`, { method: "POST" });
}

export async function sendLetter(id: string): Promise<Letter> {
  return apiFetch<Letter>(`/api/v1/letters/${id}/send`, { method: "POST" });
}

export async function openLetterPdf(id: string, number: string): Promise<void> {
  const { downloadNamedPdf } = await import("./finance");
  return downloadNamedPdf(`/api/v1/letters/${id}/pdf`, `${number}.pdf`);
}

export async function openBlankLetterhead(): Promise<void> {
  const { downloadNamedPdf } = await import("./finance");
  return downloadNamedPdf("/api/v1/letters/blank-pdf", "fuorix-letterhead.pdf");
}
