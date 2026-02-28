import { useState } from "react";
import { useAuth } from "@/store/auth";
import { updateProfile } from "@/api/auth";

export default function ProfilePage() {
  const { user, refetch } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name ?? "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);

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
        full_name: fullName || null,
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

  return (
    <div>
      <h1 className="text-2xl font-semibold text-white mb-6">My profile</h1>
      <form onSubmit={handleSubmit} className="max-w-md space-y-4">
        <div>
          <label className="block text-sm text-slate-400 mb-1">Email</label>
          <input
            type="email"
            value={user?.email ?? ""}
            disabled
            className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-slate-400 cursor-not-allowed"
          />
          <p className="text-xs text-slate-500 mt-1">Email cannot be changed.</p>
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-1">Full name</label>
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
            placeholder="Your name"
          />
        </div>
        <div className="pt-4 border-t border-slate-700">
          <h2 className="text-lg font-medium text-white mb-2">Change password</h2>
          <div className="space-y-3">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Current password</label>
              <input
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                placeholder="Leave blank to keep current"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">New password</label>
              <input
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
                placeholder="Leave blank to keep current"
              />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Confirm new password</label>
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-white"
              />
            </div>
          </div>
        </div>
        {message && (
          <p className={message.type === "ok" ? "text-green-400" : "text-red-400"}>{message.text}</p>
        )}
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save changes"}
        </button>
      </form>
    </div>
  );
}
