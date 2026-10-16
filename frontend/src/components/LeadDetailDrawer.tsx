import { useEffect, useRef, useState } from "react";
import {
  getLead,
  getLeadTimeline,
  createLeadInteraction,
  deleteLeadInteraction,
  INTERACTION_TYPES,
  type Lead,
  type LeadTimelineItem,
} from "@/api/leads";
import { useAuth } from "@/store/auth";
import { useModal } from "@/contexts/ModalContext";
import { NotesSection } from "@/components/NotesSection";
import { AttachmentsSection } from "@/components/AttachmentsSection";

interface LeadDetailDrawerProps {
  lead: Lead;
  teamName?: string | null;
  /** Bump to make the drawer refetch the lead and its history (after edit, convert, etc.). */
  refreshKey: number;
  canWrite: boolean;
  canManageLeads: boolean;
  memberCanEdit: boolean;
  managementCanEdit: boolean;
  onClose: () => void;
  onEdit: (l: Lead) => void;
  onConvert: (l: Lead) => void;
  onMarkAsConverted: (l: Lead) => void;
  onMarkLost: (l: Lead) => void;
  onDelete: (id: string) => void;
  /** The list should reload: logging contact can change status, assignee and follow-up fields. */
  onChanged: () => void;
}

const STATUS_STYLES: Record<string, string> = {
  new: "bg-blue-50 text-blue-700 ring-blue-200",
  contacted: "bg-indigo-50 text-indigo-700 ring-indigo-200",
  qualified: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  converted: "bg-green-50 text-green-700 ring-green-200",
  lost: "bg-gray-100 text-gray-600 ring-gray-200",
  closed: "bg-gray-100 text-gray-600 ring-gray-200",
  dead: "bg-red-50 text-red-700 ring-red-200",
};

const LEAD_STATUSES = ["new", "contacted", "qualified", "converted", "lost", "closed", "dead"];

const TYPE_LABELS: Record<string, string> = {
  call: "Call",
  email: "Email",
  meeting: "Meeting",
  whatsapp: "WhatsApp",
  linkedin: "LinkedIn",
  other: "Other",
};

function fmtDateTime(iso: string | null | undefined) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function fmtDate(iso: string | null | undefined) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" });
}

/** "in 3 days", "today", "2 days ago" — enough for a follow-up date at a glance. */
function relativeDays(iso: string) {
  const start = new Date();
  start.setHours(0, 0, 0, 0);
  const target = new Date(iso);
  target.setHours(0, 0, 0, 0);
  const diff = Math.round((target.getTime() - start.getTime()) / 86_400_000);
  if (diff === 0) return "today";
  if (diff === 1) return "tomorrow";
  if (diff === -1) return "yesterday";
  return diff > 0 ? `in ${diff} days` : `${-diff} days ago`;
}

