import { apiFetch, setTokens, clearTokens } from "./client";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  permissions: string[];
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
