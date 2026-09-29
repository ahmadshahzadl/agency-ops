import { apiFetch } from "./client";

export type AttendanceStatus = "present" | "late";

export interface AttendanceRecord {
  id: string;
  user_id: string;
  user_name: string | null;
  user_email: string | null;
  employment_type: string | null;
  work_date: string;
  check_in_at: string;
  check_out_at: string | null;
  status: AttendanceStatus;
  hours: number | null;
  ip_address: string | null;
  latitude: number | string | null;
  longitude: number | string | null;
  location_accuracy_m: number | string | null;
  user_agent: string | null;
  note: string | null;
}

export interface AttendanceMe {
  today: AttendanceRecord | null;
  work_date: string;
  captures_location: boolean;
  start_time: string;
  timezone: string;
  recent: AttendanceRecord[];
  present_days_30: number;
  late_days_30: number;
}

export interface TodayRow {
  user_id: string;
  full_name: string | null;
  email: string;
  job_title: string | null;
  employment_type: string | null;
  status: "present" | "late" | "absent" | "off";
  record: AttendanceRecord | null;
}

export interface TodayBoard {
  work_date: string;
  is_working_day: boolean;
  present: number;
  late: number;
  absent: number;
  rows: TodayRow[];
}

export interface SummaryRow {
  user_id: string;
  full_name: string | null;
  email: string;
  employment_type: string | null;
  working_days: number;
  present_days: number;
  late_days: number;
  absent_days: number;
  total_hours: number;
  avg_hours: number | null;
  attendance_rate: number | null;
}

export interface AttendanceSummary {
  from_date: string;
  to_date: string;
  working_days: number;
  rows: SummaryRow[];
}

export async function getMyAttendance(days = 30): Promise<AttendanceMe> {
  return apiFetch<AttendanceMe>(`/api/v1/attendance/me?days=${days}`);
}

export async function checkIn(data: { latitude?: number; longitude?: number; accuracy_m?: number; note?: string }): Promise<AttendanceRecord> {
  return apiFetch<AttendanceRecord>("/api/v1/attendance/check-in", { method: "POST", body: JSON.stringify(data) });
}

export async function checkOut(note?: string): Promise<AttendanceRecord> {
  return apiFetch<AttendanceRecord>("/api/v1/attendance/check-out", { method: "POST", body: JSON.stringify({ note }) });
}

export async function getTodayBoard(): Promise<TodayBoard> {
  return apiFetch<TodayBoard>("/api/v1/attendance/today");
}

export async function getAttendanceSummary(params: { from?: string; to?: string; include_inactive?: boolean }): Promise<AttendanceSummary> {
  const sp = new URLSearchParams();
  if (params.from) sp.set("from", params.from);
  if (params.to) sp.set("to", params.to);
  if (params.include_inactive) sp.set("include_inactive", "true");
  const qs = sp.toString();
  return apiFetch<AttendanceSummary>(`/api/v1/attendance/summary${qs ? `?${qs}` : ""}`);
}

export async function listAttendanceRecords(params: { from?: string; to?: string; user_id?: string; limit?: number }): Promise<AttendanceRecord[]> {
  const sp = new URLSearchParams();
  if (params.from) sp.set("from", params.from);
  if (params.to) sp.set("to", params.to);
  if (params.user_id) sp.set("user_id", params.user_id);
  if (params.limit) sp.set("limit", String(params.limit));
  const qs = sp.toString();
  return apiFetch<AttendanceRecord[]>(`/api/v1/attendance/records${qs ? `?${qs}` : ""}`);
}

export async function correctAttendance(id: string, data: { check_in_at?: string; check_out_at?: string | null; status?: AttendanceStatus; note?: string }): Promise<AttendanceRecord> {
  return apiFetch<AttendanceRecord>(`/api/v1/attendance/records/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deleteAttendance(id: string): Promise<void> {
  return apiFetch(`/api/v1/attendance/records/${id}`, { method: "DELETE" });
}

/** Ask the browser for a position once; resolves to undefined if refused or unavailable. */
export function getBrowserPosition(timeoutMs = 8000): Promise<{ latitude: number; longitude: number; accuracy_m: number } | undefined> {
  return new Promise((resolve) => {
    if (typeof navigator === "undefined" || !navigator.geolocation) return resolve(undefined);
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude, accuracy_m: Math.round(pos.coords.accuracy) }),
      () => resolve(undefined),
      { enableHighAccuracy: false, timeout: timeoutMs, maximumAge: 60_000 },
    );
  });
}

export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
}

export function fmtDay(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" });
}

export function mapsLink(r: { latitude: number | string | null; longitude: number | string | null }): string | null {
  if (r.latitude == null || r.longitude == null) return null;
  return `https://www.google.com/maps?q=${r.latitude},${r.longitude}`;
}
