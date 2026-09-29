import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "@/store/auth";
import { useModal } from "@/contexts/ModalContext";
import {
  getMyAttendance, getTodayBoard, getAttendanceSummary, listAttendanceRecords, correctAttendance, deleteAttendance,
  fmtTime, fmtDay, mapsLink, type AttendanceMe, type TodayBoard, type AttendanceSummary, type AttendanceRecord,
} from "@/api/attendance";
import { AttendanceStatusChip, CheckInCard } from "@/components/AttendancePanel";

type Tab = "mine" | "today" | "report" | "records";

function iso(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export default function AttendancePage() {
  const { user, hasPermission } = useAuth();
  const { showConfirm, showAlert } = useModal();
  const isAdmin = hasPermission("attendance:manage");
  const [tab, setTab] = useState<Tab>(isAdmin ? "today" : "mine");
  const [me, setMe] = useState<AttendanceMe | null>(null);
  const [board, setBoard] = useState<TodayBoard | null>(null);
  const [summary, setSummary] = useState<AttendanceSummary | null>(null);
  const [records, setRecords] = useState<AttendanceRecord[]>([]);
  const [range, setRange] = useState(() => {
    const to = new Date();
    const from = new Date(to.getTime() - 29 * 86400000);
    return { from: iso(from), to: iso(to) };
  });
  const [includeInactive, setIncludeInactive] = useState(false);
  const [userFilter, setUserFilter] = useState("");
  const [edit, setEdit] = useState<AttendanceRecord | null>(null);
  const [editForm, setEditForm] = useState({ check_in: "", check_out: "", status: "present", note: "" });
  const [busy, setBusy] = useState(false);

  const loadMine = useCallback(() => { getMyAttendance(60).then(setMe).catch(() => setMe(null)); }, []);
  const loadToday = useCallback(() => { if (isAdmin) getTodayBoard().then(setBoard).catch(() => setBoard(null)); }, [isAdmin]);
  const loadSummary = useCallback(() => {
    if (isAdmin) getAttendanceSummary({ from: range.from, to: range.to, include_inactive: includeInactive }).then(setSummary).catch(() => setSummary(null));
  }, [isAdmin, range, includeInactive]);
  const loadRecords = useCallback(() => {
    if (isAdmin) listAttendanceRecords({ from: range.from, to: range.to, user_id: userFilter || undefined, limit: 500 }).then(setRecords).catch(() => setRecords([]));
  }, [isAdmin, range, userFilter]);

  useEffect(() => { loadMine(); }, [loadMine]);
  useEffect(() => { loadToday(); }, [loadToday]);
  useEffect(() => { loadSummary(); }, [loadSummary]);
  useEffect(() => { loadRecords(); }, [loadRecords]);

  const staffOptions = useMemo(() => (board ? board.rows.map((r) => ({ id: r.user_id, name: r.full_name || r.email })) : []), [board]);

  const toLocalInput = (isoStr: string | null) => {
    if (!isoStr) return "";
    const d = new Date(isoStr);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };
  const openEdit = (r: AttendanceRecord) => {
    setEditForm({ check_in: toLocalInput(r.check_in_at), check_out: toLocalInput(r.check_out_at), status: r.status, note: r.note ?? "" });
    setEdit(r);
  };
  const saveEdit = async () => {
    if (!edit) return;
    setBusy(true);
    try {
      await correctAttendance(edit.id, {
        check_in_at: editForm.check_in ? new Date(editForm.check_in).toISOString() : undefined,
        check_out_at: editForm.check_out ? new Date(editForm.check_out).toISOString() : null,
        status: editForm.status as "present" | "late",
        note: editForm.note || undefined,
      });
      setEdit(null);
      loadRecords(); loadToday(); loadSummary();
    } catch (e) { showAlert({ title: "Error", message: e instanceof Error ? e.message : "Could not save" }); }
    finally { setBusy(false); }
  };
  const remove = (r: AttendanceRecord) => {
    showConfirm({
      title: "Delete attendance record",
      message: `Delete ${r.user_name || r.user_email} on ${fmtDay(r.work_date)}? They will count as absent for that day.`,
      confirmLabel: "Delete", variant: "danger",
      onConfirm: async () => { await deleteAttendance(r.id); setEdit(null); loadRecords(); loadToday(); loadSummary(); },
    });
  };

  const exportCsv = () => {
    if (!summary) return;
    const head = ["Employee", "Email", "Type", "Working days", "Present", "Late", "Absent", "Total hours", "Avg hours", "Attendance rate"];
    const lines = summary.rows.map((r) => [
      r.full_name ?? "", r.email, r.employment_type ?? "", r.working_days, r.present_days, r.late_days, r.absent_days, r.total_hours, r.avg_hours ?? "", r.attendance_rate != null ? Math.round(r.attendance_rate * 100) + "%" : "",
    ].map((v) => `"${String(v).replace(/"/g, '""')}"`).join(","));
    const blob = new Blob([[head.join(","), ...lines].join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `attendance-${summary.from_date}-to-${summary.to_date}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  if (!user || user.is_client) return <p className="text-gray-500">Attendance is for internal staff.</p>;

  const inputClass = "px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm";
  const tabs: { key: Tab; label: string }[] = isAdmin
    ? [{ key: "today", label: "Today" }, { key: "report", label: "Report" }, { key: "records", label: "Records" }, { key: "mine", label: "My attendance" }]
    : [{ key: "mine", label: "My attendance" }];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-0.5">
          {tabs.map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)} className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${tab === t.key ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-800"}`}>{t.label}</button>
          ))}
        </div>
        {isAdmin && (tab === "report" || tab === "records") && (
          <div className="flex items-center gap-2 flex-wrap">
            <input type="date" className={inputClass} value={range.from} onChange={(e) => setRange((r) => ({ ...r, from: e.target.value }))} />
            <span className="text-gray-400 text-sm">to</span>
            <input type="date" className={inputClass} value={range.to} onChange={(e) => setRange((r) => ({ ...r, to: e.target.value }))} />
            {tab === "records" && (
              <select className={inputClass} value={userFilter} onChange={(e) => setUserFilter(e.target.value)}>
                <option value="">Everyone</option>
                {staffOptions.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            )}
            {tab === "report" && (
              <>
                <label className="inline-flex items-center gap-2 text-sm text-gray-600"><input type="checkbox" checked={includeInactive} onChange={(e) => setIncludeInactive(e.target.checked)} className="rounded border-gray-300 text-primary" /> Include deactivated</label>
                <button onClick={exportCsv} className="px-3 py-2 rounded-lg text-sm font-medium bg-gray-100 text-gray-700 hover:bg-gray-200">Export CSV</button>
              </>
            )}
          </div>
        )}
      </div>

      {/* ---------------- mine ---------------- */}
      {tab === "mine" && (
        <div className="space-y-4">
          {me && <CheckInCard me={me} onChange={loadMine} />}
          <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-x-auto">
            <table className="w-full min-w-[520px]">
              <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600">
                <tr><th className="px-4 py-3">Day</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">In</th><th className="px-4 py-3">Out</th><th className="px-4 py-3">Hours</th><th className="px-4 py-3">Note</th></tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(me?.recent ?? []).map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50/80">
                    <td className="px-4 py-2.5 text-gray-800">{fmtDay(r.work_date)}</td>
                    <td className="px-4 py-2.5"><AttendanceStatusChip status={r.status} /></td>
                    <td className="px-4 py-2.5 text-gray-600">{fmtTime(r.check_in_at)}</td>
                    <td className="px-4 py-2.5 text-gray-600">{fmtTime(r.check_out_at)}</td>
                    <td className="px-4 py-2.5 text-gray-600">{r.check_out_at ? `${r.hours} h` : "—"}</td>
                    <td className="px-4 py-2.5 text-gray-500 text-sm">{r.note || ""}</td>
                  </tr>
                ))}
                {me && me.recent.length === 0 && <tr><td colSpan={6} className="px-4 py-6 text-center text-sm text-gray-400">No attendance yet. Check in above to start.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ---------------- today ---------------- */}
      {tab === "today" && isAdmin && (
        <div className="space-y-4">
          {board && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="rounded-xl bg-white border border-gray-100 shadow-sm p-4"><p className="text-xs uppercase tracking-wide text-gray-400">{fmtDay(board.work_date)}</p><p className="text-sm text-gray-700 mt-1">{board.is_working_day ? "Working day" : "Not a working day"}</p></div>
              <div className="rounded-xl bg-green-50 border border-green-100 p-4"><p className="text-2xl font-semibold text-green-700">{board.present}</p><p className="text-xs text-green-700/80">On time</p></div>
              <div className="rounded-xl bg-amber-50 border border-amber-100 p-4"><p className="text-2xl font-semibold text-amber-700">{board.late}</p><p className="text-xs text-amber-700/80">Late</p></div>
              <div className="rounded-xl bg-red-50 border border-red-100 p-4"><p className="text-2xl font-semibold text-red-700">{board.absent}</p><p className="text-xs text-red-700/80">Not checked in</p></div>
            </div>
          )}
          <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-x-auto">
            <table className="w-full min-w-[820px]">
              <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600">
                <tr><th className="px-4 py-3">Employee</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">In</th><th className="px-4 py-3">Out</th><th className="px-4 py-3">IP</th><th className="px-4 py-3">Location</th><th className="px-4 py-3 text-right">Actions</th></tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(board?.rows ?? []).map((r) => {
                  const link = r.record ? mapsLink(r.record) : null;
                  return (
                    <tr key={r.user_id} className="hover:bg-gray-50/80">
                      <td className="px-4 py-2.5">
                        <p className="text-gray-900 font-medium">{r.full_name || r.email}</p>
                        <p className="text-xs text-gray-500">{r.job_title || r.email}{r.employment_type ? ` · ${r.employment_type.replace("_", "-")}` : ""}</p>
                      </td>
                      <td className="px-4 py-2.5"><AttendanceStatusChip status={r.status} /></td>
                      <td className="px-4 py-2.5 text-gray-600">{fmtTime(r.record?.check_in_at)}</td>
                      <td className="px-4 py-2.5 text-gray-600">{fmtTime(r.record?.check_out_at)}</td>
                      <td className="px-4 py-2.5 text-gray-600 text-sm font-mono">{r.record?.ip_address || (r.employment_type === "intern" && r.record ? <span className="text-gray-400 font-sans">not captured</span> : "—")}</td>
                      <td className="px-4 py-2.5 text-sm">
                        {link ? <a href={link} target="_blank" rel="noreferrer" className="text-primary hover:underline">Map{r.record?.location_accuracy_m ? ` (±${Math.round(Number(r.record.location_accuracy_m))} m)` : ""}</a> : <span className="text-gray-400">—</span>}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        {r.record && <button onClick={() => openEdit(r.record!)} className="px-2.5 py-1 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-100">Correct</button>}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ---------------- report ---------------- */}
      {tab === "report" && isAdmin && (
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-x-auto">
          <div className="px-4 py-3 border-b border-gray-100 text-sm text-gray-500">{summary ? `${summary.working_days} working days between ${fmtDay(summary.from_date)} and ${fmtDay(summary.to_date)}` : "Loading…"}</div>
          <table className="w-full min-w-[820px]">
            <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600">
              <tr><th className="px-4 py-3">Employee</th><th className="px-4 py-3 text-right">Working days</th><th className="px-4 py-3 text-right">Present</th><th className="px-4 py-3 text-right">Late</th><th className="px-4 py-3 text-right">Absent</th><th className="px-4 py-3 text-right">Hours</th><th className="px-4 py-3 text-right">Avg / day</th><th className="px-4 py-3 text-right">Rate</th></tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {(summary?.rows ?? []).map((r) => (
                <tr key={r.user_id} className="hover:bg-gray-50/80">
                  <td className="px-4 py-2.5"><p className="text-gray-900 font-medium">{r.full_name || r.email}</p><p className="text-xs text-gray-500">{r.employment_type?.replace("_", "-") || r.email}</p></td>
                  <td className="px-4 py-2.5 text-right text-gray-600">{r.working_days}</td>
                  <td className="px-4 py-2.5 text-right text-green-700">{r.present_days}</td>
                  <td className="px-4 py-2.5 text-right text-amber-700">{r.late_days}</td>
                  <td className="px-4 py-2.5 text-right text-red-600">{r.absent_days}</td>
                  <td className="px-4 py-2.5 text-right text-gray-600">{r.total_hours}</td>
                  <td className="px-4 py-2.5 text-right text-gray-600">{r.avg_hours ?? "—"}</td>
                  <td className="px-4 py-2.5 text-right">
                    {r.attendance_rate != null ? (
                      <span className={`font-medium ${r.attendance_rate >= 0.9 ? "text-green-700" : r.attendance_rate >= 0.75 ? "text-amber-700" : "text-red-600"}`}>{Math.round(r.attendance_rate * 100)}%</span>
                    ) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ---------------- records ---------------- */}
      {tab === "records" && isAdmin && (
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-x-auto">
          <table className="w-full min-w-[900px]">
            <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600">
              <tr><th className="px-4 py-3">Day</th><th className="px-4 py-3">Employee</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">In</th><th className="px-4 py-3">Out</th><th className="px-4 py-3">Hours</th><th className="px-4 py-3">IP</th><th className="px-4 py-3">Location</th><th className="px-4 py-3 text-right">Actions</th></tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {records.map((r) => {
                const link = mapsLink(r);
                return (
                  <tr key={r.id} className="hover:bg-gray-50/80">
                    <td className="px-4 py-2.5 text-gray-800 whitespace-nowrap">{fmtDay(r.work_date)}</td>
                    <td className="px-4 py-2.5 text-gray-900">{r.user_name || r.user_email}</td>
                    <td className="px-4 py-2.5"><AttendanceStatusChip status={r.status} /></td>
                    <td className="px-4 py-2.5 text-gray-600">{fmtTime(r.check_in_at)}</td>
                    <td className="px-4 py-2.5 text-gray-600">{fmtTime(r.check_out_at)}</td>
                    <td className="px-4 py-2.5 text-gray-600">{r.check_out_at ? `${r.hours} h` : "—"}</td>
                    <td className="px-4 py-2.5 text-gray-600 text-sm font-mono">{r.ip_address || "—"}</td>
                    <td className="px-4 py-2.5 text-sm">{link ? <a href={link} target="_blank" rel="noreferrer" className="text-primary hover:underline">Map</a> : "—"}</td>
                    <td className="px-4 py-2.5 text-right whitespace-nowrap">
                      <button onClick={() => openEdit(r)} className="px-2.5 py-1 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-100">Correct</button>
                      <button onClick={() => remove(r)} className="px-2.5 py-1 rounded-lg text-xs font-medium text-red-600 hover:bg-red-50">Delete</button>
                    </td>
                  </tr>
                );
              })}
              {records.length === 0 && <tr><td colSpan={9} className="px-4 py-6 text-center text-sm text-gray-400">No records in this range.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {/* ---------------- correction modal ---------------- */}
      {edit && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-10 p-4" onClick={() => setEdit(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-gray-900">Correct record</h2>
            <p className="text-sm text-gray-500 mt-1">{edit.user_name || edit.user_email} · {fmtDay(edit.work_date)}</p>
            <div className="space-y-3 mt-4">
              <div><label className="block text-xs font-medium text-gray-500 mb-1">Check in</label><input type="datetime-local" className={`${inputClass} w-full`} value={editForm.check_in} onChange={(e) => setEditForm((f) => ({ ...f, check_in: e.target.value }))} /></div>
              <div><label className="block text-xs font-medium text-gray-500 mb-1">Check out (empty = still in)</label><input type="datetime-local" className={`${inputClass} w-full`} value={editForm.check_out} onChange={(e) => setEditForm((f) => ({ ...f, check_out: e.target.value }))} /></div>
              <div><label className="block text-xs font-medium text-gray-500 mb-1">Status</label>
                <select className={`${inputClass} w-full`} value={editForm.status} onChange={(e) => setEditForm((f) => ({ ...f, status: e.target.value }))}><option value="present">Present</option><option value="late">Late</option></select>
              </div>
              <div><label className="block text-xs font-medium text-gray-500 mb-1">Note</label><input className={`${inputClass} w-full`} value={editForm.note} onChange={(e) => setEditForm((f) => ({ ...f, note: e.target.value }))} placeholder="Reason for the correction" /></div>
            </div>
            <div className="flex items-center justify-between mt-5">
              <button onClick={() => remove(edit)} className="px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg">Delete</button>
              <div className="flex gap-2">
                <button onClick={() => setEdit(null)} className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">Cancel</button>
                <button disabled={busy} onClick={saveEdit} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover disabled:opacity-50">{busy ? "Saving…" : "Save"}</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
