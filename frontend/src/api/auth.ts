import { apiFetch, setTokens, clearTokens } from "./client";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  phone?: string | null;
  job_title?: string | null;
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
  try {
    // Revokes every token for this user server-side (token_version bump)
    await apiFetch<void>("/api/v1/auth/logout", { method: "POST" });
  } catch {
    // Even if the server is unreachable, clear local session state
  }
  clearTokens();
}

export async function getMe(): Promise<User> {
  return apiFetch<User>("/api/v1/auth/me");
}

export async function forgotPassword(email: string): Promise<void> {
  await apiFetch("/api/v1/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(token: string, newPassword: string): Promise<void> {
  await apiFetch("/api/v1/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

export interface ProfileUpdate {
  full_name?: string | null;
  phone?: string | null;
  job_title?: string | null;
  current_password?: string | null;
  new_password?: string | null;
}

interface ProfileUpdateResponse extends User {
  // Present only when the update changed the password (old tokens are revoked)
  access_token?: string | null;
  refresh_token?: string | null;
}

export async function updateProfile(data: ProfileUpdate): Promise<User> {
  const body: Record<string, string> = {};
  if (data.full_name !== undefined) body.full_name = data.full_name ?? "";
  if (data.phone !== undefined) body.phone = data.phone ?? "";
  if (data.job_title !== undefined) body.job_title = data.job_title ?? "";
  if (data.current_password !== undefined) body.current_password = data.current_password ?? "";
  if (data.new_password !== undefined) body.new_password = data.new_password ?? "";
  const res = await apiFetch<ProfileUpdateResponse>("/api/v1/auth/me", { method: "PATCH", body: JSON.stringify(body) });
  if (res.access_token && res.refresh_token) {
    // Password change revoked all previous tokens; adopt the fresh pair
    setTokens(res.access_token, res.refresh_token);
  }
  return res;
}
