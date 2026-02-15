import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import type { User } from "@/api/auth";
import { getMe, logout as apiLogout } from "@/api/auth";
import { getToken } from "@/api/client";

interface AuthState {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hasPermission: (code: string) => boolean;
  refetch: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const u = await getMe();
      setUser(u);
      setError(null);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refetch();
  }, [refetch]);

  const login = useCallback(
    async (email: string, password: string) => {
      setError(null);
      const { login: doLogin } = await import("@/api/auth");
      await doLogin(email, password);
      await refetch();
    },
    [refetch]
  );

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  const hasPermission = useCallback(
    (code: string) => {
      if (!user) return false;
      return user.permissions.includes(code) || user.permissions.includes("admin:all");
    },
    [user]
  );

  return (
    <AuthContext.Provider
      value={{ user, loading, error, login, logout, hasPermission, refetch }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
