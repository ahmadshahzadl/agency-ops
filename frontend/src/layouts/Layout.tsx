import { useEffect, useState } from "react";
import { Outlet, NavLink, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "@/store/auth";
import { APP_NAME } from "@/config";
import { BrandLogo } from "@/components/BrandLogo";
import { applyTheme, getStoredTheme } from "@/lib/theme";
import {
  getUnreadCount,
  listNotifications,
  markOneRead,
  markAllRead,
  type Notification,
} from "@/api/notifications";
import { getWsUrl, getToken } from "@/api/client";

const navItems: { to: string; label: string; permission?: string }[] = [
  { to: "/dashboard", label: "Overview" },
  { to: "/leads", label: "Leads", permission: "leads:read" },
  { to: "/quotes", label: "Quotes", permission: "quotes:read" },
  { to: "/clients", label: "Clients", permission: "clients:read" },
  { to: "/projects", label: "Projects", permission: "projects:read" },
  { to: "/tasks", label: "Tasks", permission: "tasks:read" },
  { to: "/boards", label: "Boards", permission: "tasks:read" },
  { to: "/timesheet", label: "Timesheet", permission: "time:read" },
  { to: "/meetings", label: "Meetings", permission: "meetings:read" },
  { to: "/messages", label: "Messages" },
  { to: "/invoices", label: "Invoices", permission: "finance:read" },
  { to: "/expenses", label: "Expenses", permission: "expenses:read" },
  { to: "/analytics", label: "Reports", permission: "analytics:read" },
  { to: "/team-activity", label: "Team activity", permission: "team_activity:read" },
  { to: "/announcements", label: "Announcements", permission: "announcements:read" },
  { to: "/users", label: "Users", permission: "admin:all" },
  { to: "/teams", label: "Teams", permission: "admin:all" },
  { to: "/roles", label: "Roles", permission: "admin:all" },
];

const NavIcon = ({ path, className = "w-5 h-5 shrink-0" }: { path: string; className?: string }) => {
  const icons: Record<string, JSX.Element> = {
    "/dashboard": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
      </svg>
    ),
    "/leads": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    ),
    "/quotes": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
    "/clients": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
      </svg>
    ),
    "/projects": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
      </svg>
    ),
    "/tasks": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
    "/boards": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h3a1 1 0 011 1v14a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM10.5 5a1 1 0 011-1h3a1 1 0 011 1v9a1 1 0 01-1 1h-3a1 1 0 01-1-1V5zM17 5a1 1 0 011-1h1a1 1 0 011 1v6a1 1 0 01-1 1h-1a1 1 0 01-1-1V5z" />
      </svg>
    ),
    "/timesheet": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    "/meetings": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    ),
    "/messages": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
    ),
    "/invoices": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 14l6-6m-5.5.5h.01m4.99 5h.01M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l3.5-2 3.5 2 3.5-2 3.5 2zM10 8.5a.5.5 0 11-1 0 .5.5 0 011 0zm5 5a.5.5 0 11-1 0 .5.5 0 011 0z" />
      </svg>
    ),
    "/expenses": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    ),
    "/analytics": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    "/team-activity": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
    "/announcements": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5.882V19.24a1.76 1.76 0 01-3.417.592l-2.147-6.15M18 13a3 3 0 100-6M5.436 13a3 3 0 005.564 0z" />
      </svg>
    ),
    "/users": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
      </svg>
    ),
    "/teams": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
      </svg>
    ),
    "/roles": (
      <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
      </svg>
    ),
  };
  return icons[path] ?? (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
    </svg>
  );
};

const SALES_HIDDEN_NAV = ["/invoices", "/expenses", "/analytics"];
const SALES_ONLY_HIDDEN_NAV = ["/clients", "/team-activity"];

const PATH_TO_HEADER_TITLE: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/leads": "Leads",
  "/quotes": "Quotes",
  "/clients": "Customers",
  "/projects": "Projects",
  "/tasks": "Tasks",
  "/boards": "Boards",
  "/timesheet": "Timesheet",
  "/meetings": "Meetings",
  "/messages": "Messages",
  "/invoices": "Invoices",
  "/expenses": "Expenses",
  "/analytics": "Reports",
  "/team-activity": "Team activity",
  "/announcements": "Announcements",
  "/users": "Users",
  "/teams": "Teams",
  "/roles": "Roles",
  "/profile": "Settings",
};

const LOGIN_TRANSITION_KEY = "loginTransition";

