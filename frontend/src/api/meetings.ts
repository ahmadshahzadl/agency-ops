import { apiFetch } from "./client";

export interface Meeting {
  id: string;
  project_id: string | null;
  title: string;
  description: string | null;
  start_at: string;
  end_at: string;
  location: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  attendee_ids: string[];
}

export async function listMeetings(params?: { skip?: number; limit?: number; project_id?: string }): Promise<Meeting[]> {
  const sp = new URLSearchParams();
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  if (params?.project_id) sp.set("project_id", params.project_id);
  const qs = sp.toString();
  return apiFetch<Meeting[]>(`/api/v1/meetings${qs ? `?${qs}` : ""}`);
}

export async function createMeeting(data: {
  project_id?: string;
  title: string;
  description?: string;
  start_at: string;
  end_at: string;
  location?: string;
  attendee_ids?: string[];
}): Promise<Meeting> {
  return apiFetch<Meeting>("/api/v1/meetings", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateMeeting(
  id: string,
  data: Partial<Meeting> & { attendee_ids?: string[] }
): Promise<Meeting> {
  return apiFetch<Meeting>(`/api/v1/meetings/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteMeeting(id: string): Promise<void> {
  return apiFetch(`/api/v1/meetings/${id}`, { method: "DELETE" });
}
