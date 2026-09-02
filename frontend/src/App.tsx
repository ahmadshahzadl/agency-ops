import { BrowserRouter, HashRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/store/auth";
import { ModalProvider } from "@/contexts/ModalContext";
import Layout from "@/layouts/Layout";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Leads from "@/pages/Leads";
import Clients from "@/pages/Clients";
import Projects from "@/pages/Projects";
import Tasks from "@/pages/Tasks";
import Boards from "@/pages/Boards";
import Timesheet from "@/pages/Timesheet";
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
import Messages from "@/pages/Messages";
import PublicStatus from "@/pages/PublicStatus";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#01184e] dark:bg-gray-800 text-white">
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
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route path="/status/:token" element={<PublicStatus />} />
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
        <Route path="boards" element={<Boards />} />
        <Route path="timesheet" element={<Timesheet />} />
        <Route path="meetings" element={<Meetings />} />
        <Route path="invoices" element={<Invoices />} />
        <Route path="expenses" element={<Expenses />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="team-activity" element={<TeamActivity />} />
        <Route path="users" element={<Users />} />
        <Route path="teams" element={<Teams />} />
        <Route path="roles" element={<Roles />} />
        <Route path="profile" element={<Profile />} />
        <Route path="messages" element={<Messages />} />
        <Route path="announcements" element={<Announcements />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

/** Use HashRouter when loaded via file:// (Electron packaged app); BrowserRouter for web. */
const isFileProtocol = typeof window !== "undefined" && window.location?.protocol === "file:";
const Router = isFileProtocol ? HashRouter : BrowserRouter;

export default function App() {
  return (
    <Router>
      <AuthProvider>
        <ModalProvider>
          <AppRoutes />
        </ModalProvider>
      </AuthProvider>
    </Router>
  );
}
