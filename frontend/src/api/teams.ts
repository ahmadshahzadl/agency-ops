import { apiFetch } from "./client";

export interface Team {
  id: string;
  name: string;
  description: string | null;
}

export interface TeamWithMembers extends Team {
  user_ids: string[];
}

export async function listTeams(): Promise<TeamWithMembers[]> {
  return apiFetch<TeamWithMembers[]>("/api/v1/teams");
}

/** Teams the current user is a member of (for leads/projects when not admin). */
export async function listMyTeams(): Promise<TeamWithMembers[]> {
  return apiFetch<TeamWithMembers[]>("/api/v1/teams/my");
}

export async function createTeam(data: { name: string; description?: string }): Promise<Team> {
  return apiFetch<Team>("/api/v1/teams", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getTeam(id: string): Promise<TeamWithMembers> {
  return apiFetch<TeamWithMembers>(`/api/v1/teams/${id}`);
}

export async function updateTeam(id: string, data: { name?: string; description?: string }): Promise<Team> {
  return apiFetch<Team>(`/api/v1/teams/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteTeam(id: string): Promise<void> {
  return apiFetch(`/api/v1/teams/${id}`, { method: "DELETE" });
}

export async function addTeamMember(teamId: string, userId: string): Promise<void> {
  return apiFetch(`/api/v1/teams/${teamId}/members/${userId}`, { method: "POST" });
}

export async function removeTeamMember(teamId: string, userId: string): Promise<void> {
  return apiFetch(`/api/v1/teams/${teamId}/members/${userId}`, { method: "DELETE" });
}
