import { apiFetch } from "./client";

export interface Notification {
  id: string;
  user_id: string;
  title: string;
  message: string | null;
  link: string | null;
  type: string;
  reference_id: string | null;
  read_at: string | null;
  created_at: string;
}

export async function listNotifications(params?: {
  unread_only?: boolean;
  skip?: number;
  limit?: number;
}): Promise<Notification[]> {
  const sp = new URLSearchParams();
  if (params?.unread_only) sp.set("unread_only", "true");
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  const q = sp.toString();
  return apiFetch<Notification[]>(`/api/v1/notifications${q ? `?${q}` : ""}`);
}

export async function getUnreadCount(): Promise<{ count: number }> {
  return apiFetch<{ count: number }>("/api/v1/notifications/unread-count");
}

export async function markRead(notificationIds: string[]): Promise<void> {
  await apiFetch("/api/v1/notifications/mark-read", {
    method: "POST",
    body: JSON.stringify({ notification_ids: notificationIds }),
  });
}

export async function markOneRead(id: string): Promise<void> {
  await apiFetch(`/api/v1/notifications/${id}/mark-read`, { method: "POST" });
}

export async function markAllRead(): Promise<void> {
  await apiFetch("/api/v1/notifications/mark-all-read", { method: "POST" });
}