function toLocalInputValue(d: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function StatusPill({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ring-1 ring-inset ${STATUS_STYLES[status] ?? "bg-gray-100 text-gray-600 ring-gray-200"}`}>
      {status}
    </span>
  );
}

function KindIcon({ kind, type }: { kind: LeadTimelineItem["kind"]; type: string }) {
  const base = "w-8 h-8 rounded-full flex items-center justify-center shrink-0 ring-4 ring-white";
  if (kind === "interaction") {
    const icon =
      type === "call" ? (
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
      ) : type === "email" ? (
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
      ) : type === "meeting" ? (
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
      ) : (
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
      );
    return (
      <span className={`${base} bg-primary text-white`}>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">{icon}</svg>
      </span>
    );
  }
  if (kind === "meeting") {
    return (
      <span className={`${base} bg-violet-100 text-violet-700`}>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      </span>
    );
  }
  if (kind === "quote") {
    return (
      <span className={`${base} bg-amber-100 text-amber-700`}>
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </span>
    );
  }
  return (
    <span className={`${base} bg-gray-100 text-gray-500`}>
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    </span>
  );
}

export function LeadDetailDrawer({
  lead: initialLead,
  teamName,
  refreshKey,
  canWrite,
  canManageLeads,
  memberCanEdit,
  managementCanEdit,
  onClose,
  onEdit,
  onConvert,
  onMarkAsConverted,
  onMarkLost,
  onDelete,
  onChanged,
}: LeadDetailDrawerProps) {
  const { user } = useAuth();
  const { showConfirm, showAlert } = useModal();
  const [lead, setLead] = useState<Lead>(initialLead);
  const [timeline, setTimeline] = useState<LeadTimelineItem[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    type: "call",
    summary: "",
    occurred_at: toLocalInputValue(new Date()),
    next_follow_up: "",
    status: "",
  });
  const summaryRef = useRef<HTMLTextAreaElement>(null);

  const canEdit = memberCanEdit || managementCanEdit;
  const canLog = canWrite && canEdit;

  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const [fresh, items] = await Promise.all([getLead(initialLead.id), getLeadTimeline(initialLead.id)]);
      setLead(fresh);
      setTimeline(items);
    } catch {
      setTimeline([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    setLead(initialLead);
  }, [initialLead]);

  useEffect(() => {
    loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialLead.id, refreshKey]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  const logInteraction = async () => {
    if (!form.summary.trim() || saving) return;
    setSaving(true);
    try {
      await createLeadInteraction(lead.id, {
        type: form.type,
        summary: form.summary.trim(),
        occurred_at: form.occurred_at ? new Date(form.occurred_at).toISOString() : undefined,
        next_follow_up_at: form.next_follow_up ? new Date(`${form.next_follow_up}T09:00`).toISOString() : null,
        status: form.status || undefined,
      });
      setForm({ type: form.type, summary: "", occurred_at: toLocalInputValue(new Date()), next_follow_up: "", status: "" });
      await loadHistory();
      onChanged();
    } catch (e) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed to log interaction" });
    } finally {
      setSaving(false);
    }
  };

  const removeInteraction = (item: LeadTimelineItem) => {
    if (!item.reference_id) return;
    showConfirm({
      title: "Delete entry",
      message: "Remove this interaction from the lead's history?",
      confirmLabel: "Delete",
      variant: "danger",
      onConfirm: async () => {
        try {
          await deleteLeadInteraction(lead.id, item.reference_id as string);
          await loadHistory();
          onChanged();
        } catch (e) {
          showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed to delete" });
          throw e;
        }
      },
    });
  };

  const followUpOverdue = !!lead.next_follow_up_at && new Date(lead.next_follow_up_at).getTime() < Date.now() && !lead.converted_to_client_id;
  const fieldClass = "w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-500 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm";
  const actionClass = "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border border-gray-200 text-gray-700 hover:bg-gray-50";

  return (
    <>
      <div className="fixed inset-0 bg-black/30 z-30" aria-hidden onClick={onClose} />
      <div
        className="fixed top-0 right-0 bottom-0 w-full max-w-3xl bg-white shadow-2xl z-40 flex flex-col animate-slide-in-right"
        role="dialog"
        aria-label={`Lead: ${lead.company_name}`}
      >
        {/* Header */}
        <div className="shrink-0 px-6 py-4 border-b border-gray-100">
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <p className="text-xs font-semibold tracking-wider uppercase text-gray-400 mb-1">Lead</p>
              <h2 className="text-xl font-semibold text-gray-900 truncate">{lead.company_name}</h2>
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                <StatusPill status={lead.status} />
                {lead.source && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                    {lead.source}
                  </span>
                )}
                {lead.converted_to_client_id && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700">
                    Client created
                  </span>
                )}
                {followUpOverdue && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700">
                    Follow-up overdue
                  </span>
                )}
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-gray-700 shrink-0"
              aria-label="Close"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {canEdit && (
            <div className="flex items-center gap-2 mt-4 flex-wrap">
              <button type="button" onClick={() => onEdit(lead)} className={actionClass}>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                </svg>
                Edit details
              </button>
              {canLog && (
                <button
                  type="button"
                  onClick={() => summaryRef.current?.focus()}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium bg-primary text-white hover:bg-primary-hover"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Log interaction
                </button>
              )}
              {!lead.converted_to_client_id && (
                <>
                  {managementCanEdit && (
                    <button type="button" onClick={() => onConvert(lead)} className={actionClass}>
                      Create client &amp; project
                    </button>
                  )}
                  {memberCanEdit && (
                    <button type="button" onClick={() => onMarkAsConverted(lead)} className={actionClass}>
                      Mark as converted
                    </button>
                  )}
                  <button type="button" onClick={() => onMarkLost(lead)} className={actionClass}>
                    Mark lost / closed
                  </button>
                </>
              )}
              <button
                type="button"
                onClick={() => onDelete(lead.id)}
                className="ml-auto inline-flex items-center px-3 py-1.5 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50"
              >
                Delete
              </button>
            </div>
          )}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto">
          <div className="px-6 py-5 space-y-6">
            {/* Details */}
            <section>
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Details</h3>
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
                <div>
                  <dt className="text-gray-500">Contact</dt>
                  <dd className="text-gray-900 font-medium">{lead.contact_name || "—"}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Email</dt>
                  <dd className="text-gray-900">
                    {lead.contact_email ? (
                      <a href={`mailto:${lead.contact_email}`} className="text-primary hover:underline break-all">{lead.contact_email}</a>
                    ) : "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Phone</dt>
                  <dd className="text-gray-900">
                    {lead.contact_phone ? (
                      <a href={`tel:${lead.contact_phone}`} className="text-primary hover:underline">{lead.contact_phone}</a>
                    ) : "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Team</dt>
                  <dd className="text-gray-900">{teamName || "—"}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Assigned to</dt>
                  <dd className="text-gray-900">{lead.assigned_to_name || "Unassigned"}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Submitted by</dt>
                  <dd className="text-gray-900">{lead.created_by_name || "—"}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Created</dt>
                  <dd className="text-gray-900">{fmtDateTime(lead.created_at)}</dd>
                </div>
                <div>
                  <dt className="text-gray-500">Last contact</dt>
                  <dd className="text-gray-900">
                    {lead.last_contact_at ? `${fmtDateTime(lead.last_contact_at)} · ${relativeDays(lead.last_contact_at)}` : "No contact logged yet"}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500">Next follow-up</dt>
                  <dd className={followUpOverdue ? "text-red-600 font-medium" : "text-gray-900"}>
                    {lead.next_follow_up_at ? `${fmtDate(lead.next_follow_up_at)} · ${relativeDays(lead.next_follow_up_at)}` : "—"}
                  </dd>
                </div>
                {lead.converted_at && (
                  <div>
                    <dt className="text-gray-500">Converted</dt>
                    <dd className="text-gray-900">{fmtDateTime(lead.converted_at)}</dd>
                  </div>
                )}
              </dl>
              {lead.notes && (
                <div className="mt-4 rounded-lg bg-gray-50 border border-gray-100 p-3 text-sm text-gray-700 whitespace-pre-wrap">
                  {lead.notes}
                </div>
              )}
            </section>

            {/* Log an interaction */}
            {canLog && (
              <section className="rounded-xl border border-gray-200 p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Log an interaction</h3>
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {INTERACTION_TYPES.map((t) => (
                    <button
                      key={t}
                      type="button"
                      onClick={() => setForm((f) => ({ ...f, type: t }))}
                      className={`px-3 py-1 rounded-full text-xs font-medium border transition-colors ${
                        form.type === t ? "bg-primary text-white border-primary" : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      {TYPE_LABELS[t]}
                    </button>
                  ))}
                </div>
                <textarea
                  ref={summaryRef}
                  value={form.summary}
                  onChange={(e) => setForm((f) => ({ ...f, summary: e.target.value }))}
                  placeholder="What happened? e.g. Spoke to Sara, she wants a demo of the ERP next week."
                  rows={3}
                  className={fieldClass}
                />
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">When</label>
                    <input
                      type="datetime-local"
                      value={form.occurred_at}
                      onChange={(e) => setForm((f) => ({ ...f, occurred_at: e.target.value }))}
                      className={fieldClass}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Next follow-up</label>
                    <input
                      type="date"
                      value={form.next_follow_up}
                      onChange={(e) => setForm((f) => ({ ...f, next_follow_up: e.target.value }))}
                      className={fieldClass}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Move stage to</label>
                    <select
                      value={form.status}
                      onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
                      className={fieldClass}
                      disabled={!!lead.converted_to_client_id}
                    >
                      <option value="">Keep “{lead.status}”</option>
                      {LEAD_STATUSES.filter((s) => s !== lead.status).map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="flex justify-end mt-3">
                  <button
                    type="button"
                    onClick={logInteraction}
                    disabled={!form.summary.trim() || saving}
                    className="px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {saving ? "Saving…" : "Save to history"}
                  </button>
                </div>
              </section>
            )}

            {/* History */}
            <section>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-700">History</h3>
                {!historyLoading && <span className="text-xs text-gray-400">{timeline.length} {timeline.length === 1 ? "entry" : "entries"}</span>}
              </div>
              {historyLoading ? (
                <p className="text-sm text-gray-500">Loading history…</p>
              ) : timeline.length === 0 ? (
                <p className="text-sm text-gray-500">Nothing recorded yet. Log the first call or email above.</p>
              ) : (
                <ol className="relative border-l border-gray-200 ml-4 space-y-5">
                  {timeline.map((item) => {
                    const own = item.kind === "interaction" && (canManageLeads || timelineAuthorIsUser(item, user?.full_name, user?.email));
                    return (
                      <li key={item.id} className="ml-6">
                        <span className="absolute -left-4">
                          <KindIcon kind={item.kind} type={item.type} />
                        </span>
                        <div className="rounded-lg border border-gray-100 bg-white p-3 shadow-sm">
                          <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                              <p className="text-sm font-medium text-gray-900">
                                {item.kind === "interaction" ? TYPE_LABELS[item.type] ?? item.title : item.title}
                                {item.kind !== "interaction" && (
                                  <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-medium bg-gray-100 text-gray-600">
                                    {item.type.replace(/_/g, " ")}
                                  </span>
                                )}
                              </p>
                              {item.details && <p className="text-sm text-gray-700 mt-1 whitespace-pre-wrap">{item.details}</p>}
                              <p className="text-xs text-gray-500 mt-2">
                                {item.by_name ?? "—"} · {fmtDateTime(item.occurred_at)}
                                {item.next_follow_up_at && (
                                  <span className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded bg-amber-50 text-amber-800">
                                    Follow up {fmtDate(item.next_follow_up_at)}
                                  </span>
                                )}
                              </p>
                            </div>
                            {own && canWrite && (
                              <button
                                type="button"
                                onClick={() => removeInteraction(item)}
                                className="text-xs text-gray-400 hover:text-red-600 shrink-0"
                                title="Delete entry"
                              >
                                Delete
                              </button>
                            )}
                          </div>
                        </div>
                      </li>
                    );
                  })}
                </ol>
              )}
            </section>

            <NotesSection entityType="lead" entityId={lead.id} />
            <AttachmentsSection entityType="lead" entityId={lead.id} />
          </div>
        </div>
      </div>
    </>
  );
}

/** The timeline carries display names, not ids; match the current user by name or email. */
function timelineAuthorIsUser(item: LeadTimelineItem, fullName: string | null | undefined, email: string | null | undefined) {
  if (!item.by_name) return false;
  return item.by_name === (fullName?.trim() || "") || item.by_name === email;
}
