import { apiFetch } from "./client";

export type BookingHours = Record<string, [string, string][]>;

export interface BookingQuestion {
  id: string;
  label: string;
  type: "text" | "textarea";
  required: boolean;
}

export interface BookingPage {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  duration_minutes: number;
  buffer_before_minutes: number;
  buffer_after_minutes: number;
  min_notice_minutes: number;
  max_days_ahead: number;
  timezone: string;
  hours: BookingHours;
  questions: BookingQuestion[];
  location_text: string | null;
  host_user_id: string | null;
  host_name: string | null;
  host_google_connected: boolean;
  hosts: { id: string; name: string; google_connected: boolean }[];
  co_host_ids: string[];
  overrides: Record<string, [string, string][]>;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export type BookingPageInput = Omit<BookingPage, "id" | "host_name" | "host_google_connected" | "hosts" | "created_at" | "updated_at">;

export async function listBookingPages(): Promise<BookingPage[]> {
  return apiFetch<BookingPage[]>("/api/v1/booking-pages");
}

export async function createBookingPage(data: BookingPageInput): Promise<BookingPage> {
  return apiFetch<BookingPage>("/api/v1/booking-pages", { method: "POST", body: JSON.stringify(data) });
}

export async function updateBookingPage(id: string, data: Partial<BookingPageInput>): Promise<BookingPage> {
  return apiFetch<BookingPage>(`/api/v1/booking-pages/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deleteBookingPage(id: string): Promise<void> {
  return apiFetch(`/api/v1/booking-pages/${id}`, { method: "DELETE" });
}

export async function previewBookingSlots(id: string, start: string, end: string): Promise<{ timezone: string; slots: string[] }> {
  return apiFetch(`/api/v1/booking-pages/${id}/slots?start=${start}&end=${end}`);
}
