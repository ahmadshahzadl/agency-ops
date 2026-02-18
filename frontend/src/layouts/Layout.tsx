import { useEffect, useState } from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/store/auth";
import { getUnreadCount } from "@/api/notifications";

const navItems: { to: string; label: string; permission?: string }[] = [
  { to: "/dashboard", label: "Dashboard", permission: "dashboard:read" },
  { to: "/leads", label: "Leads", permission: "leads:read" },
  { to: "/clients", label: "Clients", permission: "clients:read" },
  { to: "/projects", label: "Projects", permission: "projects:read" },
  { to: "/tasks", label: "Tasks", permission: "tasks:read" },
  { to: "/meetings", label: "Meetings", permission: "meetings:read" },
  { to: "/invoices", label: "Invoices", permission: "finance:read" },
  { to: "/expenses", label: "Expenses", permission: "finance:read" },
  { to: "/analytics", label: "Analytics", permission: "analytics:read" },
  { to: "/team-activity", label: "Team activity", permission: "team_activity:read" },
  { to: "/announcements", label: "Announcements", permission: "admin:all" },
  { to: "/users", label: "Users", permission: "admin:all" },
  { to: "/teams", label: "Teams", permission: "admin:all" },
  { to: "/roles", label: "Roles", permission: "admin:all" },
  { to: "/notifications", label: "Notifications" },
  { to: "/profile", label: "Profile" },
];

const SALES_HIDDEN_NAV = ["/invoices", "/expenses", "/analytics"];
const SALES_ONLY_HIDDEN_NAV = ["/clients", "/team-activity"];

export default function Layout() {
  const { user, logout, hasPermission } = useAuth();
  const navigate = useNavigate();
  const [unreadCount, setUnreadCount] = useState(0);

  const refreshUnreadCount = () => {
    getUnreadCount()
      .then((r) => setUnreadCount(r.count))
      .catch(() => {});
  };

  useEffect(() => {
    refreshUnreadCount();
    const onRefresh = () => refreshUnreadCount();
    window.addEventListener("notifications-updated", onRefresh);
    return () => window.removeEventListener("notifications-updated", onRefresh);
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate("/login");
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
    <div className="min-h-screen flex bg-slate-900 text-slate-200">
      <aside className="w-56 bg-slate-800 border-r border-slate-700 flex flex-col">
        <div className="p-4 border-b border-slate-700">
          <h1 className="font-semibold text-lg text-primary">Software House</h1>
          <p className="text-xs text-slate-400 mt-1">{user?.email}</p>
        </div>
        <nav className="flex-1 p-2 space-y-0.5">
          {visibleNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive ? "bg-primary/20 text-primary" : "text-slate-300 hover:bg-slate-700"
                }`
              }
            >
              <span className="flex items-center justify-between">
                {item.label}
                {item.to === "/notifications" && unreadCount > 0 && (
                  <span className="bg-primary text-white text-xs font-medium rounded-full min-w-[1.25rem] h-5 px-1.5 flex items-center justify-center">
                    {unreadCount > 99 ? "99+" : unreadCount}
                  </span>
                )}
              </span>
            </NavLink>
          ))}
        </nav>
        <div className="p-2 border-t border-slate-700">
          <button
            onClick={handleLogout}
            className="w-full px-3 py-2 text-left text-sm text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg"
          >
            Logout
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
