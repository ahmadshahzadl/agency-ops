import { useState } from "react";
import { Link } from "react-router-dom";
import { forgotPassword } from "@/api/auth";
import { APP_NAME } from "@/config";
import { BrandLogo } from "@/components/BrandLogo";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await forgotPassword(email);
    } catch {
      // Same UX either way — no user enumeration
    }
    setSent(true);
    setBusy(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#01184e] dark:bg-gray-800 p-6">
      <div className="w-full max-w-md rounded-2xl bg-white dark:bg-gray-800/95 shadow-2xl border border-gray-100 dark:border-gray-700 p-8 sm:p-10">
        <div className="flex items-center gap-3 mb-8">
          <BrandLogo variant="login" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">{APP_NAME}</h1>
        </div>
        {sent ? (
          <>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-3">Check your email</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              If <b>{email}</b> is registered, a password reset link is on its way. The link is valid for 1 hour.
            </p>
            <Link to="/login" className="inline-block mt-6 text-sm font-medium text-primary hover:underline">
              ← Back to sign in
            </Link>
          </>
        ) : (
          <>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-2">Forgot your password?</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">Enter your email and we'll send you a reset link.</p>
            <form onSubmit={handleSubmit} className="space-y-5">
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-[#01184e]/40 focus:border-[#01184e]"
                placeholder="you@company.com"
                required
                autoFocus
              />
              <button
                type="submit"
                disabled={busy}
                className="w-full py-3 rounded-xl font-semibold text-white bg-[#01184e] hover:bg-[#032a75] disabled:opacity-60 transition-colors shadow-md"
              >
                {busy ? "Sending…" : "Send reset link"}
              </button>
            </form>
            <Link to="/login" className="inline-block mt-5 text-sm font-medium text-primary hover:underline">
              ← Back to sign in
            </Link>
          </>
        )}
      </div>
    </div>
  );
}
