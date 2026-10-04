import { useMemo } from "react";

export type DateRange = { from: string; to: string };
export type RangePreset = "this_month" | "last_month" | "this_quarter" | "this_year" | "all" | "custom";

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

/** The from/to dates for a preset, in local time. "all" is an empty range (no filter). */
export function rangeForPreset(preset: RangePreset, today = new Date()): DateRange {
  const y = today.getFullYear();
  const m = today.getMonth();
  switch (preset) {
    case "this_month":
      return { from: iso(new Date(y, m, 1)), to: iso(new Date(y, m + 1, 0)) };
    case "last_month":
      return { from: iso(new Date(y, m - 1, 1)), to: iso(new Date(y, m, 0)) };
    case "this_quarter": {
      const q = Math.floor(m / 3) * 3;
      return { from: iso(new Date(y, q, 1)), to: iso(new Date(y, q + 3, 0)) };
    }
    case "this_year":
      return { from: iso(new Date(y, 0, 1)), to: iso(new Date(y, 11, 31)) };
    default:
      return { from: "", to: "" };
  }
}

export function presetForRange(range: DateRange): RangePreset {
  if (!range.from && !range.to) return "all";
  for (const p of ["this_month", "last_month", "this_quarter", "this_year"] as RangePreset[]) {
    const r = rangeForPreset(p);
    if (r.from === range.from && r.to === range.to) return p;
  }
  return "custom";
}

const PRESETS: { key: RangePreset; label: string }[] = [
  { key: "this_month", label: "This month" },
  { key: "last_month", label: "Last month" },
  { key: "this_quarter", label: "This quarter" },
  { key: "this_year", label: "This year" },
  { key: "all", label: "All time" },
];

/** Preset pills plus from/to inputs. Controlled: the parent owns the range and refetches on change. */
export function DateRangeFilter({ value, onChange, className = "" }: { value: DateRange; onChange: (r: DateRange) => void; className?: string }) {
  const active = useMemo(() => presetForRange(value), [value]);
  const input = "px-2.5 py-1.5 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm";
  return (
    <div className={`flex items-center gap-2 flex-wrap ${className}`}>
      <div className="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-0.5">
        {PRESETS.map((p) => (
          <button
            key={p.key}
            type="button"
            onClick={() => onChange(rangeForPreset(p.key))}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${active === p.key ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-800"}`}
          >
            {p.label}
          </button>
        ))}
      </div>
      <input type="date" className={input} value={value.from} max={value.to || undefined} onChange={(e) => onChange({ ...value, from: e.target.value })} aria-label="From date" />
      <span className="text-xs text-gray-400">to</span>
      <input type="date" className={input} value={value.to} min={value.from || undefined} onChange={(e) => onChange({ ...value, to: e.target.value })} aria-label="To date" />
    </div>
  );
}

/** Remember the last range per page so coming back keeps the view. */
export function loadRange(key: string, fallback: RangePreset = "this_month"): DateRange {
  try {
    const raw = localStorage.getItem(`range:${key}`);
    if (raw) {
      const parsed = JSON.parse(raw) as { preset?: RangePreset; from?: string; to?: string };
      if (parsed.preset && parsed.preset !== "custom") return rangeForPreset(parsed.preset);
      if (parsed.from !== undefined && parsed.to !== undefined) return { from: parsed.from, to: parsed.to };
    }
  } catch { /* ignore */ }
  return rangeForPreset(fallback);
}

export function saveRange(key: string, range: DateRange): void {
  try {
    localStorage.setItem(`range:${key}`, JSON.stringify({ preset: presetForRange(range), from: range.from, to: range.to }));
  } catch { /* ignore */ }
}
