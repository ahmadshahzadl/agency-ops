import { useEffect, useState } from "react";
import {
  listNotifications,
  markOneRead,
  markAllRead,
  getUnreadCount,
  type Notification,
} from "@/api/notifications";

export default function NotificationsPage() {
  const [items, setItems] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [notifs, count] = await Promise.all([
        listNotifications({ limit: 100 }),
        getUnreadCount(),
      ]);
      setItems(notifs);
      setUnreadCount(count.count);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const onWsNotifications = () => load();
    window.addEventListener("ws:notifications_updated", onWsNotifications);
    return () => window.removeEventListener("ws:notifications_updated", onWsNotifications);
  }, []);

  const handleMarkRead = async (id: string) => {
    await markOneRead(id);
    load();
    window.dispatchEvent(new Event("notifications-updated"));
  };

  const handleMarkAllRead = async () => {
    await markAllRead();
    load();
    window.dispatchEvent(new Event("notifications-updated"));
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold text-white">Notifications</h1>
        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllRead}
            className="px-4 py-2 rounded-lg bg-slate-700 text-slate-200 hover:bg-slate-600"
          >
            Mark all as read
          </button>
        )}
      </div>
      {loading ? (
        <p className="text-slate-400">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-slate-400">No notifications.</p>
      ) : (
        <div className="space-y-2">
          {items.map((n) => (
            <div
              key={n.id}
              className={`rounded-xl border p-4 ${
                n.read_at ? "border-slate-700 bg-slate-800/30" : "border-primary/30 bg-slate-800/60"
              }`}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-white">{n.title}</p>
                  {n.message && <p className="text-sm text-slate-400 mt-1 whitespace-pre-wrap">{n.message}</p>}
                  <p className="text-xs text-slate-500 mt-2">
                    {new Date(n.created_at).toLocaleString()}
                  </p>
                </div>
                {!n.read_at && (
                  <button
                    onClick={() => handleMarkRead(n.id)}
                    className="shrink-0 px-3 py-1 rounded-lg bg-primary/20 text-primary text-sm hover:bg-primary/30"
                  >
                    Mark read
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
