import { apiFetch } from "./client";
import type { Task } from "./tasks";

export interface BoardMember {
  user_id: string;
  full_name: string | null;
  email: string | null;
}

export interface Board {
  id: string;
  project_id: string;
  name: string;
  position: number;
  created_by: string | null;
  created_at: string | null;
  updated_at: string | null;
  members: BoardMember[];
  task_count: number;
}

export async function listBoards(projectId?: string): Promise<Board[]> {
  const qs = projectId ? `?project_id=${projectId}` : "";
  return apiFetch<Board[]>(`/api/v1/boards${qs}`);
}

export async function createBoard(data: {
  project_id: string;
  name: string;
  member_ids?: string[];
}): Promise<Board> {
  return apiFetch<Board>("/api/v1/boards", { method: "POST", body: JSON.stringify(data) });
}

export async function updateBoard(id: string, data: { name?: string; position?: number }): Promise<Board> {
  return apiFetch<Board>(`/api/v1/boards/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deleteBoard(id: string): Promise<void> {
  return apiFetch(`/api/v1/boards/${id}`, { method: "DELETE" });
}

export async function listBoardTasks(id: string): Promise<Task[]> {
  return apiFetch<Task[]>(`/api/v1/boards/${id}/tasks`);
}

export async function addBoardMember(boardId: string, userId: string): Promise<Board> {
  return apiFetch<Board>(`/api/v1/boards/${boardId}/members`, {
    method: "POST",
    body: JSON.stringify({ user_id: userId }),
  });
}

export async function removeBoardMember(boardId: string, userId: string): Promise<Board> {
  return apiFetch<Board>(`/api/v1/boards/${boardId}/members/${userId}`, { method: "DELETE" });
}
