import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "@/store/auth";
import { APP_NAME } from "@/config";
import { BrandLogo } from "@/components/BrandLogo";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();

  if (user) return <Navigate to="/dashboard" replace />;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Login failed");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#f5f6f8] text-rich-cerulean">
        Loading...
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f5f6f8]">
      <div className="w-full max-w-sm rounded-xl bg-white border border-gray-100 p-8 shadow-lg">
        <div className="flex items-center gap-2 mb-6">
          <BrandLogo variant="login" />
          <h1 className="text-2xl font-bold text-gray-900">{APP_NAME}</h1>
        </div>
        <h2 className="text-lg font-semibold text-gray-800 mb-6">Sign in</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          {err && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {err}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-rich-cerulean/30 focus:border-rich-cerulean"
              placeholder="admin@example.com"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-200 bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-rich-cerulean/30 focus:border-rich-cerulean"
              required
            />
          </div>
          <button
            type="submit"
            className="w-full py-3 rounded-lg font-semibold text-white bg-rich-cerulean hover:bg-steel-blue transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-rich-cerulean"
          >
            Sign in
          </button>
        </form>
      </div>
    </div>
  );
}
