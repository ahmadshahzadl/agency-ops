import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "@/store/auth";
import {
  getMyAttendance, checkIn, checkOut, getBrowserPosition, getTodayBoard, getAttendanceSummary,
  fmtTime, type AttendanceMe, type TodayBoard, type AttendanceSummary,
} from "@/api/attendance";

export function AttendanceStatusChip({ status }: { status: "present" | "late" | "absent" | "off" | "not_marked" }) {
  const map: Record<string, { cls: string; label: string }> = {
    present: { cls: "bg-green-50 text-green-700 border-green-200", label: "Present" },
    late: { cls: "bg-amber-50 text-amber-700 border-amber-200", label: "Late" },
    absent: { cls: "bg-red-50 text-red-700 border-red-200", label: "Absent" },
    off: { cls: "bg-gray-50 text-gray-500 border-gray-200", label: "Off" },
    not_marked: { cls: "bg-gray-50 text-gray-500 border-dashed border-gray-300", label: "Not marked" },
  };
  const m = map[status] ?? map.off;
  return <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${m.cls}`}>{m.label}</span>;
}

/** The employee's own check-in card. Interns are only marked; everyone else also leaves IP and a location. */
export function CheckInCard({ me, onChange, compact = false }: { me: AttendanceMe; onChange: () => void; compact?: boolean }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [locating, setLocating] = useState(false);
  const today = me.today;

  const doCheckIn = async () => {
    setBusy(true); setError(null);
    try {
      let pos: { latitude: number; longitude: number; accuracy_m: number } | undefined;
      if (me.captures_location) {
        setLocating(true);
        pos = await getBrowserPosition();
        setLocating(false);
      }
      await checkIn(pos ?? {});
      onChange();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not check in");
    } finally { setBusy(false); setLocating(false); }
  };

  const doCheckOut = async () => {
    setBusy(true); setError(null);
    try { await checkOut(); onChange(); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not check out"); }
    finally { setBusy(false); }
  };

  const nowLabel = new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });

  return (
    <div className="rounded-xl bg-white border border-gray-100 shadow-sm p-5">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-xs uppercase tracking-wide text-gray-400">My attendance</p>
          <p className="text-lg font-semibold text-gray-900 mt-0.5">{nowLabel}</p>
          <div className="mt-2 flex items-center gap-2 flex-wrap text-sm text-gray-600">
            {today ? (
              <>
                <AttendanceStatusChip status={today.status} />
                <span>In {fmtTime(today.check_in_at)}</span>
                {today.check_out_at ? <span>· Out {fmtTime(today.check_out_at)} · {today.hours} h</span> : <span>· {today.hours} h so far</span>}
              </>
            ) : (
              <>
                <AttendanceStatusChip status="not_marked" />
                <span>Start time {me.start_time} ({me.timezone})</span>
              </>
            )}
          </div>
          {!compact && (
            <p className="text-xs text-gray-400 mt-2">
              {me.captures_location
                ? "Checking in records your IP address and, if you allow it, your location."
                : "Interns only mark the day. No location or IP is stored."}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!today && (
            <button disabled={busy} onClick={doCheckIn} className="px-4 py-2 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover disabled:opacity-50">
              {locating ? "Getting location…" : busy ? "Checking in…" : "Check in"}
            </button>
          )}
          {today && !today.check_out_at && (
            <button disabled={busy} onClick={doCheckOut} className="px-4 py-2 rounded-lg bg-gray-900 text-white text-sm font-medium hover:bg-gray-800 disabled:opacity-50">
              {busy ? "Checking out…" : "Check out"}
            </button>
          )}
          {today?.check_out_at && <span className="text-sm text-gray-500">Day complete</span>}
          {!compact && <Link to="/attendance" className="px-3 py-2 rounded-lg text-sm font-medium text-gray-600 hover:bg-gray-100">History</Link>}
        </div>
      </div>
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      {!compact && (
        <p className="mt-3 text-xs text-gray-500">Last 30 days: {me.present_days_30} on time · {me.late_days_30} late</p>
      )}
    </div>
  );
}

/** Dashboard block: own check-in for everyone, plus today's board and the 30-day summary for admins. */
export function AttendancePanel() {
  const { user, hasPermission } = useAuth();
  const isAdmin = hasPermission("attendance:manage");
  const [me, setMe] = useState<AttendanceMe | null>(null);
  const [board, setBoard] = useState<TodayBoard | null>(null);
  const [summary, setSummary] = useState<AttendanceSummary | null>(null);

  const load = useCallback(() => {
    getMyAttendance(30).then(setMe).catch(() => setMe(null));
    if (isAdmin) {
      getTodayBoard().then(setBoard).catch(() => setBoard(null));
      getAttendanceSummary({}).then(setSummary).catch(() => setSummary(null));
    }
  }, [isAdmin]);

  useEffect(() => { load(); }, [load]);

  if (!user || user.is_client) return null;
  if (!me && !isAdmin) return null;

  const notIn = board ? board.rows.filter((r) => r.status === "absent") : [];
  const lateRows = board ? board.rows.filter((r) => r.status === "late") : [];
  const worst = summary ? summary.rows.filter((r) => r.working_days > 0).slice(0, 5) : [];

  return (
    <div className="space-y-4">
      {me && <CheckInCard me={me} onChange={load} compact={isAdmin} />}
      {isAdmin && board && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <div className="rounded-xl bg-white border border-gray-100 shadow-sm p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-gray-400">Attendance today</p>
                <p className="text-sm text-gray-500 mt-0.5">{board.is_working_day ? "Working day" : "Not a working day"}</p>
              </div>
              <Link to="/attendance" className="text-sm font-medium text-primary hover:underline">Full report</Link>
            </div>
            <div className="grid grid-cols-3 gap-3 mt-4">
              <div className="rounded-lg bg-green-50 p-3"><p className="text-2xl font-semibold text-green-700">{board.present}</p><p className="text-xs text-green-700/80">On time</p></div>
              <div className="rounded-lg bg-amber-50 p-3"><p className="text-2xl font-semibold text-amber-700">{board.late}</p><p className="text-xs text-amber-700/80">Late</p></div>
              <div className="rounded-lg bg-red-50 p-3"><p className="text-2xl font-semibold text-red-700">{board.absent}</p><p className="text-xs text-red-700/80">Not checked in</p></div>
            </div>
            {(notIn.length > 0 || lateRows.length > 0) && (
              <div className="mt-4 space-y-1.5 text-sm">
                {lateRows.slice(0, 5).map((r) => (
                  <p key={r.user_id} className="flex items-center justify-between gap-2 text-gray-700">
                    <span>{r.full_name || r.email}</span>
                    <span className="text-amber-700 text-xs">late · in {fmtTime(r.record?.check_in_at)}</span>
                  </p>
                ))}
                {notIn.slice(0, 6).map((r) => (
                  <p key={r.user_id} className="flex items-center justify-between gap-2 text-gray-700">
                    <span>{r.full_name || r.email}</span>
                    <span className="text-red-600 text-xs">not checked in</span>
                  </p>
                ))}
                {notIn.length > 6 && <p className="text-xs text-gray-400">and {notIn.length - 6} more</p>}
              </div>
            )}
          </div>
          <div className="rounded-xl bg-white border border-gray-100 shadow-sm p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-wide text-gray-400">Last 30 days</p>
                <p className="text-sm text-gray-500 mt-0.5">{summary ? `${summary.working_days} working days · most absences first` : "Loading…"}</p>
              </div>
            </div>
            {summary && (
              <table className="w-full mt-3 text-sm">
                <thead className="text-left text-xs text-gray-400">
                  <tr><th className="py-1 font-medium">Employee</th><th className="py-1 font-medium text-right">Present</th><th className="py-1 font-medium text-right">Late</th><th className="py-1 font-medium text-right">Absent</th><th className="py-1 font-medium text-right">Rate</th></tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {worst.map((r) => (
                    <tr key={r.user_id}>
                      <td className="py-1.5 text-gray-800">{r.full_name || r.email}{r.employment_type === "intern" && <span className="ml-1 text-[10px] text-gray-400">intern</span>}</td>
                      <td className="py-1.5 text-right text-gray-700">{r.present_days}</td>
                      <td className="py-1.5 text-right text-amber-700">{r.late_days}</td>
                      <td className="py-1.5 text-right text-red-600">{r.absent_days}</td>
                      <td className="py-1.5 text-right text-gray-700">{r.attendance_rate != null ? `${Math.round(r.attendance_rate * 100)}%` : "—"}</td>
                    </tr>
                  ))}
                  {worst.length === 0 && <tr><td colSpan={5} className="py-3 text-center text-gray-400">No staff with working days in range.</td></tr>}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
