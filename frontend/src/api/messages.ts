import { apiFetch } from "./client";

export interface Message {
  id: string;
  sender_id: string;
  recipient_id: string;
  content: string;
  read_at: string | null;
  created_at: string;
  sender_name: string | null;
}

export interface ConversationSummary {
  other_user_id: string;
  other_user_name: string;
  last_message_at: string | null;
  last_message_preview: string | null;
  unread_count: number;
}

export async function listConversations(): Promise<ConversationSummary[]> {
  return apiFetch<ConversationSummary[]>("/api/v1/messages/conversations");
}

export async function listMessages(
  withUserId: string,
  params?: { skip?: number; limit?: number }
): Promise<Message[]> {
  const sp = new URLSearchParams({ with_user_id: withUserId });
  if (params?.skip != null) sp.set("skip", String(params.skip));
  if (params?.limit != null) sp.set("limit", String(params.limit));
  return apiFetch<Message[]>(`/api/v1/messages?${sp}`);
}

export async function sendMessage(recipientId: string, content: string): Promise<Message> {
  return apiFetch<Message>("/api/v1/messages", {
    method: "POST",
    body: JSON.stringify({ recipient_id: recipientId, content }),
  });
}

export async function markMessageRead(messageId: string): Promise<void> {
  return apiFetch(`/api/v1/messages/${messageId}/read`, { method: "POST" });
}
