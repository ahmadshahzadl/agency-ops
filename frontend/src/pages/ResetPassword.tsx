import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { resetPassword } from "@/api/auth";
import { APP_NAME } from "@/config";
import { BrandLogo } from "@/components/BrandLogo";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    if (password.length < 8) {
      setErr("Password must be at least 8 characters.");
      return;
    }
    if (password !== confirm) {
      setErr("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await resetPassword(token, password);
      setDone(true);
      window.setTimeout(() => navigate("/login"), 2500);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Reset failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#01184e] dark:bg-gray-800 p-6">
      <div className="w-full max-w-md rounded-2xl bg-white dark:bg-gray-800/95 shadow-2xl border border-gray-100 dark:border-gray-700 p-8 sm:p-10">
        <div className="flex items-center gap-3 mb-8">
          <BrandLogo variant="login" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">{APP_NAME}</h1>
        </div>
        {done ? (
          <>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-3">Password updated ✓</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">Taking you to sign in…</p>
          </>
        ) : !token ? (
          <>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-3">Invalid link</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">This reset link is malformed or incomplete.</p>
            <Link to="/forgot-password" className="inline-block mt-6 text-sm font-medium text-primary hover:underline">
              Request a new link
            </Link>
          </>
        ) : (
          <>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-6">Choose a new password</h2>
            <form onSubmit={handleSubmit} className="space-y-5">
              {err && (
                <div role="alert" className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
                  {err}
                </div>
              )}
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#01184e]/40 focus:border-[#01184e]"
                placeholder="New password (min 8 characters)"
                required
                autoFocus
              />
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#01184e]/40 focus:border-[#01184e]"
                placeholder="Confirm new password"
                required
              />
              <button
                type="submit"
                disabled={busy}
                className="w-full py-3 rounded-xl font-semibold text-white bg-[#01184e] hover:bg-[#032a75] disabled:opacity-60 transition-colors shadow-md"
              >
                {busy ? "Updating…" : "Update password"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
