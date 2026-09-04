import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "@/store/auth";
import { getWsUrl, getToken } from "@/api/client";
import {
  listConversations,
  listMessages,
  sendMessage,
  markMessageRead,
  type Message,
  type ConversationSummary,
  listDirectory,
  type DirectoryUser,
} from "@/api/messages";


function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  return (name.slice(0, 2) || "?").toUpperCase();
}

/** Parse ISO timestamp as UTC if no timezone suffix, so display in user's local time (e.g. Pakistan +5). */
function parseUtc(iso: string | null | undefined): Date {
  if (!iso) return new Date();
  const s = iso.trim();
  if (!/Z|[+-]\d{2}:?\d{2}$/.test(s)) return new Date(s + "Z");
  return new Date(s);
}

function formatMessageTime(iso: string): string {
  const d = parseUtc(iso);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const msgDay = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const diffDays = Math.floor((today.getTime() - msgDay.getTime()) / 86400000);
  const time = d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  if (diffDays === 0) return time;
  if (diffDays === 1) return `Yesterday ${time}`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" }) + " " + time;
}

function formatConversationTime(iso: string | null): string {
  if (!iso) return "";
  const d = parseUtc(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  if (diffMs < 60000) return "Just now";
  if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)}m`;
  if (diffMs < 86400000) return `${Math.floor(diffMs / 3600000)}h`;
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d`;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function Avatar({ name, className = "w-10 h-10" }: { name: string; className?: string }) {
  const initials = getInitials(name);
  return (
    <div
      className={`shrink-0 rounded-full bg-primary/20 text-primary flex items-center justify-center font-semibold text-sm ${className}`}
      title={name}
    >
      {initials}
    </div>
  );
}

