import { useState, useEffect } from "react";
import { useAuth } from "@/store/auth";
import { updateProfile } from "@/api/auth";
import { fetchServerVersion, compareVersions } from "@/api/version";
import { APP_VERSION } from "@/config";
import { setTheme, getStoredTheme, type ThemeValue } from "@/lib/theme";

const inputClass =
  "w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-primary/20 focus:border-primary";
const labelClass = "block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1";

export default function ProfilePage() {
  const { user, refetch, hasPermission } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  const [contactPhone, setContactPhone] = useState(user?.phone ?? "");
  const [contactJobTitle, setContactJobTitle] = useState(user?.job_title ?? "");
  const [contactSaving, setContactSaving] = useState(false);
  const [contactMessage, setContactMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  const [themeValue, setThemeValue] = useState<ThemeValue>(getStoredTheme());
  const [updateCheckStatus, setUpdateCheckStatus] = useState<
    "idle" | "checking" | "latest" | "available" | "error"
  >("idle");
  const [serverVersion, setServerVersion] = useState<string | null>(null);

  useEffect(() => {
    setFullName(user?.full_name ?? "");
    setContactPhone(user?.phone ?? "");
    setContactJobTitle(user?.job_title ?? "");
  }, [user?.full_name, user?.phone, user?.job_title]);

  const initial = (user?.full_name || user?.email || "?").charAt(0).toUpperCase();
  const roleLabel = user?.roles?.length
    ? user.roles.map((r) => r.replace(/_/g, " ")).join(", ")
    : "—";
  const canEditContact = hasPermission("admin:all") || (user?.roles?.includes("manager") ?? false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setMessage(null);
    if (newPassword && newPassword !== confirmPassword) {
      setMessage({ type: "err", text: "New password and confirm do not match." });
      return;
    }
    if (newPassword && !currentPassword) {
      setMessage({ type: "err", text: "Enter current password to change password." });
      return;
    }
    setSaving(true);
    try {
      const payload: { full_name?: string; current_password?: string; new_password?: string } = {
        full_name: fullName || undefined,
      };
      if (newPassword) {
        payload.current_password = currentPassword;
        payload.new_password = newPassword;
      }
      await updateProfile(payload);
      await refetch();
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setMessage({ type: "ok", text: "Profile updated." });
    } catch (err) {
      setMessage({
        type: "err",
        text: err instanceof Error ? err.message : "Failed to update profile",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleContactSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canEditContact) return;
    setContactMessage(null);
    setContactSaving(true);
    try {
      await updateProfile({ phone: contactPhone || null, job_title: contactJobTitle || null });
      await refetch();
      setContactMessage({ type: "ok", text: "Contact details updated." });
    } catch (err) {
      setContactMessage({
        type: "err",
        text: err instanceof Error ? err.message : "Failed to update contact",
      });
    } finally {
      setContactSaving(false);
    }
  };

  const handleThemeChange = (value: ThemeValue) => {
    setThemeValue(value);
    setTheme(value);
  };

  const handleCheckForUpdates = async () => {
    setUpdateCheckStatus("checking");
    setServerVersion(null);
    try {
      const { version } = await fetchServerVersion();
      setServerVersion(version);
      const cmp = compareVersions(version, APP_VERSION);
      if (cmp > 0) {
        setUpdateCheckStatus("available");
      } else {
        setUpdateCheckStatus("latest");
      }
    } catch {
      setUpdateCheckStatus("error");
    }
  };

  return (
    <div className="h-full min-h-0 flex gap-4 -m-6 p-6 overflow-hidden">
      {/* Left: avatar, name, email, role, contact — wider and larger */}
      <section className="w-80 min-w-[18rem] shrink-0 flex flex-col">
        <div className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 shadow-sm p-6 flex flex-col items-center text-center h-full">
          <div
            className="w-32 h-32 rounded-full flex items-center justify-center text-white text-4xl font-semibold shrink-0 bg-primary"
            aria-hidden
          >
            {initial}
          </div>
          <h2 className="mt-5 text-xl font-semibold text-gray-900 dark:text-white truncate w-full">
            {user?.full_name || "No name set"}
          </h2>
          <p className="mt-2 text-gray-600 dark:text-gray-400 truncate w-full" title={user?.email ?? ""}>
            {user?.email}
          </p>
          <div className="mt-5 pt-5 border-t border-gray-100 dark:border-gray-600 w-full">
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Role</p>
            <p className="mt-1.5 text-gray-700 dark:text-gray-300 truncate w-full" title={roleLabel}>
              {roleLabel}
            </p>
          </div>
          <div className="mt-5 pt-5 border-t border-gray-100 dark:border-gray-600 w-full text-left">
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">Contact</p>
            <p className="mt-1.5 text-gray-700 dark:text-gray-300 truncate w-full" title={user?.phone ?? ""}>
              {user?.phone || "—"}
            </p>
            <p className="mt-1 text-gray-700 dark:text-gray-300 truncate w-full" title={user?.job_title ?? ""}>
              {user?.job_title || "—"}
            </p>
          </div>
        </div>
      </section>

      {/* Right: 2 cols — row1 (Profile | Contact) takes space, row2 (Appearance | Updates) minimal height */}
      <div className="flex-1 min-w-0 min-h-0 grid grid-cols-2 grid-rows-[1fr_auto] gap-4 overflow-hidden">
        {/* Profile — half width */}
        <section className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 shadow-sm p-4 min-h-0 flex flex-col overflow-auto">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-3">Profile</h2>
          <form onSubmit={handleSubmit} className="space-y-3 flex-1 min-h-0 flex flex-col">
            <div>
              <label className={labelClass}>Full name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className={inputClass}
                placeholder="Your name"
              />
            </div>
            <div>
              <label className={labelClass}>Change password</label>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Leave blank to keep current.</p>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="text-xs text-gray-600 dark:text-gray-400 mb-0.5 block">Current</label>
                  <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} className={inputClass} placeholder="Current" />
                </div>
                <div>
                  <label className="text-xs text-gray-600 dark:text-gray-400 mb-0.5 block">New</label>
                  <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className={inputClass} placeholder="New" />
                </div>
                <div>
                  <label className="text-xs text-gray-600 dark:text-gray-400 mb-0.5 block">Confirm</label>
                  <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className={inputClass} placeholder="Confirm" />
                </div>
              </div>
            </div>
            {message && (
              <p className={message.type === "ok" ? "text-green-600 dark:text-green-400 text-xs" : "text-red-600 dark:text-red-400 text-xs"}>{message.text}</p>
            )}
            <button type="submit" disabled={saving} className="px-3 py-1.5 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50 w-fit">
              {saving ? "Saving…" : "Save changes"}
            </button>
          </form>
        </section>

        {/* Contact information — half width */}
        <section className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 shadow-sm p-4 min-h-0 flex flex-col overflow-auto">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-2">Contact information</h2>
          <p className="text-xs text-gray-600 dark:text-gray-400 mb-3">
            Admins and managers can edit. View on the left.
          </p>
          {canEditContact ? (
            <form onSubmit={handleContactSubmit} className="space-y-3 flex-1 min-h-0 flex flex-col">
              <div>
                <label className={labelClass}>Phone</label>
                <input type="tel" value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} className={inputClass} placeholder="Phone number" />
              </div>
              <div>
                <label className={labelClass}>Job title</label>
                <input value={contactJobTitle} onChange={(e) => setContactJobTitle(e.target.value)} className={inputClass} placeholder="e.g. Developer, PM" />
              </div>
              {contactMessage && (
                <p className={contactMessage.type === "ok" ? "text-green-600 dark:text-green-400 text-xs" : "text-red-600 dark:text-red-400 text-xs"}>{contactMessage.text}</p>
              )}
              <button type="submit" disabled={contactSaving} className="px-3 py-1.5 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50 w-fit">
                {contactSaving ? "Saving…" : "Save contact details"}
              </button>
            </form>
          ) : (
            <p className="text-xs text-gray-500 dark:text-gray-400">Ask an admin or manager to update.</p>
          )}
        </section>

        {/* Appearance — half width, compact */}
        <section className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 shadow-sm px-4 py-3 flex flex-row items-center justify-between gap-3 shrink-0">
          <div>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Appearance</h2>
            <p className="text-xs text-gray-600 dark:text-gray-400">Light, dark, or system.</p>
          </div>
          <select
            value={themeValue}
            onChange={(e) => handleThemeChange(e.target.value as ThemeValue)}
            className="px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm focus:ring-2 focus:ring-primary/20 shrink-0"
          >
            <option value="light">Light</option>
            <option value="dark">Dark</option>
            <option value="system">System</option>
          </select>
        </section>

        {/* Updates — half width, compact */}
        <section className="rounded-xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 shadow-sm px-4 py-3 flex flex-col gap-2 shrink-0 min-h-0 overflow-auto">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Updates</h2>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={handleCheckForUpdates}
              disabled={updateCheckStatus === "checking"}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-700 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50"
            >
              {updateCheckStatus === "checking" ? (
                <>
                  <span className="inline-block w-3.5 h-3.5 border-2 border-gray-300 border-t-primary rounded-full animate-spin" />
                  Checking…
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Check for updates
                </>
              )}
            </button>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              Installed: <strong>{APP_VERSION}</strong>
            </span>
          </div>
          {updateCheckStatus === "latest" && (
            <p className="mt-2 text-xs text-green-600 dark:text-green-400">
              Latest version.
              {serverVersion != null && ` (Server: ${serverVersion})`}
            </p>
          )}
          {updateCheckStatus === "available" && serverVersion && (
            <div className="mt-2 p-2 rounded-lg bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800">
              <p className="text-xs text-amber-800 dark:text-amber-200 font-medium">
                Update available (server: {serverVersion}).
              </p>
              <button type="button" onClick={() => window.location.reload()} className="mt-1.5 px-2 py-1 rounded-lg bg-amber-600 text-white text-xs font-medium hover:bg-amber-700">
                Refresh now
              </button>
            </div>
          )}
          {updateCheckStatus === "error" && (
            <p className="mt-2 text-xs text-red-600 dark:text-red-400">Could not check. Server may be unreachable.</p>
          )}
        </section>
      </div>
    </div>
  );
}
