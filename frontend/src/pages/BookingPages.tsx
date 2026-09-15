import { useEffect, useMemo, useState } from "react";
import {
  listBookingPages,
  createBookingPage,
  updateBookingPage,
  deleteBookingPage,
  previewBookingSlots,
  type BookingPage,
  type BookingPageInput,
  type BookingQuestion,
  type BookingHours,
} from "@/api/booking";
import { listAssignableUsers, type UserList } from "@/api/users";
import { useModal } from "@/contexts/ModalContext";

const DAYS: { key: string; label: string }[] = [
  { key: "mon", label: "Monday" },
  { key: "tue", label: "Tuesday" },
  { key: "wed", label: "Wednesday" },
  { key: "thu", label: "Thursday" },
  { key: "fri", label: "Friday" },
  { key: "sat", label: "Saturday" },
  { key: "sun", label: "Sunday" },
];

const inputClass =
  "w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm";
const labelClass = "block text-sm font-medium text-gray-700 mb-1";

function browserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch {
    return "UTC";
  }
}

function timezoneOptions(): string[] {
  try {
    const intl = Intl as unknown as { supportedValuesOf?: (k: string) => string[] };
    const list = intl.supportedValuesOf?.("timeZone");
    if (list && list.length) return list;
  } catch {
    /* ignore */
  }
  return ["UTC", "Asia/Karachi", "Asia/Dubai", "Europe/London", "America/New_York"];
}

function slugify(s: string): string {
  return s
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
}

const DEFAULT_HOURS: BookingHours = {
  mon: [["10:00", "18:00"]],
  tue: [["10:00", "18:00"]],
  wed: [["10:00", "18:00"]],
  thu: [["10:00", "18:00"]],
  fri: [["10:00", "18:00"]],
};

function emptyForm(): BookingPageInput {
  return {
    slug: "discovery-call",
    name: "Discovery call",
    description: "A free 30-minute call to talk through your project and next steps. No commitment.",
    duration_minutes: 30,
    buffer_before_minutes: 0,
    buffer_after_minutes: 15,
    min_notice_minutes: 240,
    max_days_ahead: 30,
    timezone: browserTimezone(),
    hours: DEFAULT_HOURS,
    questions: [
      { id: "company", label: "Company name", type: "text", required: true },
      { id: "project", label: "What are you looking to build?", type: "textarea", required: false },
    ],
    location_text: "Video call (link in your calendar invite)",
    host_user_id: null,
    is_active: true,
  };
}

