import { API_BASE } from "./client";

export interface VersionResponse {
  version: string;
}

/** Fetch the app version reported by the server (for "Check for updates"). */
export async function fetchServerVersion(): Promise<VersionResponse> {
  const res = await fetch(`${API_BASE}/api/v1/version`);
  if (!res.ok) throw new Error("Failed to fetch version");
  return res.json();
}

/**
 * Compare two semver-like strings (e.g. "0.0.1", "1.2.3").
 * Returns: 1 if a > b, -1 if a < b, 0 if equal.
 */
export function compareVersions(a: string, b: string): number {
  const pa = a.split(".").map((n) => parseInt(n, 10) || 0);
  const pb = b.split(".").map((n) => parseInt(n, 10) || 0);
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const na = pa[i] ?? 0;
    const nb = pb[i] ?? 0;
    if (na > nb) return 1;
    if (na < nb) return -1;
  }
  return 0;
}
