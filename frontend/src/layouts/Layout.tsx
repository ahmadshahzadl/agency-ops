import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/store/auth";

const navItems: { to: string; label: string; permission?: string }[] = [
  { to: "/dashboard", label: "Dashboard", permission: "analytics:read" },
  { to: "/leads", label: "Leads", permission: "leads:read" },
  { to: "/clients", label: "Clients", permission: "clients:read" },
  { to: "/projects", label: "Projects", permission: "projects:read" },
  { to: "/tasks", label: "Tasks", permission: "tasks:read" },
  { to: "/meetings", label: "Meetings", permission: "meetings:read" },
  { to: "/invoices", label: "Invoices", permission: "finance:read" },
  { to: "/expenses", label: "Expenses", permission: "finance:read" },
  { to: "/analytics", label: "Analytics", permission: "analytics:read" },
  { to: "/users", label: "Users", permission: "admin:all" },
  { to: "/teams", label: "Teams", permission: "admin:all" },
  { to: "/roles", label: "Roles", permission: "admin:all" },
];

export default function Layout() {
  const { user, logout, hasPermission } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const visibleNav = navItems.filter((item) => !item.permission || hasPermission(item.permission));

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
              {item.label}
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
