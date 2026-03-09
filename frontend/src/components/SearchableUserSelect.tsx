import { useState, useRef, useEffect } from "react";
import type { UserList } from "@/api/users";

function userLabel(u: UserList) {
  return u.full_name?.trim() || u.email;
}

interface SearchableUserSelectProps {
  users: UserList[];
  value: string | null;
  onChange: (userId: string | null) => void;
  placeholder?: string;
  disabled?: boolean;
  variant?: "dark" | "light";
}

export function SearchableUserSelect({
  users,
  value,
  onChange,
  placeholder = "Search and select user...",
  disabled = false,
  variant = "dark",
}: SearchableUserSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  const selected = value ? users.find((u) => u.id === value) : null;
  const searchLower = search.trim().toLowerCase();
  const filtered =
    searchLower === ""
      ? users
      : users.filter(
          (u) =>
            (u.full_name ?? "").toLowerCase().includes(searchLower) ||
            u.email.toLowerCase().includes(searchLower)
        );

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const isLight = variant === "light";
  const triggerClass = isLight
    ? "w-full px-3 py-2 rounded-lg border border-gray-300 bg-white text-gray-900 text-left flex items-center justify-between gap-2 disabled:opacity-50 focus:ring-2 focus:ring-primary/20 focus:border-primary"
    : "w-full px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-left text-white flex items-center justify-between gap-2 disabled:opacity-50";
  const triggerPlaceholderClass = isLight ? "text-gray-500" : "text-slate-500";
  const dropdownClass = isLight
    ? "absolute z-20 mt-1 w-full rounded-lg border border-gray-200 bg-white shadow-lg overflow-hidden"
    : "absolute z-20 mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 shadow-lg overflow-hidden";
  const searchInputClass = isLight
    ? "w-full px-3 py-2 border-b border-gray-200 text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-primary"
    : "w-full px-3 py-2 bg-slate-700 border-b border-slate-600 text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-primary";
  const unassignedClass = isLight
    ? "w-full px-3 py-2 text-left text-gray-500 hover:bg-gray-100"
    : "w-full px-3 py-2 text-left text-slate-400 hover:bg-slate-700";
  const optionClass = (isSelected: boolean) =>
    isLight
      ? `w-full px-3 py-2 text-left hover:bg-gray-100 ${isSelected ? "bg-gray-100 text-gray-900 font-medium" : "text-gray-700"}`
      : `w-full px-3 py-2 text-left hover:bg-slate-700 ${isSelected ? "bg-slate-600 text-white" : "text-slate-300"}`;

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => !disabled && setOpen((o) => !o)}
        disabled={disabled}
        className={triggerClass}
      >
        <span className={selected ? (isLight ? "text-gray-900" : "text-white") : triggerPlaceholderClass}>
          {selected ? userLabel(selected) : placeholder}
        </span>
        <span className={isLight ? "text-gray-400 text-sm" : "text-slate-400 text-sm"}>{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className={dropdownClass}>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or email..."
            className={searchInputClass}
            autoFocus
          />
          <div className="max-h-48 overflow-y-auto">
            <button type="button" onClick={() => { onChange(null); setOpen(false); setSearch(""); }} className={unassignedClass}>
              — Unassigned —
            </button>
            {filtered.length === 0 ? (
              <div className={`px-3 py-2 text-sm ${isLight ? "text-gray-500" : "text-slate-500"}`}>No users match</div>
            ) : (
              filtered.map((u) => (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => { onChange(u.id); setOpen(false); setSearch(""); }}
                  className={optionClass(value === u.id)}
                >
                  {userLabel(u)}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
