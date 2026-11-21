import { useEffect, useMemo, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/store/auth";
import { getConsentInfo, decideConsent, type ConsentInfo } from "@/api/connector";

const CAN = [
  "Read leads, clients, projects, boards, tasks, quotes, agreements, letters, meetings, invoices and hours, limited to what your role can see",
  "Create and edit leads, quotes, projects, milestones, boards, tasks, notes and time entries",
  "Draft and edit agreements and letters",
];
const CANNOT = [
  "Send any email (quotes, letters, agreements, invoices). You press Send in the app",
  "Issue letters, sign or terminate agreements, or accept/reject quotes",
  "Delete anything",
  "See the credentials vault, expenses, payroll or private messages",
  "Change users, roles or teams",
];

/** OAuth consent for the Claude connector: /oauth/consent?client_id=...&redirect_uri=...&code_challenge=... */
export default function ConnectorConsent() {
  const { user, loading } = useAuth();
  const location = useLocation();
  const params = useMemo(() => Object.fromEntries(new URLSearchParams(location.search)), [location.search]);
  const [info, setInfo] = useState<ConsentInfo | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!user || user.is_client) return;
    getConsentInfo(params.client_id || "", params.redirect_uri || "")
      .then(setInfo)
      .catch((e) => setErr(e instanceof Error ? e.message : "This connection request is not valid."));
  }, [user, params.client_id, params.redirect_uri]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-[#01184e] text-white">Loading...</div>;
  }
  if (!user) {
    sessionStorage.setItem("postLoginRedirect", `/oauth/consent${location.search}`);
    return <Navigate to="/login" replace />;
  }

  const decide = async (approve: boolean) => {
    setBusy(true);
    setErr(null);
    try {
      const to = await decideConsent(
        {
          client_id: params.client_id || "",
          redirect_uri: params.redirect_uri || "",
          code_challenge: params.code_challenge || "",
          code_challenge_method: params.code_challenge_method || "",
          state: params.state || "",
          scope: params.scope || "",
        },
        approve,
      );
      sessionStorage.removeItem("postLoginRedirect");
      window.location.href = to;
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not complete the connection");
      setBusy(false);
    }
  };

  const blocked = user.is_client ? "Client portal accounts cannot connect Claude." : info?.blocked_reason;

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#01184e] dark:bg-gray-900 p-6">
      <div className="w-full max-w-lg rounded-2xl bg-white dark:bg-gray-800 shadow-2xl border border-gray-100 dark:border-gray-700 p-8">
        <h1 className="text-xl font-semibold text-gray-900 dark:text-white">
          Connect {info?.client_name || "Claude"} to Fuorix?
        </h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Signed in as <strong className="text-gray-800 dark:text-gray-200">{user.email}</strong>. Claude will act as you,
          with your role's access, and everything it changes is logged as "via Claude".
        </p>

        {err && <p role="alert" className="mt-4 text-sm text-red-600 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2">{err}</p>}
        {blocked && <p role="alert" className="mt-4 text-sm text-amber-800 dark:text-amber-200 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-2">{blocked}</p>}

        <div className="mt-5 grid gap-4 sm:grid-cols-2 text-sm">
          <div>
            <p className="font-medium text-gray-900 dark:text-white mb-1.5">Claude can</p>
            <ul className="space-y-1.5 text-gray-700 dark:text-gray-300 list-disc pl-4">{CAN.map((c) => <li key={c}>{c}</li>)}</ul>
          </div>
          <div>
            <p className="font-medium text-gray-900 dark:text-white mb-1.5">Claude cannot</p>
            <ul className="space-y-1.5 text-gray-700 dark:text-gray-300 list-disc pl-4">{CANNOT.map((c) => <li key={c}>{c}</li>)}</ul>
          </div>
        </div>

        <p className="mt-4 text-xs text-gray-500 dark:text-gray-400">
          You can disconnect any time in Settings → Connected apps. Signing out everywhere also disconnects it.
        </p>

        <div className="mt-6 flex justify-end gap-2">
          <button type="button" onClick={() => decide(false)} disabled={busy || !!err}
            className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 text-sm font-medium hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50">
            Cancel
          </button>
          <button type="button" onClick={() => decide(true)} disabled={busy || !!err || !!blocked || !info}
            className="px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50">
            {busy ? "Connecting…" : "Allow"}
          </button>
        </div>
      </div>
    </div>
  );
}
