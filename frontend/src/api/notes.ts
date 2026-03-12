import { apiFetch } from "./client";

export type NoteEntityType =
  | "lead"
  | "task"
  | "meeting"
  | "project"
  | "client"
  | "invoice"
  | "expense"
  | "announcement";

export interface Note {
  id: string;
  entity_type: string;
  entity_id: string;
  content: string;
  is_private: boolean;
  created_by: string;
  created_at: string;
  updated_at: string | null;
  created_by_name: string | null;
}

export async function listNotes(entityType: NoteEntityType, entityId: string): Promise<Note[]> {
  const params = new URLSearchParams({ entity_type: entityType, entity_id: entityId });
  return apiFetch<Note[]>(`/api/v1/notes?${params}`);
}

export async function createNote(data: {
  entity_type: NoteEntityType;
  entity_id: string;
  content: string;
  is_private: boolean;
}): Promise<Note> {
  return apiFetch<Note>("/api/v1/notes", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateNote(
  id: string,
  data: { content?: string; is_private?: boolean }
): Promise<Note> {
  return apiFetch<Note>(`/api/v1/notes/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteNote(id: string): Promise<void> {
  return apiFetch(`/api/v1/notes/${id}`, { method: "DELETE" });
}
