import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/store/auth";
import { useModal } from "@/contexts/ModalContext";
import { listClients, type Client } from "@/api/clients";
import {
  listLetters, listLetterTypes, getLetterTemplate, createLetter, updateLetter,
  deleteLetter, issueLetter, sendLetter, openLetterPdf, openBlankLetterhead,
  type Letter,
} from "@/api/letters";

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  issued: "bg-green-100 text-green-700",
};

export default function Letters() {
  const { user, hasPermission } = useAuth();
  const { showConfirm, showAlert } = useModal();
  const canWrite = hasPermission("letters:write");

  const [items, setItems] = useState<Letter[]>([]);
  const [types, setTypes] = useState<{ value: string; label: string }[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [modal, setModal] = useState<"new" | Letter | null>(null);
  const [form, setForm] = useState({
    letter_type: "general", subject: "", body: "", recipient_name: "", recipient_address: "",
    recipient_email: "", client_id: "", letter_date: "", signatory_name: "", signatory_title: "",
  });

  const load = useCallback(() => {
    listLetters({
      ...(statusFilter ? { status_filter: statusFilter } : {}),
      ...(typeFilter ? { letter_type: typeFilter } : {}),
    }).then(setItems).catch(() => setItems([]));
  }, [statusFilter, typeFilter]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    listLetterTypes().then(setTypes).catch(() => setTypes([]));
    listClients().then(setClients).catch(() => setClients([]));
  }, []);

  const typeLabel = (v: string) => types.find((t) => t.value === v)?.label ?? v;

  const applyTemplate = async (letterType: string, recipientName?: string, clientId?: string) => {
    try {
      const t = await getLetterTemplate({
        letter_type: letterType,
        recipient_name: recipientName || undefined,
        client_id: clientId || undefined,
      });
      setForm((f) => ({ ...f, letter_type: letterType, subject: t.subject || f.subject, body: t.body }));
    } catch {
      /* keep current text */
    }
  };

  const openNew = async () => {
    setForm({
      letter_type: "general", subject: "", body: "", recipient_name: "", recipient_address: "",
      recipient_email: "", client_id: "", letter_date: new Date().toISOString().slice(0, 10),
      signatory_name: user?.full_name || "", signatory_title: user?.job_title || "",
    });
    setModal("new");
    applyTemplate("general");
  };

  const openEdit = (l: Letter) => {
    setForm({
      letter_type: l.letter_type,
      subject: l.subject,
      body: l.body,
      recipient_name: l.recipient_name || "",
      recipient_address: l.recipient_address || "",
      recipient_email: l.recipient_email || "",
      client_id: l.client_id || "",
      letter_date: l.letter_date || "",
      signatory_name: l.signatory_name || "",
      signatory_title: l.signatory_title || "",
    });
    setModal(l);
  };

  const save = async () => {
    const payload = {
      letter_type: form.letter_type,
      subject: form.subject,
      body: form.body,
      recipient_name: form.recipient_name || null,
      recipient_address: form.recipient_address || null,
      recipient_email: form.recipient_email || null,
      client_id: form.client_id || null,
      letter_date: form.letter_date || null,
      signatory_name: form.signatory_name || null,
      signatory_title: form.signatory_title || null,
    };
    try {
      if (modal === "new") await createLetter(payload);
      else if (modal) await updateLetter(modal.id, payload);
      setModal(null);
      load();
    } catch (e) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    }
  };

  const act = async (fn: () => Promise<unknown>, successMsg?: string) => {
    try {
      await fn();
      load();
      if (successMsg) showAlert({ title: "Done", message: successMsg });
    } catch (e) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    }
  };

  const editable = modal === "new" || (modal !== null && modal.status === "draft");
  const inputClass = "w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <select className={`${inputClass} !w-auto`} value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
          <option value="">All types</option>
          {types.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
        <select className={`${inputClass} !w-auto`} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
          <option value="">All statuses</option>
          <option value="draft">draft</option>
          <option value="issued">issued</option>
        </select>
        <div className="ml-auto flex items-center gap-2">
          <button onClick={() => openBlankLetterhead().catch(() => showAlert({ title: "Error", message: "Could not load PDF" }))} className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 font-medium hover:border-primary hover:text-primary">
            Blank letterhead
          </button>
          {canWrite && (
            <button onClick={openNew} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover">
              New letter
            </button>
          )}
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-gray-400 border-b border-gray-100 dark:border-gray-700">
              <th className="px-4 py-2.5">Number</th>
              <th className="px-4 py-2.5">Subject</th>
              <th className="px-4 py-2.5">To</th>
              <th className="px-4 py-2.5">Type</th>
              <th className="px-4 py-2.5">Date</th>
              <th className="px-4 py-2.5">Status</th>
              <th className="px-4 py-2.5"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50 dark:divide-gray-700">
            {items.map((l) => (
              <tr key={l.id} className="text-gray-700 dark:text-gray-200 hover:bg-gray-50/70 dark:hover:bg-gray-700/40">
                <td className="px-4 py-2.5 whitespace-nowrap font-mono text-xs">{l.number}</td>
                <td className="px-4 py-2.5">
                  <button onClick={() => openEdit(l)} className="font-medium hover:text-primary text-left">{l.subject}</button>
                </td>
                <td className="px-4 py-2.5 text-gray-500">{l.recipient_name || l.client_name || "—"}</td>
                <td className="px-4 py-2.5 text-gray-500 text-xs">{typeLabel(l.letter_type)}</td>
                <td className="px-4 py-2.5 text-gray-500 text-xs whitespace-nowrap">{l.letter_date ?? "—"}</td>
                <td className="px-4 py-2.5">
                  <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${STATUS_STYLES[l.status] ?? ""}`}>{l.status}</span>
                </td>
                <td className="px-4 py-2.5 text-right whitespace-nowrap space-x-2">
                  <button onClick={() => openLetterPdf(l.id, l.number).catch(() => showAlert({ title: "Error", message: "Could not load PDF" }))} className="text-xs font-medium text-gray-500 hover:text-primary hover:underline">PDF</button>
                  {canWrite && l.status === "draft" && (
                    <>
                      <button onClick={() => act(() => issueLetter(l.id), "Letter issued — it is now a frozen record.")} className="text-xs font-medium text-green-600 hover:underline">Issue</button>
                      {(l.recipient_email || l.client_id) && (
                        <button onClick={() => act(() => sendLetter(l.id), "Letter issued and emailed with the PDF attached.")} className="text-xs font-medium text-primary hover:underline">Email</button>
                      )}
                      <button
                        onClick={() => showConfirm({
                          title: "Delete letter",
                          message: `Delete ${l.number}?`,
                          onConfirm: () => act(() => deleteLetter(l.id)),
                        })}
                        className="text-xs font-medium text-red-400 hover:text-red-600"
                      >
                        ✕
                      </button>
                    </>
                  )}
                  {canWrite && l.status === "issued" && (l.recipient_email || l.client_id) && (
                    <button onClick={() => act(() => sendLetter(l.id), "Letter emailed with the PDF attached.")} className="text-xs font-medium text-primary hover:underline">Email</button>
                  )}
                </td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-6 text-center text-gray-400">No letters yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-3xl p-4 sm:p-6 max-h-[92vh] overflow-y-auto">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
              {modal === "new" ? "New letter" : `${editable ? "Edit" : "View"} ${modal.number}`}
            </h2>
            {modal !== "new" && !editable && (
              <p className="text-sm text-gray-500 mb-3">
                This letter was issued{modal.issued_at ? ` on ${modal.issued_at.slice(0, 10)}` : ""} and is a frozen record.
              </p>
            )}
            <div className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] uppercase tracking-wide text-gray-400 mb-1">Letter type</label>
                  <select
                    className={inputClass}
                    disabled={!editable}
                    value={form.letter_type}
                    onChange={(e) => applyTemplate(e.target.value, form.recipient_name, form.client_id)}
                  >
                    {types.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                  <p className="mt-1 text-[11px] text-gray-400">Changing the type reloads the template text.</p>
                </div>
                <div>
                  <label className="block text-[11px] uppercase tracking-wide text-gray-400 mb-1">Date</label>
                  <input type="date" className={inputClass} disabled={!editable} value={form.letter_date} onChange={(e) => setForm((f) => ({ ...f, letter_date: e.target.value }))} />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input className={inputClass} placeholder="Recipient name (person or organization)" disabled={!editable} value={form.recipient_name} onChange={(e) => setForm((f) => ({ ...f, recipient_name: e.target.value }))} />
                <select className={inputClass} disabled={!editable} value={form.client_id} onChange={(e) => setForm((f) => ({ ...f, client_id: e.target.value }))}>
                  <option value="">Link to client (optional)…</option>
                  {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                <textarea rows={2} className={inputClass} placeholder="Recipient address (optional, shown on the letter)" disabled={!editable} value={form.recipient_address} onChange={(e) => setForm((f) => ({ ...f, recipient_address: e.target.value }))} />
                <input type="email" className={inputClass} placeholder="Recipient email (optional, for sending)" disabled={!editable} value={form.recipient_email} onChange={(e) => setForm((f) => ({ ...f, recipient_email: e.target.value }))} />
              </div>

              <input className={inputClass} placeholder="Subject *" disabled={!editable} value={form.subject} onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))} />
              <textarea rows={12} className={`${inputClass} leading-relaxed`} placeholder="Letter body * — [square brackets] mark text to replace" disabled={!editable} value={form.body} onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))} />

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] uppercase tracking-wide text-gray-400 mb-1">Signatory</label>
                  <input className={inputClass} placeholder="Name" disabled={!editable} value={form.signatory_name} onChange={(e) => setForm((f) => ({ ...f, signatory_name: e.target.value }))} />
                </div>
                <div>
                  <label className="block text-[11px] uppercase tracking-wide text-gray-400 mb-1">Title</label>
                  <input className={inputClass} placeholder="e.g. Chief Executive Officer" disabled={!editable} value={form.signatory_title} onChange={(e) => setForm((f) => ({ ...f, signatory_title: e.target.value }))} />
                </div>
              </div>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 font-medium">Close</button>
              {editable && canWrite && (
                <button onClick={save} disabled={!form.subject.trim() || !form.body.trim()} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover disabled:opacity-50">
                  Save
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
