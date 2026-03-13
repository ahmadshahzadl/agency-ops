import { apiFetch } from "./client";

export interface Permission {
  id: string;
  code: string;
  description: string | null;
}

export interface Role {
  id: string;
  name: string;
  description: string | null;
  permission_ids: string[];
}

export async function listPermissions(): Promise<Permission[]> {
  return apiFetch<Permission[]>("/api/v1/roles/permissions");
}

export async function listRoles(): Promise<Role[]> {
  return apiFetch<Role[]>("/api/v1/roles");
}

export async function createRole(data: { name: string; description?: string; permission_ids?: string[] }): Promise<Role> {
  return apiFetch<Role>("/api/v1/roles", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateRole(
  id: string,
  data: { name?: string; description?: string; permission_ids?: string[] }
): Promise<Role> {
  return apiFetch<Role>(`/api/v1/roles/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteRole(id: string): Promise<void> {
  return apiFetch(`/api/v1/roles/${id}`, { method: "DELETE" });
}
