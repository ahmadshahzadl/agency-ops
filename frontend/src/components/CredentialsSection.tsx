import { useEffect, useState } from "react";
import { useAuth } from "@/store/auth";
import {
  listCredentials, createCredential, deleteCredential, revealCredential,
  type Credential,
} from "@/api/credentials";

/** Encrypted per-project credentials. Secrets stay masked; Reveal is a
 * server call that lands in the activity log. Rendered only for holders
 * of credentials:read. */
export function CredentialsSection({ projectId }: { projectId?: string }) {
  const { hasPermission } = useAuth();
  const canRead = hasPermission("credentials:read") || hasPermission("admin:all");
  const canWrite = hasPermission("credentials:write") || hasPermission("admin:all");

  const [items, setItems] = useState<Credential[]>([]);
  const [revealed, setRevealed] = useState<Record<string, string>>({});
  const [adding, setAdding] = useState(false);
  const [form, setForm] = useState({ label: "", username: "", secret: "", url: "", notes: "" });
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  const load = () => {
    if (!projectId) return;
    listCredentials(projectId).then(setItems).catch(() => setItems([]));
  };
  useEffect(load, [projectId]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => setRevealed({}), [projectId]); // drop plaintext when switching projects

  if (!canRead || !projectId) return null;

  const copy = async (id: string, text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(id);
      window.setTimeout(() => setCopied((c) => (c === id ? null : c)), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  const reveal = async (c: Credential) => {
    try {
      const r = await revealCredential(c.id);
      setRevealed((m) => ({ ...m, [c.id]: r.secret }));
      // Auto-hide after 60s so secrets don't linger on screen
      window.setTimeout(() => setRevealed((m) => {
        const { [c.id]: _gone, ...rest } = m;
        return rest;
      }), 60_000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reveal");
    }
  };

  const save = async () => {
    setError(null);
    try {
      await createCredential({
        project_id: projectId,
        label: form.label.trim(),
        secret: form.secret,
        username: form.username.trim() || null,
        url: form.url.trim() || null,
        notes: form.notes.trim() || null,
      });
      setForm({ label: "", username: "", secret: "", url: "", notes: "" });
      setAdding(false);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    }
  };

  const inputClass = "w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm";

  return (
    <div className="mt-4 rounded-xl border border-gray-200 dark:border-gray-600 p-3">
      <div className="flex items-center justify-between">
        <p className="text-[11px] uppercase tracking-wide text-gray-400">
          🔐 Credentials — encrypted; every reveal is logged
        </p>
        {canWrite && !adding && (
          <button onClick={() => setAdding(true)} className="text-xs font-medium text-primary hover:underline">+ Add credential</button>
        )}
      </div>
      {error && <p className="mt-2 text-xs text-red-500">{error}</p>}

      <div className="mt-2 space-y-2">
        {items.map((c) => (
          <div key={c.id} className="rounded-lg border border-gray-100 dark:border-gray-700 px-3 py-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium text-sm text-gray-800 dark:text-gray-100">{c.label}</span>
              {c.url && (
                <a href={c.url.startsWith("http") ? c.url : `https://${c.url}`} target="_blank" rel="noreferrer" className="text-xs text-primary hover:underline truncate max-w-[180px]">{c.url}</a>
              )}
              {canWrite && (
                <button
                  onClick={() => { if (window.confirm(`Delete credential "${c.label}"?`)) deleteCredential(c.id).then(load).catch(() => {}); }}
                  className="ml-auto text-xs text-red-400 hover:text-red-600"
                >
                  ✕
                </button>
              )}
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
              {c.username && (
                <span className="inline-flex items-center gap-1.5">
                  <span className="text-gray-400">user:</span>
                  <span className="font-mono">{c.username}</span>
                  <button onClick={() => copy(`u-${c.id}`, c.username!)} className="text-primary hover:underline">{copied === `u-${c.id}` ? "copied" : "copy"}</button>
                </span>
              )}
              <span className="inline-flex items-center gap-1.5">
                <span className="text-gray-400">secret:</span>
                {revealed[c.id] ? (
                  <>
                    <span className="font-mono break-all">{revealed[c.id]}</span>
                    <button onClick={() => copy(`s-${c.id}`, revealed[c.id])} className="text-primary hover:underline">{copied === `s-${c.id}` ? "copied" : "copy"}</button>
                    <button onClick={() => setRevealed((m) => { const { [c.id]: _gone, ...rest } = m; return rest; })} className="text-gray-400 hover:underline">hide</button>
                  </>
                ) : (
                  <>
                    <span className="font-mono tracking-wider">••••••••</span>
                    <button onClick={() => reveal(c)} className="text-primary hover:underline">reveal</button>
                  </>
                )}
              </span>
            </div>
            {c.notes && <p className="mt-1 text-xs text-gray-400">{c.notes}</p>}
          </div>
        ))}
        {items.length === 0 && !adding && (
          <p className="text-xs text-gray-400">No credentials stored for this project.</p>
        )}
      </div>

      {adding && (
        <div className="mt-2 rounded-lg border border-gray-200 dark:border-gray-600 p-2 space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <input autoFocus className={inputClass} placeholder="Label * (e.g. cPanel — client hosting)" value={form.label} onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))} />
            <input className={inputClass} placeholder="URL (optional)" value={form.url} onChange={(e) => setForm((f) => ({ ...f, url: e.target.value }))} />
            <input className={inputClass} placeholder="Username (optional)" autoComplete="off" value={form.username} onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))} />
            <input type="password" className={inputClass} placeholder="Secret *" autoComplete="new-password" value={form.secret} onChange={(e) => setForm((f) => ({ ...f, secret: e.target.value }))} />
          </div>
          <input className={inputClass} placeholder="Notes (optional — e.g. which environment, 2FA owner)" value={form.notes} onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))} />
          <div className="flex justify-end gap-2">
            <button onClick={() => { setAdding(false); setError(null); }} className="text-sm text-gray-500 hover:text-gray-800">Cancel</button>
            <button onClick={save} disabled={!form.label.trim() || !form.secret} className="px-3 py-1.5 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50">Save encrypted</button>
          </div>
        </div>
      )}
    </div>
  );
}
