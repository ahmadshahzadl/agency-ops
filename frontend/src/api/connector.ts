import { apiFetch } from "./client";

/** Claude connector (remote MCP): consent page + Settings -> Connected apps. */

export interface ConsentInfo {
  client_name: string;
  account: string;
  blocked_reason: string | null;
}

export interface ConnectorGrant {
  id: string;
  client_name: string;
  created_at: string | null;
  last_used_at: string | null;
}

export interface ConnectorStatus {
  enabled: boolean;
  mcp_url: string;
  can_connect: boolean;
  grants: ConnectorGrant[];
}

export async function getConsentInfo(clientId: string, redirectUri: string): Promise<ConsentInfo> {
  const q = new URLSearchParams({ client_id: clientId, redirect_uri: redirectUri });
  return apiFetch<ConsentInfo>(`/api/v1/oauth/authorize/info?${q}`);
}

export async function decideConsent(params: Record<string, string>, approve: boolean): Promise<string> {
  const r = await apiFetch<{ redirect_to: string }>("/api/v1/oauth/authorize/approve", {
    method: "POST",
    body: JSON.stringify({ ...params, approve }),
  });
  return r.redirect_to;
}

export async function getConnectorStatus(): Promise<ConnectorStatus> {
  return apiFetch<ConnectorStatus>("/api/v1/oauth/grants");
}

export async function revokeConnector(grantId: string): Promise<void> {
  return apiFetch(`/api/v1/oauth/grants/${grantId}/revoke`, { method: "POST" });
}
