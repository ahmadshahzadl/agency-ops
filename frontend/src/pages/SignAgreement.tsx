import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiFetch, API_BASE } from "@/api/client";
import { getBrandMarkUrl } from "@/config";

interface PublicAgreement {
  number: string;
  title: string;
  agreement_type: string;
  type_label: string;
  status: string;
  company_name: string;
  client_name: string | null;
  effective_date: string | null;
  valid_until: string | null;
  contract_value: string | null;
  currency: string;
  clauses: { heading: string; body: string }[];
  accepted_at: string | null;
  accepted_by_name: string | null;
  countersigned_at: string | null;
  countersigned_by_name: string | null;
  can_sign: boolean;
}

export default function SignAgreement() {
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<PublicAgreement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [title, setTitle] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [showDecline, setShowDecline] = useState(false);
  const [declineReason, setDeclineReason] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const load = () => {
    if (!token) return;
    apiFetch<PublicAgreement>(`/api/v1/public/agreements/${token}`).then(setData).catch(() => setError("This signing link is not valid."));
  };
  useEffect(load, [token]);

  const pdfUrl = `${API_BASE}/api/v1/public/agreements/${token}/pdf`;

  const sign = async () => {
    setFormError(null);
    if (name.trim().split(/\s+/).length < 2) { setFormError("Type your full name as it should appear on the agreement."); return; }
    if (!agreed) { setFormError("Tick the box to confirm you have read and agree to the terms."); return; }
    setBusy(true);
    try {
      const r = await apiFetch<PublicAgreement>(`/api/v1/public/agreements/${token}/accept`, {
        method: "POST",
        body: JSON.stringify({ signer_name: name.trim(), signer_email: email.trim() || null, signer_title: title.trim() || null, agreed: true }),
      });
      setData(r);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Could not record your signature. Please try again.");
    } finally { setBusy(false); }
  };

  const decline = async () => {
    setBusy(true);
    try {
      const r = await apiFetch<PublicAgreement>(`/api/v1/public/agreements/${token}/decline`, { method: "POST", body: JSON.stringify({ reason: declineReason.trim() || null }) });
      setData(r);
      setShowDecline(false);
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Could not record your response.");
    } finally { setBusy(false); }
  };

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-[#01184e] text-white p-6 text-center">
        <img src={getBrandMarkUrl()} alt="" className="w-16 h-16 mb-4 opacity-90" />
        <h1 className="text-xl font-semibold">This link is not valid</h1>
        <p className="text-white/60 mt-2 text-sm">It may have been replaced by a newer one. Reply to the email you received and we will send a fresh link.</p>
      </div>
    );
  }
  if (!data) return <div className="min-h-screen flex items-center justify-center bg-[#01184e] text-white">Loading…</div>;

  const fmt = (iso: string | null) => (iso ? new Date(iso).toLocaleString("en-GB", { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "");
  const fmtDate = (d: string | null) => (d ? new Date(`${d}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }) : "");

  const banner = (() => {
    switch (data.status) {
      case "signed":
        return { cls: "bg-green-50 border-green-200 text-green-800", text: `Signed by ${data.accepted_by_name} on ${fmt(data.accepted_at)}.${data.countersigned_at ? ` Countersigned by ${data.countersigned_by_name} for ${data.company_name} on ${fmt(data.countersigned_at)}.` : ` ${data.company_name} will countersign shortly.`} Your signed copy has been emailed to you.` };
      case "declined":
        return { cls: "bg-gray-50 border-gray-200 text-gray-700", text: "You declined this agreement. Nothing further is needed; we may be in touch to discuss changes." };
      case "expired":
      case "link_expired":
        return { cls: "bg-amber-50 border-amber-200 text-amber-800", text: "The signing deadline has passed. Reply to the email you received and we will send a new version." };
      case "terminated":
        return { cls: "bg-gray-50 border-gray-200 text-gray-700", text: "This agreement has been terminated." };
      default:
        return null;
    }
  })();

  return (
    <div className="min-h-screen bg-[#f4f6fa] text-gray-900">
      <header className="bg-[#01184e] text-white">
        <div className="max-w-3xl mx-auto px-5 py-5 flex items-center gap-3">
          <img src={getBrandMarkUrl()} alt="" className="w-9 h-9" />
          <div>
            <p className="font-semibold leading-tight">{data.company_name}</p>
            <p className="text-xs text-white/60">{data.type_label}</p>
          </div>
          <a href={pdfUrl} target="_blank" rel="noreferrer" className="ml-auto text-sm font-medium bg-white/10 hover:bg-white/20 px-3 py-1.5 rounded-lg">Download PDF</a>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-5 py-8 space-y-6">
        {banner && <div className={`rounded-xl border px-4 py-3 text-sm ${banner.cls}`}>{banner.text}</div>}

        <section className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
          <p className="text-xs uppercase tracking-wide text-gray-400">{data.number}</p>
          <h1 className="text-2xl font-semibold mt-1">{data.title}</h1>
          <dl className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
            <div><dt className="text-gray-400">Between</dt><dd className="font-medium">{data.company_name} and {data.client_name || "the Client"}</dd></div>
            {data.effective_date && <div><dt className="text-gray-400">Effective date</dt><dd className="font-medium">{fmtDate(data.effective_date)}</dd></div>}
            {data.contract_value && <div><dt className="text-gray-400">Value</dt><dd className="font-medium">{data.currency} {data.contract_value}</dd></div>}
            {data.valid_until && data.can_sign && <div><dt className="text-gray-400">Please sign by</dt><dd className="font-medium">{fmtDate(data.valid_until)}</dd></div>}
          </dl>
        </section>

        <section className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-5">
          {data.clauses.map((c, i) => (
            <div key={i}>
              <h2 className="font-semibold text-[#01184e]">{i + 1}. {c.heading}</h2>
              <p className="mt-1.5 text-sm leading-relaxed text-gray-700 whitespace-pre-wrap">{c.body}</p>
            </div>
          ))}
        </section>

        {data.can_sign && (
          <section className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
            <h2 className="text-lg font-semibold">Sign this agreement</h2>
            <p className="text-sm text-gray-500 mt-1">Type your name to sign electronically. We record your name, email, the time, and the network address you signed from, and email you the signed copy.</p>
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-gray-500 mb-1">Full name *</label>
                <input className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-[#01184e]/20 focus:border-[#01184e]" value={name} onChange={(e) => setName(e.target.value)} placeholder="As it should appear on the agreement" autoComplete="name" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Email</label>
                <input type="email" className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-[#01184e]/20 focus:border-[#01184e]" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Where to send your signed copy" autoComplete="email" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Title or role</label>
                <input className="w-full px-3 py-2 rounded-lg border border-gray-300 focus:ring-2 focus:ring-[#01184e]/20 focus:border-[#01184e]" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Founder, Director" autoComplete="organization-title" />
              </div>
            </div>
            <label className="mt-4 flex items-start gap-2 text-sm text-gray-700">
              <input type="checkbox" className="mt-0.5 rounded border-gray-300" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} />
              <span>I have read this {data.type_label.toLowerCase()} and agree to its terms on behalf of {data.client_name || "the Client"}. I understand that typing my name here has the same effect as a handwritten signature.</span>
            </label>
            {formError && <p className="mt-3 text-sm text-red-600">{formError}</p>}
            <div className="mt-5 flex items-center gap-3 flex-wrap">
              <button disabled={busy} onClick={sign} className="px-5 py-2.5 rounded-lg bg-[#01184e] text-white font-medium hover:bg-[#02225f] disabled:opacity-50">{busy ? "Signing…" : "Sign agreement"}</button>
              <button disabled={busy} onClick={() => setShowDecline((v) => !v)} className="text-sm text-gray-500 hover:text-gray-800">I do not agree</button>
            </div>
            {showDecline && (
              <div className="mt-4 rounded-lg border border-gray-200 p-3">
                <label className="block text-xs font-medium text-gray-500 mb-1">Tell us what you would like changed (optional)</label>
                <textarea rows={3} className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm" value={declineReason} onChange={(e) => setDeclineReason(e.target.value)} />
                <div className="mt-2 flex justify-end gap-2">
                  <button onClick={() => setShowDecline(false)} className="px-3 py-1.5 text-sm text-gray-600">Cancel</button>
                  <button disabled={busy} onClick={decline} className="px-3 py-1.5 rounded-lg bg-gray-800 text-white text-sm font-medium">Decline</button>
                </div>
              </div>
            )}
          </section>
        )}

        <p className="text-center text-xs text-gray-400 pb-6">Questions? Reply to the email this link came from.</p>
      </main>
    </div>
  );
}
