import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/store/auth";
import Layout from "@/layouts/Layout";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Leads from "@/pages/Leads";
import Clients from "@/pages/Clients";
import Projects from "@/pages/Projects";
import Tasks from "@/pages/Tasks";
import Meetings from "@/pages/Meetings";
import Invoices from "@/pages/Invoices";
import Expenses from "@/pages/Expenses";
import Analytics from "@/pages/Analytics";
import TeamActivity from "@/pages/TeamActivity";
import Users from "@/pages/Users";
import Teams from "@/pages/Teams";
import Roles from "@/pages/Roles";
import Profile from "@/pages/Profile";
import Announcements from "@/pages/Announcements";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f5f6f8] text-rich-cerulean">
        Loading...
      </div>
    );
  }
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="leads" element={<Leads />} />
        <Route path="clients" element={<Clients />} />
        <Route path="projects" element={<Projects />} />
        <Route path="tasks" element={<Tasks />} />
        <Route path="meetings" element={<Meetings />} />
        <Route path="invoices" element={<Invoices />} />
        <Route path="expenses" element={<Expenses />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="team-activity" element={<TeamActivity />} />
        <Route path="users" element={<Users />} />
        <Route path="teams" element={<Teams />} />
        <Route path="roles" element={<Roles />} />
        <Route path="profile" element={<Profile />} />
        <Route path="announcements" element={<Announcements />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