export default function BookingPagesPage() {
  const { showConfirm, showAlert } = useModal();
  const [items, setItems] = useState<BookingPage[]>([]);
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState<UserList[]>([]);
  const [modal, setModal] = useState<"new" | BookingPage | null>(null);
  const [form, setForm] = useState<BookingPageInput>(emptyForm());
  const [saving, setSaving] = useState(false);
  const [slugTouched, setSlugTouched] = useState(false);
  const [preview, setPreview] = useState<{ page: BookingPage; slots: string[]; timezone: string } | null>(null);
  const tzOptions = useMemo(timezoneOptions, []);
  const publicBase = (import.meta.env.VITE_BOOKING_PUBLIC_URL as string | undefined)?.replace(/\/$/, "") || "";

  const load = () => {
    listBookingPages()
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  };
  useEffect(() => {
    load();
    listAssignableUsers().then(setUsers).catch(() => setUsers([]));
  }, []);

  const openNew = () => {
    setForm(emptyForm());
    setSlugTouched(false);
    setModal("new");
  };
  const openEdit = (p: BookingPage) => {
    setForm({
      slug: p.slug,
      name: p.name,
      description: p.description ?? "",
      duration_minutes: p.duration_minutes,
      buffer_before_minutes: p.buffer_before_minutes,
      buffer_after_minutes: p.buffer_after_minutes,
      min_notice_minutes: p.min_notice_minutes,
      max_days_ahead: p.max_days_ahead,
      timezone: p.timezone,
      hours: p.hours ?? {},
      questions: p.questions ?? [],
      location_text: p.location_text ?? "",
      host_user_id: p.host_user_id,
      is_active: p.is_active,
    });
    setSlugTouched(true);
    setModal(p);
  };

  const save = async () => {
    if (!form.name.trim()) return showAlert({ title: "Missing name", message: "Give the booking page a name." });
    if (!form.host_user_id) return showAlert({ title: "Missing host", message: "Choose who hosts these calls. Their existing meetings block slots." });
    if (Object.keys(form.hours).length === 0) return showAlert({ title: "No hours", message: "Enable at least one day." });
    setSaving(true);
    try {
      const payload: BookingPageInput = {
        ...form,
        description: form.description || null,
        location_text: form.location_text || null,
        questions: form.questions.filter((q) => q.label.trim()).map((q) => ({ ...q, id: q.id || slugify(q.label) })),
      };
      if (modal === "new") await createBookingPage(payload);
      else if (modal) await updateBookingPage(modal.id, payload);
      setModal(null);
      load();
    } catch (e: unknown) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    } finally {
      setSaving(false);
    }
  };

  const remove = (p: BookingPage) => {
    showConfirm({
      title: "Delete booking page",
      message: `Delete "${p.name}"? Existing meetings are kept; the public page stops working immediately.`,
      confirmLabel: "Delete",
      variant: "danger",
      onConfirm: async () => {
        await deleteBookingPage(p.id);
        setModal(null);
        load();
      },
    });
  };

  const toggleActive = async (p: BookingPage) => {
    try {
      await updateBookingPage(p.id, { is_active: !p.is_active });
      load();
    } catch (e: unknown) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    }
  };

  const showPreview = async (p: BookingPage) => {
    const start = new Date();
    const end = new Date();
    end.setDate(end.getDate() + 6);
    const iso = (d: Date) => d.toISOString().slice(0, 10);
    try {
      const r = await previewBookingSlots(p.id, iso(start), iso(end));
      setPreview({ page: p, slots: r.slots, timezone: r.timezone });
    } catch (e: unknown) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    }
  };

  // ---- hours editor helpers ----
  const dayEnabled = (key: string) => (form.hours[key]?.length ?? 0) > 0;
  const setDay = (key: string, enabled: boolean) => {
    setForm((f) => {
      const hours = { ...f.hours };
      if (enabled) hours[key] = hours[key]?.length ? hours[key] : [["10:00", "18:00"]];
      else delete hours[key];
      return { ...f, hours };
    });
  };
  const setWindow = (key: string, idx: number, pos: 0 | 1, value: string) => {
    setForm((f) => {
      const hours = { ...f.hours };
      const windows = (hours[key] ?? []).map((w) => [...w] as [string, string]);
      windows[idx][pos] = value;
      hours[key] = windows;
      return { ...f, hours };
    });
  };
  const addWindow = (key: string) =>
    setForm((f) => ({ ...f, hours: { ...f.hours, [key]: [...(f.hours[key] ?? []), ["14:00", "17:00"]] } }));
  const removeWindow = (key: string, idx: number) =>
    setForm((f) => {
      const windows = (f.hours[key] ?? []).filter((_, i) => i !== idx);
      const hours = { ...f.hours };
      if (windows.length) hours[key] = windows;
      else delete hours[key];
      return { ...f, hours };
    });

  // ---- questions editor helpers ----
  const setQuestion = (idx: number, patch: Partial<BookingQuestion>) =>
    setForm((f) => ({ ...f, questions: f.questions.map((q, i) => (i === idx ? { ...q, ...patch } : q)) }));
  const addQuestion = () =>
    setForm((f) => ({ ...f, questions: [...f.questions, { id: "", label: "", type: "text", required: false }] }));
  const removeQuestion = (idx: number) => setForm((f) => ({ ...f, questions: f.questions.filter((_, i) => i !== idx) }));

  const num = (v: string, fallback: number) => (v === "" ? fallback : Math.max(0, parseInt(v, 10) || 0));

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <p className="text-sm text-gray-600 max-w-2xl">
          Booking pages power the public &ldquo;Book a call&rdquo; page on the website. Visitors pick a free slot from the host&rsquo;s
          hours, minus their existing meetings. Each booking becomes a meeting here and a lead for new contacts.
        </p>
        <button onClick={openNew} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover">
          New booking page
        </button>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : items.length === 0 ? (
        <div className="rounded-xl bg-white border border-dashed border-gray-200 p-10 text-center text-gray-500">
          No booking pages yet. Create one to enable online booking.
        </div>
      ) : (
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-x-auto">
          <table className="w-full min-w-[720px]">
            <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600">
              <tr>
                <th className="px-4 py-3">Page</th>
                <th className="px-4 py-3">Host</th>
                <th className="px-4 py-3">Length</th>
                <th className="px-4 py-3">Timezone</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 w-40 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {items.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50/80">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">{p.name}</div>
                    <div className="text-xs text-gray-500">
                      {publicBase ? (
                        <a href={`${publicBase}/book?page=${p.slug}`} target="_blank" rel="noreferrer" className="hover:text-primary">
                          {publicBase}/book?page={p.slug}
                        </a>
                      ) : (
                        <span>slug: {p.slug}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {p.host_name || <span className="text-red-600">No host</span>}
                    {p.host_name && (
                      <div className={`text-xs mt-0.5 ${p.host_google_connected ? "text-green-700" : "text-amber-700"}`} title={p.host_google_connected ? "Bookings get a Google Meet link and sync to the host's calendar" : "The host has not connected Google Calendar in Profile: invites go out as .ics without a Meet link"}>
                        {p.host_google_connected ? "Google Calendar · Meet links" : "No Google Calendar"}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{p.duration_minutes} min</td>
                  <td className="px-4 py-3 text-gray-600">{p.timezone}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggleActive(p)}
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${
                        p.is_active ? "bg-green-50 text-green-700 border-green-100" : "bg-gray-100 text-gray-600 border-gray-200"
                      }`}
                      title="Click to toggle"
                    >
                      {p.is_active ? "Live" : "Paused"}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button onClick={() => showPreview(p)} className="px-2 py-1 text-xs rounded-lg text-gray-600 hover:bg-gray-100">
                        Preview slots
                      </button>
                      <button onClick={() => openEdit(p)} className="px-2 py-1 text-xs rounded-lg text-primary hover:bg-gray-100">
                        Edit
                      </button>
                      <button onClick={() => remove(p)} className="px-2 py-1 text-xs rounded-lg text-red-600 hover:bg-gray-100">
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {preview && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-10" onClick={() => setPreview(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-lg max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-gray-900 mb-1">Next 7 days: {preview.page.name}</h2>
            <p className="text-xs text-gray-500 mb-4">Shown in {preview.timezone}. This is exactly what visitors can pick right now.</p>
            {preview.slots.length === 0 ? (
              <p className="text-sm text-gray-500">No free slots. Check the hours, the host&rsquo;s meetings and the minimum notice.</p>
            ) : (
              <div className="space-y-2">
                {Object.entries(
                  preview.slots.reduce<Record<string, string[]>>((acc, s) => {
                    const d = new Date(s);
                    const day = d.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short", timeZone: preview.timezone });
                    (acc[day] ||= []).push(d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", timeZone: preview.timezone }));
                    return acc;
                  }, {})
                ).map(([day, times]) => (
                  <div key={day} className="text-sm">
                    <span className="font-medium text-gray-800">{day}</span>
                    <span className="text-gray-500"> · {times.join(", ")}</span>
                  </div>
                ))}
              </div>
            )}
            <div className="flex justify-end mt-4">
              <button onClick={() => setPreview(null)} className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">Close</button>
            </div>
          </div>
        </div>
      )}

      {modal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-10" onClick={() => setModal(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">{modal === "new" ? "New booking page" : "Edit booking page"}</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="md:col-span-2">
                <label className={labelClass}>Name</label>
                <input
                  className={inputClass}
                  value={form.name}
                  onChange={(e) => {
                    const name = e.target.value;
                    setForm((f) => ({ ...f, name, slug: slugTouched ? f.slug : slugify(name) }));
                  }}
                />
              </div>
              <div>
                <label className={labelClass}>URL slug</label>
                <input
                  className={inputClass}
                  value={form.slug}
                  onChange={(e) => {
                    setSlugTouched(true);
                    setForm((f) => ({ ...f, slug: slugify(e.target.value) }));
                  }}
                />
              </div>
              <div>
                <label className={labelClass}>Host</label>
                <select className={inputClass} value={form.host_user_id ?? ""} onChange={(e) => setForm((f) => ({ ...f, host_user_id: e.target.value || null }))}>
                  <option value="">Select host…</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>{u.full_name || u.email}</option>
                  ))}
                </select>
              </div>
              <div className="md:col-span-2">
                <label className={labelClass}>Description (shown to visitors)</label>
                <textarea className={inputClass} rows={2} value={form.description ?? ""} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} />
              </div>
              <div className="md:col-span-2">
                <label className={labelClass}>Location text (shown in confirmation)</label>
                <input className={inputClass} value={form.location_text ?? ""} onChange={(e) => setForm((f) => ({ ...f, location_text: e.target.value }))} placeholder="Video call (link in your calendar invite)" />
              </div>
              <div>
                <label className={labelClass}>Duration (minutes)</label>
                <input type="number" min={5} className={inputClass} value={form.duration_minutes} onChange={(e) => setForm((f) => ({ ...f, duration_minutes: num(e.target.value, 30) }))} />
              </div>
              <div>
                <label className={labelClass}>Timezone (hours below are in this zone)</label>
                <select className={inputClass} value={form.timezone} onChange={(e) => setForm((f) => ({ ...f, timezone: e.target.value }))}>
                  {tzOptions.map((tz) => (
                    <option key={tz} value={tz}>{tz}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className={labelClass}>Buffer before / after (minutes)</label>
                <div className="flex gap-2">
                  <input type="number" min={0} className={inputClass} value={form.buffer_before_minutes} onChange={(e) => setForm((f) => ({ ...f, buffer_before_minutes: num(e.target.value, 0) }))} />
                  <input type="number" min={0} className={inputClass} value={form.buffer_after_minutes} onChange={(e) => setForm((f) => ({ ...f, buffer_after_minutes: num(e.target.value, 15) }))} />
                </div>
              </div>
              <div>
                <label className={labelClass}>Minimum notice (minutes) / book up to (days)</label>
                <div className="flex gap-2">
                  <input type="number" min={0} className={inputClass} value={form.min_notice_minutes} onChange={(e) => setForm((f) => ({ ...f, min_notice_minutes: num(e.target.value, 240) }))} />
                  <input type="number" min={1} className={inputClass} value={form.max_days_ahead} onChange={(e) => setForm((f) => ({ ...f, max_days_ahead: Math.max(1, num(e.target.value, 30)) }))} />
                </div>
              </div>
            </div>

            <h3 className="text-sm font-semibold text-gray-900 mt-5 mb-2">Weekly hours</h3>
            <div className="space-y-2">
              {DAYS.map((d) => (
                <div key={d.key} className="flex items-start gap-3">
                  <label className="flex items-center gap-2 w-32 pt-2 text-sm text-gray-700">
                    <input type="checkbox" checked={dayEnabled(d.key)} onChange={(e) => setDay(d.key, e.target.checked)} className="rounded border-gray-300 text-primary focus:ring-primary/20" />
                    {d.label}
                  </label>
                  <div className="flex-1 space-y-1">
                    {dayEnabled(d.key) ? (
                      (form.hours[d.key] ?? []).map((w, i) => (
                        <div key={i} className="flex items-center gap-2">
                          <input type="time" className={inputClass} value={w[0]} onChange={(e) => setWindow(d.key, i, 0, e.target.value)} />
                          <span className="text-gray-400 text-sm">to</span>
                          <input type="time" className={inputClass} value={w[1]} onChange={(e) => setWindow(d.key, i, 1, e.target.value)} />
                          <button type="button" onClick={() => removeWindow(d.key, i)} className="text-gray-400 hover:text-red-600 text-lg leading-none px-1" title="Remove window">×</button>
                          {i === (form.hours[d.key]?.length ?? 1) - 1 && (
                            <button type="button" onClick={() => addWindow(d.key)} className="text-xs text-primary hover:underline whitespace-nowrap">+ window</button>
                          )}
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-gray-400 pt-2">Unavailable</p>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <h3 className="text-sm font-semibold text-gray-900 mt-5 mb-2">Questions asked when booking</h3>
            <p className="text-xs text-gray-500 mb-2">Name and email are always collected. A question mentioning &ldquo;company&rdquo; names the lead.</p>
            <div className="space-y-2">
              {form.questions.map((q, i) => (
                <div key={i} className="flex items-center gap-2">
                  <input className={inputClass} placeholder="Question label" value={q.label} onChange={(e) => setQuestion(i, { label: e.target.value, id: q.id || slugify(e.target.value) })} />
                  <select className={`${inputClass} w-32`} value={q.type} onChange={(e) => setQuestion(i, { type: e.target.value as BookingQuestion["type"] })}>
                    <option value="text">Short</option>
                    <option value="textarea">Long</option>
                  </select>
                  <label className="flex items-center gap-1 text-xs text-gray-600 whitespace-nowrap">
                    <input type="checkbox" checked={q.required} onChange={(e) => setQuestion(i, { required: e.target.checked })} className="rounded border-gray-300 text-primary focus:ring-primary/20" />
                    Required
                  </label>
                  <button type="button" onClick={() => removeQuestion(i)} className="text-gray-400 hover:text-red-600 text-lg leading-none px-1" title="Remove">×</button>
                </div>
              ))}
              <button type="button" onClick={addQuestion} className="text-xs text-primary hover:underline">+ Add question</button>
            </div>

            <label className="flex items-center gap-2 mt-5 text-sm text-gray-700">
              <input type="checkbox" checked={form.is_active} onChange={(e) => setForm((f) => ({ ...f, is_active: e.target.checked }))} className="rounded border-gray-300 text-primary focus:ring-primary/20" />
              Live (visitors can book)
            </label>

            <div className="flex justify-between items-center mt-5">
              {modal !== "new" ? (
                <button onClick={() => remove(modal as BookingPage)} className="text-sm text-red-600 hover:underline">Delete page</button>
              ) : <span />}
              <div className="flex gap-2">
                <button onClick={() => setModal(null)} className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">Cancel</button>
                <button onClick={save} disabled={saving} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover disabled:opacity-60">
                  {saving ? "Saving…" : "Save"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
