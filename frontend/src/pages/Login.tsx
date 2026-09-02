import { useState } from "react";
import { useNavigate, Navigate, Link } from "react-router-dom";
import { useAuth } from "@/store/auth";
import { APP_NAME, getBrandMarkUrl } from "@/config";
import { BrandLogo } from "@/components/BrandLogo";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [passwordVisible, setPasswordVisible] = useState(false);
  const [logoFailed, setLogoFailed] = useState(false);
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();

  if (user) return <Navigate to="/dashboard" replace />;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    try {
      await login(email, password);
      sessionStorage.setItem("loginTransition", "1");
      navigate("/dashboard");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Login failed");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#01184e] dark:bg-gray-800 text-white">
        Loading...
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-[#01184e] dark:bg-gray-800">
      {/* Left: logo, full height, 50% opacity */}
      <div
        className="hidden md:flex w-1/2 min-h-screen items-center justify-center pl-8 pr-4 py-12 pointer-events-none shrink-0"
        aria-hidden
      >
        {logoFailed ? (
          <div className="text-white/40 text-6xl font-bold tracking-tight select-none">{APP_NAME}</div>
        ) : (
          <img
            src={getBrandMarkUrl()}
            alt=""
            className="h-3/4 max-h-[70vh] w-auto max-w-full object-contain object-center opacity-60"
            onError={() => setLogoFailed(true)}
          />
        )}
      </div>

      {/* Right: login modal */}
      <div className="flex-1 min-h-screen flex items-center justify-center p-6 md:p-10 lg:p-12">
        <div className="w-full max-w-md rounded-2xl bg-white dark:bg-gray-800/95 shadow-2xl border border-gray-100 dark:border-gray-700 p-8 sm:p-10">
          <div className="flex items-center gap-3 mb-8">
            <BrandLogo variant="login" />
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
              {APP_NAME}
            </h1>
          </div>
          <p className="text-gray-500 dark:text-gray-400 text-sm sm:text-base mb-1">Welcome back</p>
          <h2 className="text-xl sm:text-2xl font-semibold text-gray-800 dark:text-gray-100 mb-8">
            Sign in to your account
          </h2>
          <form onSubmit={handleSubmit} className="space-y-6">
            {err && (
              <div
                role="alert"
                className="text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl px-4 py-3"
              >
                {err}
              </div>
            )}
            <div>
              <label
                htmlFor="login-email"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
              >
                Email
              </label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#01184e]/40 focus:border-[#01184e] dark:focus:ring-[#01184e]/50 transition-shadow"
                placeholder="you@company.com"
                required
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-2">
                <label
                  htmlFor="login-password"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  Password
                </label>
                <Link to="/forgot-password" className="text-xs font-medium text-primary hover:underline" tabIndex={-1}>
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <input
                  id="login-password"
                  type={passwordVisible ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-3 pr-12 rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-[#01184e]/40 focus:border-[#01184e] dark:focus:ring-[#01184e]/50 transition-shadow"
                  placeholder="Enter your password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setPasswordVisible((v) => !v)}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-[#01184e]/30 focus:ring-offset-0 transition-colors active:scale-95"
                  aria-label={passwordVisible ? "Hide password" : "Show password"}
                  tabIndex={-1}
                >
                  <span className="sr-only">{passwordVisible ? "Hide password" : "Show password"}</span>
                  {passwordVisible ? (
                    <svg
                      className="w-5 h-5 animate-icon-pop"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.066 5.501m-12.054-1L21 21" />
                    </svg>
                  ) : (
                    <svg
                      className="w-5 h-5 animate-icon-pop"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                      aria-hidden
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
            <button
              type="submit"
              className="w-full py-3.5 rounded-xl font-semibold text-white bg-[#01184e] hover:bg-[#032a75] dark:bg-[#01184e] dark:hover:bg-[#032a75] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#01184e] transition-colors shadow-md hover:shadow-lg"
            >
              Sign in
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
