import { apiFetch } from "./client";

export interface GoogleStatus {
  configured: boolean;
  connected: boolean;
  account_email: string | null;
  connected_at: string | null;
  last_error: string | null;
}

export async function getGoogleStatus(): Promise<GoogleStatus> {
  return apiFetch<GoogleStatus>("/api/v1/integrations/google/status");
}

export async function getGoogleConnectUrl(): Promise<string> {
  const r = await apiFetch<{ url: string }>("/api/v1/integrations/google/connect");
  return r.url;
}

export async function disconnectGoogle(): Promise<void> {
  return apiFetch("/api/v1/integrations/google", { method: "DELETE" });
}