export default function Layout() {
  const { user, logout, hasPermission } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [unreadCount, setUnreadCount] = useState(0);
  const [showLoginMorph, setShowLoginMorph] = useState(() =>
    typeof sessionStorage !== "undefined" ? !!sessionStorage.getItem(LOGIN_TRANSITION_KEY) : false
  );

  useEffect(() => {
    applyTheme(getStoredTheme());
    const m = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if (getStoredTheme() === "system") applyTheme("system");
    };
    m.addEventListener("change", onChange);
    return () => m.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    if (!showLoginMorph) return;
    const done = () => {
      sessionStorage.removeItem(LOGIN_TRANSITION_KEY);
      setShowLoginMorph(false);
    };
    const t = setTimeout(done, 820);
    return () => clearTimeout(t);
  }, [showLoginMorph]);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [notificationItems, setNotificationItems] = useState<Notification[]>([]);
  const [notificationsLoading, setNotificationsLoading] = useState(false);

  const headerTitle = PATH_TO_HEADER_TITLE[location.pathname] ?? (location.pathname === "/" ? "Dashboard" : location.pathname.slice(1).replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()));

  const refreshUnreadCount = () => {
    getUnreadCount()
      .then((r) => setUnreadCount(r.count))
      .catch(() => {});
  };

  const loadNotifications = () => {
    setNotificationsLoading(true);
    listNotifications({ limit: 100 })
      .then((list) => {
        setNotificationItems(list);
        return getUnreadCount();
      })
      .then((r) => setUnreadCount(r.count))
      .catch(() => {})
      .finally(() => setNotificationsLoading(false));
  };

  useEffect(() => {
    if (notificationsOpen) loadNotifications();
  }, [notificationsOpen]);

  useEffect(() => {
    refreshUnreadCount();
    const onRefresh = () => refreshUnreadCount();
    window.addEventListener("notifications-updated", onRefresh);
    return () => window.removeEventListener("notifications-updated", onRefresh);
  }, []);

  // Single WebSocket for all real-time updates; dispatch events so pages can refetch
  useEffect(() => {
    if (!user) return;
    const wsUrl = getWsUrl("/api/v1/ws/activity");
    const token = getToken();
    const url = token ? `${wsUrl}?token=${encodeURIComponent(token)}` : wsUrl;
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(url);
      ws.onmessage = (ev) => {
        try {
          const payload = JSON.parse(ev.data as string) as { type?: string; types?: string[] };
          const types = payload.types ?? (payload.type ? [payload.type] : []);
          types.forEach((t) => window.dispatchEvent(new CustomEvent(`ws:${t}`)));
        } catch {
          // ignore parse errors
        }
      };
      ws.onerror = () => {};
      ws.onclose = () => {};
    } catch {
      // ignore
    }
    return () => {
      if (ws?.readyState === WebSocket.OPEN) ws.close();
    };
  }, [user]);

  useEffect(() => {
    const onWsNotifications = () => {
      refreshUnreadCount();
      if (notificationsOpen) loadNotifications();
    };
    window.addEventListener("ws:notifications_updated", onWsNotifications);
    return () => window.removeEventListener("ws:notifications_updated", onWsNotifications);
  }, [notificationsOpen]);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const handleMarkNotificationRead = async (id: string) => {
    await markOneRead(id);
    loadNotifications();
    window.dispatchEvent(new Event("notifications-updated"));
  };

  const handleMarkAllNotificationsRead = async () => {
    await markAllRead();
    loadNotifications();
    window.dispatchEvent(new Event("notifications-updated"));
  };

  let visibleNav = navItems.filter((item) => {
    if (!item.permission) return true;
    if (item.permission === "projects:read")
      return hasPermission("projects:read") || hasPermission("dashboard:read");
    return hasPermission(item.permission);
  });
  const isSales = user?.roles?.includes("sales");
  const isSalesOnly = isSales && !hasPermission("admin:all") && !user?.roles?.includes("manager");
  if (isSales) {
    visibleNav = visibleNav.filter((item) => !SALES_HIDDEN_NAV.includes(item.to));
  }
  if (isSalesOnly) {
    visibleNav = visibleNav.filter((item) => !SALES_ONLY_HIDDEN_NAV.includes(item.to));
  }

  return (
    <div className="h-screen flex overflow-hidden bg-[#f5f6f8] dark:bg-gray-900">
      {/* Post-login morph overlay: full-screen blue shrinks to sidebar then fades */}
      {showLoginMorph && (
        <div
          className="fixed inset-y-0 left-0 w-full z-[100] bg-[#01184e] dark:bg-gray-800 animate-login-morph pointer-events-none"
          aria-hidden
        />
      )}
      {/* Sidebar - full viewport height, does not scroll */}
      <aside className="w-60 h-full flex flex-col shrink-0 shadow-lg overflow-hidden bg-[#01184e] dark:bg-gray-800">
        <div className="p-6 flex justify-center">
          <div className="flex flex-col items-center gap-2">
            <BrandLogo variant="sidebar" />
            <span className="font-semibold text-lg text-white tracking-tight text-center">{APP_NAME}</span>
          </div>
        </div>
        <nav className="flex-1 px-3 pb-4 space-y-0.5 overflow-y-auto sidebar-nav-scroll">
          {visibleNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-white/25 text-white border-l-4 border-white shadow-sm"
                    : "text-white/90 hover:bg-white/10 hover:text-white border-l-4 border-transparent"
                }`
              }
            >
              <NavIcon path={item.to} />
              <span className="truncate">{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-white/20">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-3 py-2.5 text-left text-sm font-medium text-white/90 hover:bg-white/10 hover:text-white rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Log out
          </button>
        </div>
      </aside>
      {/* Main: white header + content (only this area scrolls) */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <header className="shrink-0 h-20 px-6 flex items-center justify-between border-b border-gray-100 dark:border-gray-700 bg-white dark:bg-gray-800">
          <h1 className="font-titillium text-2xl font-bold text-gray-900 dark:text-white truncate">
            {headerTitle}
          </h1>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setNotificationsOpen(true)}
              className="relative p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
              aria-label="Notifications"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 min-w-[1rem] h-4 px-1 flex items-center justify-center bg-[#01184e] text-white text-xs font-semibold rounded-full">
                  {unreadCount > 99 ? "99+" : unreadCount}
                </span>
              )}
            </button>
            <button
              type="button"
              onClick={() => navigate("/profile")}
              className="flex items-center gap-2 rounded-lg py-1.5 pl-1 pr-2 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium bg-primary dark:bg-primary" style={{ backgroundColor: "#01184e" }}>
                {(user?.full_name || user?.email || "?").charAt(0).toUpperCase()}
              </div>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-200 hidden sm:inline truncate max-w-[160px]">
                {user?.full_name || user?.email}
              </span>
              <svg className="w-4 h-4 text-gray-500 dark:text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-auto bg-[#f5f6f8] dark:bg-gray-900 p-6">
          <Outlet />
        </main>
      </div>

      {/* Notifications drawer - slides in from right */}
      {notificationsOpen && (
        <>
          <div
            className="fixed inset-0 bg-black/30 z-40"
            aria-hidden
            onClick={() => setNotificationsOpen(false)}
          />
          <div
            className="fixed top-0 right-0 bottom-0 w-full max-w-md bg-white shadow-xl z-50 flex flex-col animate-slide-in-right"
            role="dialog"
            aria-label="Notifications"
          >
            <div className="shrink-0 flex items-center justify-between px-4 py-3 border-b border-gray-100">
              <h2 className="text-lg font-semibold text-gray-900">Notifications</h2>
              <div className="flex items-center gap-2">
                {unreadCount > 0 && (
                  <button
                    type="button"
                    onClick={handleMarkAllNotificationsRead}
                    className="text-sm font-medium text-[#01184e] hover:underline"
                  >
                    Mark all read
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setNotificationsOpen(false)}
                  className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-gray-700"
                  aria-label="Close"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-auto p-4">
              {notificationsLoading ? (
                <p className="text-gray-500 text-sm">Loading…</p>
              ) : notificationItems.length === 0 ? (
                <p className="text-gray-500 text-sm">No notifications.</p>
              ) : (
                <ul className="space-y-2">
                  {notificationItems.map((n) => (
                    <li
                      key={n.id}
                      className={`rounded-lg border p-3 ${
                        n.read_at ? "border-gray-100 bg-gray-50/50" : "border-[#5791c4]/40"
                      }`}
                      style={n.read_at ? undefined : { backgroundColor: "#5791c4" }}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <p className={`font-medium ${n.read_at ? "text-gray-900" : "text-white"}`}>{n.title}</p>
                          {n.message && (
                            <p className={`text-sm mt-0.5 whitespace-pre-wrap ${n.read_at ? "text-gray-600" : "text-white/90"}`}>{n.message}</p>
                          )}
                          <p className={`text-xs mt-2 ${n.read_at ? "text-gray-400" : "text-white/80"}`}>
                            {new Date(n.created_at).toLocaleString()}
                          </p>
                          {n.link && (
                            <button
                              type="button"
                              onClick={() => {
                                setNotificationsOpen(false);
                                handleMarkNotificationRead(n.id);
                                navigate(n.link!);
                              }}
                              className={`inline-block mt-2 text-sm font-medium text-left hover:underline ${n.read_at ? "text-[#01184e]" : "text-white underline-offset-2"}`}
                            >
                              View
                            </button>
                          )}
                        </div>
                        {!n.read_at && (
                          <button
                            type="button"
                            onClick={() => handleMarkNotificationRead(n.id)}
                            className="shrink-0 px-2 py-1 rounded text-xs font-medium text-white border border-white/50 hover:bg-white/20"
                          >
                            Mark read
                          </button>
                        )}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
