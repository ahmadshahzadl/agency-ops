import { apiFetch } from "./client";

export interface Announcement {
  id: string;
  title: string;
  body: string | null;
  target_type: string;
  target_user_ids: string[] | null;
  created_by_id: string | null;
  created_at: string;
}

export interface AnnouncementCreate {
  title: string;
  body?: string | null;
  target_type: "all" | "users";
  target_user_ids?: string[] | null;
}

export async function listAnnouncements(params?: { skip?: number; limit?: number }): Promise<Announcement[]> {
  const sp = new URLSearchParams();
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  const q = sp.toString();
  return apiFetch<Announcement[]>(`/api/v1/announcements${q ? `?${q}` : ""}`);
}

export async function createAnnouncement(data: AnnouncementCreate): Promise<Announcement> {
  return apiFetch<Announcement>("/api/v1/announcements", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getAnnouncement(id: string): Promise<Announcement> {
  return apiFetch<Announcement>(`/api/v1/announcements/${id}`);
}

export async function updateAnnouncement(id: string, data: Partial<AnnouncementCreate>): Promise<Announcement> {
  return apiFetch<Announcement>(`/api/v1/announcements/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteAnnouncement(id: string): Promise<void> {
  await apiFetch(`/api/v1/announcements/${id}`, { method: "DELETE" });
}
