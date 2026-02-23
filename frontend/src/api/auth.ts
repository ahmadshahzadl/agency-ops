import { apiFetch, setTokens, clearTokens } from "./client";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  permissions: string[];
  roles?: string[];
  can_manage_tasks?: boolean;
  can_manage_leads?: boolean;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const data = await apiFetch<LoginResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setTokens(data.access_token, data.refresh_token);
  return data;
}

export async function logout(): Promise<void> {
  clearTokens();
}

export async function getMe(): Promise<User> {
  return apiFetch<User>("/api/v1/auth/me");
}

export interface ProfileUpdate {
  full_name?: string | null;
  current_password?: string | null;
  new_password?: string | null;
}

export async function updateProfile(data: ProfileUpdate): Promise<User> {
  const body: Record<string, string> = {};
  if (data.full_name !== undefined) body.full_name = data.full_name ?? "";
  if (data.current_password !== undefined) body.current_password = data.current_password ?? "";
  if (data.new_password !== undefined) body.new_password = data.new_password ?? "";
  return apiFetch<User>("/api/v1/auth/me", { method: "PATCH", body: JSON.stringify(body) });
}
