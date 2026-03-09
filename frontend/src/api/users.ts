import { apiFetch } from "./client";

export interface UserList {
  id: string;
  email: string;
  full_name: string | null;
  phone?: string | null;
  job_title?: string | null;
  is_active: boolean;
  manager_id: string | null;
  role_ids: string[];
  team_ids: string[];
}

export async function listUsers(params?: { skip?: number; limit?: number; q?: string }): Promise<UserList[]> {
  const sp = new URLSearchParams();
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  if (params?.q) sp.set("q", params.q);
  const qs = sp.toString();
  return apiFetch<UserList[]>(`/api/v1/users${qs ? `?${qs}` : ""}`);
}

/** Users the current user can assign tasks to (for assignee dropdown): admin=all, manager=self+team, member=self only. */
export async function listAssignableUsers(): Promise<UserList[]> {
  return apiFetch<UserList[]>("/api/v1/users/assignable");
}

export async function createUser(data: {
  email: string;
  password: string;
  full_name?: string;
  phone?: string | null;
  job_title?: string | null;
  is_active?: boolean;
  manager_id?: string | null;
  role_ids?: string[];
  team_ids?: string[];
}): Promise<UserList> {
  return apiFetch<UserList>("/api/v1/users", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateUser(
  id: string,
  data: {
    full_name?: string;
    phone?: string | null;
    job_title?: string | null;
    is_active?: boolean;
    manager_id?: string | null;
    role_ids?: string[];
    team_ids?: string[];
  }
): Promise<UserList> {
  return apiFetch<UserList>(`/api/v1/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteUser(id: string): Promise<void> {
  return apiFetch(`/api/v1/users/${id}`, { method: "DELETE" });
}
