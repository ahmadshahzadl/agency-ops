import { apiFetch, API_BASE, getToken } from "./client";

export interface Attachment {
  id: string;
  entity_type: string;
  entity_id: string;
  filename: string;
  content_type: string | null;
  size_bytes: number;
  uploaded_by: string | null;
  uploaded_by_name: string | null;
  created_at: string | null;
}

export async function listAttachments(entityType: string, entityId: string): Promise<Attachment[]> {
  return apiFetch<Attachment[]>(`/api/v1/attachments?entity_type=${entityType}&entity_id=${entityId}`);
}

/** Multipart upload — bypasses apiFetch (which forces JSON content-type). */
export async function uploadAttachment(entityType: string, entityId: string, file: File): Promise<Attachment> {
  const form = new FormData();
  form.set("entity_type", entityType);
  form.set("entity_id", entityId);
  form.set("file", file);
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/v1/attachments`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

export async function deleteAttachment(id: string): Promise<void> {
  return apiFetch(`/api/v1/attachments/${id}`, { method: "DELETE" });
}

/** Fetch the file as a blob URL (downloads need the Authorization header, so plain <a href> won't work). */
export async function fetchAttachmentBlobUrl(id: string): Promise<string> {
  const token = getToken();
  const res = await fetch(`${API_BASE}/api/v1/attachments/${id}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!res.ok) throw new Error("Download failed");
  return URL.createObjectURL(await res.blob());
}

export async function downloadAttachment(att: Attachment): Promise<void> {
  const url = await fetchAttachmentBlobUrl(att.id);
  const a = document.createElement("a");
  a.href = url;
  a.download = att.filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

export function isImage(att: Attachment): boolean {
  return (att.content_type || "").startsWith("image/");
}

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