export default function Messages() {
  const [searchParams] = useSearchParams();
  const { user } = useAuth();
  const withUserId = searchParams.get("with");
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [selectedUserName, setSelectedUserName] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [input, setInput] = useState("");
  const [showNewMessage, setShowNewMessage] = useState(false);
  const [userList, setUserList] = useState<DirectoryUser[]>([]);
  const [userSearch, setUserSearch] = useState("");
  const [loadingNewMessage, setLoadingNewMessage] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const currentUserId = user?.id ?? null;

  const loadConversations = async () => {
    setLoadingConversations(true);
    try {
      const list = await listConversations();
      setConversations(list);
    } finally {
      setLoadingConversations(false);
    }
  };

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    if (withUserId) setSelectedUserId(withUserId);
  }, [withUserId]);

  useEffect(() => {
    if (!currentUserId) return;
    const token = getToken();
    if (!token) return;
    const url = `${getWsUrl("/api/v1/ws/messages")}?token=${encodeURIComponent(token)}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;
    ws.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data as string) as { type?: string; message?: Message };
        if (payload.type === "new_message" && payload.message) {
          const msg = payload.message;
          if (msg.recipient_id === currentUserId && msg.sender_id === selectedUserId) {
            setMessages((prev) => (prev.some((m) => m.id === msg.id) ? prev : [...prev, msg]));
          }
          loadConversations();
        }
      } catch {
        // ignore
      }
    };
    ws.onerror = () => {};
    ws.onclose = () => {};
    return () => {
      wsRef.current = null;
      ws.close();
    };
  }, [currentUserId, selectedUserId]);

  useEffect(() => {
    if (!selectedUserId) {
      setMessages([]);
      return;
    }
    setLoadingMessages(true);
    listMessages(selectedUserId, { limit: 100 })
      .then((list) => {
        setMessages(list);
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        list.forEach((m) => {
          if (m.recipient_id === currentUserId && !m.read_at) markMessageRead(m.id).catch(() => {});
        });
        loadConversations();
      })
      .finally(() => setLoadingMessages(false));
  }, [selectedUserId, currentUserId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || !selectedUserId || sending) return;
    setSending(true);
    setInput("");
    try {
      const sent = await sendMessage(selectedUserId, text);
      setMessages((prev) => [...prev, sent]);
      loadConversations();
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    } finally {
      setSending(false);
    }
  };

  const openNewMessage = () => {
    setShowNewMessage(true);
    setUserSearch("");
    setLoadingNewMessage(true);
    listDirectory()
      .then(setUserList)
      .catch(() => {})
      .finally(() => setLoadingNewMessage(false));
  };

  const selectUserForChat = (u: DirectoryUser) => {
    if (u.id === currentUserId) return;
    setSelectedUserId(u.id);
    setSelectedUserName(u.full_name || u.email || "User");
    setShowNewMessage(false);
  };

  const selectedConversation = conversations.find((c) => c.other_user_id === selectedUserId);
  const threadTitle = selectedConversation?.other_user_name ?? selectedUserName ?? "Chat";

  const getUserTeamNames = (u: DirectoryUser): string[] => u.team_names || [];

  const filteredUserList = userList.filter((u) => {
    if (u.id === currentUserId) return false;
    const q = userSearch.trim().toLowerCase();
    if (!q) return true;
    const name = (u.full_name || "").toLowerCase();
    const email = (u.email || "").toLowerCase();
    const teamNames = getUserTeamNames(u).join(" ").toLowerCase();
    return name.includes(q) || email.includes(q) || teamNames.includes(q);
  });

  const emptyState = (
    <div className="flex flex-col items-center justify-center flex-1 text-center px-6 py-12">
      <div className="w-16 h-16 rounded-2xl bg-gray-100 dark:bg-slate-700/50 flex items-center justify-center mb-4">
        <svg className="w-8 h-8 text-gray-400 dark:text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      </div>
      <p className="text-gray-500 dark:text-slate-400 text-sm max-w-xs">
        Select a conversation or start a new one to message your team.
      </p>
      <button
        type="button"
        onClick={openNewMessage}
        className="mt-4 rounded-xl bg-primary px-4 py-2.5 text-sm font-medium text-white hover:opacity-90 transition"
      >
        New message
      </button>
    </div>
  );

  return (
    <div className="h-[calc(100vh-7rem)] flex rounded-2xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800/40 shadow-sm overflow-hidden">
      {/* Conversation list */}
      <div className="w-80 md:w-96 shrink-0 flex flex-col bg-gray-50 dark:bg-slate-800/50 border-r border-gray-200 dark:border-slate-700">
        <div className="p-4 border-b border-gray-200 dark:border-slate-700 shrink-0">
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white tracking-tight">Messages</h2>
            <button
              type="button"
              onClick={openNewMessage}
              className="shrink-0 rounded-xl bg-primary px-4 py-2 text-sm font-medium text-white hover:opacity-90 transition shadow-sm"
            >
              + New
            </button>
          </div>
        </div>

        {showNewMessage && (
          <div className="shrink-0 border-b border-gray-200 dark:border-slate-700 p-3 space-y-2">
            <input
              type="text"
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
              placeholder="Search by name, email or team…"
              className="w-full rounded-xl border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2.5 text-sm text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
            />
            <div className="max-h-64 overflow-y-auto rounded-xl border border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800/80">
              {loadingNewMessage ? (
                <div className="p-4 space-y-2">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="flex items-center gap-3 p-2">
                      <div className="w-9 h-9 rounded-full bg-gray-200 dark:bg-slate-700/60 animate-pulse" />
                      <div className="flex-1 min-w-0">
                        <div className="h-4 w-28 rounded bg-gray-200 dark:bg-slate-700/60 animate-pulse mb-1" />
                        <div className="h-3 w-20 rounded bg-gray-100 dark:bg-slate-700/40 animate-pulse" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : filteredUserList.length === 0 ? (
                <p className="p-3 text-gray-500 dark:text-slate-500 text-sm">
                  {userList.length === 0 ? "Loading users…" : "No users match your search."}
                </p>
              ) : (
                filteredUserList.map((u) => {
                  const teamNames = getUserTeamNames(u);
                  return (
                    <button
                      key={u.id}
                      type="button"
                      onClick={() => selectUserForChat(u)}
                      className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-gray-100 dark:hover:bg-slate-700/50 text-left transition rounded-lg"
                    >
                      <Avatar name={u.full_name || u.email || "?"} className="w-9 h-9" />
                      <div className="min-w-0 flex-1">
                        <p className="text-gray-900 dark:text-white font-medium truncate">{u.full_name || u.email || "No name"}</p>
                        {u.full_name && u.email && (
                          <p className="text-gray-500 dark:text-slate-500 text-xs truncate">{u.email}</p>
                        )}
                        {teamNames.length > 0 && (
                          <p className="text-gray-400 dark:text-slate-500 text-xs truncate mt-0.5">
                            {teamNames.join(", ")}
                          </p>
                        )}
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>
        )}

        <div className="flex-1 overflow-y-auto min-h-0">
          {loadingConversations ? (
            <div className="p-4 space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="flex items-center gap-3 p-2">
                  <div className="w-11 h-11 rounded-full bg-gray-200 dark:bg-slate-700/60 animate-pulse" />
                  <div className="flex-1 min-w-0">
                    <div className="h-4 w-32 rounded bg-gray-200 dark:bg-slate-700/60 animate-pulse mb-2" />
                    <div className="h-3 w-24 rounded bg-gray-100 dark:bg-slate-700/40 animate-pulse" />
                  </div>
                </div>
              ))}
            </div>
          ) : conversations.length === 0 ? (
            <div className="p-6 text-center">
              <p className="text-gray-500 dark:text-slate-500 text-sm">No conversations yet.</p>
              <p className="text-gray-400 dark:text-slate-600 text-xs mt-1">Click &quot;New&quot; to message someone.</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-200 dark:divide-slate-700/50">
              {conversations.map((c) => {
                const isSelected = selectedUserId === c.other_user_id;
                return (
                  <li key={c.other_user_id}>
                    <button
                      type="button"
                      onClick={() => setSelectedUserId(c.other_user_id)}
                      className={`w-full flex items-center gap-3 p-3 text-left transition rounded-none border-l-2 ${
                        isSelected
                          ? "bg-primary/10 dark:bg-primary/15 border-l-primary"
                          : "border-l-transparent hover:bg-gray-100 dark:hover:bg-slate-700/30"
                      }`}
                    >
                      <Avatar name={c.other_user_name} className="w-11 h-11" />
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className={`font-medium truncate ${isSelected ? "text-gray-900 dark:text-white" : "text-gray-800 dark:text-slate-200"}`}>
                            {c.other_user_name}
                          </span>
                          {c.last_message_at && (
                            <span className="shrink-0 text-xs text-gray-500 dark:text-slate-500">
                              {formatConversationTime(c.last_message_at)}
                            </span>
                          )}
                        </div>
                        <div className="flex items-center justify-between gap-2 mt-0.5">
                          <p className="text-sm text-gray-500 dark:text-slate-400 truncate flex-1 min-w-0">
                            {c.last_message_preview || "No messages yet"}
                          </p>
                          {c.unread_count > 0 && (
                            <span className="shrink-0 min-w-[1.25rem] h-5 rounded-full bg-primary text-white text-xs font-medium flex items-center justify-center px-1.5">
                              {c.unread_count > 99 ? "99+" : c.unread_count}
                            </span>
                          )}
                        </div>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>

      {/* Thread */}
      <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-slate-900/30">
        {!selectedUserId ? (
          emptyState
        ) : (
          <>
            <div className="shrink-0 flex items-center gap-3 p-4 border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/40">
              <Avatar name={threadTitle} className="w-10 h-10" />
              <div className="min-w-0 flex-1">
                <h3 className="font-semibold text-gray-900 dark:text-white truncate">{threadTitle}</h3>
                <p className="text-xs text-gray-500 dark:text-slate-500">Direct message</p>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto min-h-0">
              <div className="p-4 pb-2 space-y-1">
                {loadingMessages ? (
                  <div className="flex flex-col gap-4 py-6">
                    <div className="flex justify-start">
                      <div className="h-12 w-48 rounded-2xl rounded-bl bg-gray-200 dark:bg-slate-700/60 animate-pulse" />
                    </div>
                    <div className="flex justify-end">
                      <div className="h-10 w-40 rounded-2xl rounded-br bg-primary/20 dark:bg-primary/30 animate-pulse" />
                    </div>
                    <div className="flex justify-start">
                      <div className="h-8 w-56 rounded-2xl rounded-bl bg-gray-200 dark:bg-slate-700/60 animate-pulse" />
                    </div>
                  </div>
                ) : messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <p className="text-gray-500 dark:text-slate-500 text-sm">No messages yet. Say hello!</p>
                  </div>
                ) : (
                  messages.map((m) => {
                    const isMe = m.sender_id === currentUserId;
                    return (
                      <div
                        key={m.id}
                        className={`flex ${isMe ? "justify-end" : "justify-start"} group`}
                      >
                        <div
                          className={`max-w-[78%] rounded-2xl px-4 py-2.5 shadow-sm ${
                            isMe
                              ? "rounded-br-md bg-primary text-white"
                              : "rounded-bl-md bg-gray-100 dark:bg-slate-700/80 text-gray-900 dark:text-slate-100 border border-gray-200 dark:border-slate-600/50"
                          }`}
                        >
                          <p className="whitespace-pre-wrap break-words text-[15px] leading-relaxed">
                            {m.content}
                          </p>
                          <div className={`flex items-center justify-end gap-1.5 mt-1.5 ${isMe ? "text-white/80" : "text-gray-500 dark:text-slate-400"}`}>
                            <span className="text-[11px]">{formatMessageTime(m.created_at)}</span>
                            {isMe && (
                              <span className="text-[10px]">
                                {m.read_at ? "✓✓" : "✓"}
                              </span>
                            )}
                            {!isMe && !m.read_at && (
                              <span className="text-[10px] text-primary">· new</span>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
                <div ref={messagesEndRef} className="h-2" />
              </div>
            </div>

            <div className="shrink-0 p-4 pt-3 border-t border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/40">
              <div className="flex gap-2 items-end rounded-2xl border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800/80 p-1.5 focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition">
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder="Type a message… (Enter to send, Shift+Enter for new line)"
                  rows={1}
                  className="flex-1 min-h-[44px] max-h-32 resize-none rounded-xl bg-transparent px-4 py-2.5 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-slate-500 focus:outline-none text-[15px] leading-relaxed"
                />
                <button
                  type="button"
                  onClick={handleSend}
                  disabled={sending || !input.trim()}
                  className="shrink-0 rounded-xl bg-primary p-2.5 text-white hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed transition"
                  title="Send"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
