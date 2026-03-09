import { useState, useRef, useEffect } from "react";
import type { UserList } from "@/api/users";

function userLabel(u: UserList) {
  return u.full_name?.trim() || u.email;
}

interface SearchableUserMultiSelectProps {
  users: UserList[];
  value: string[];
  onChange: (userIds: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
  variant?: "dark" | "light";
}

export function SearchableUserMultiSelect({
  users,
  value,
  onChange,
  placeholder = "Search and add attendees...",
  disabled = false,
  variant = "dark",
}: SearchableUserMultiSelectProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedUsers = value
    .map((id) => users.find((u) => u.id === id))
    .filter(Boolean) as UserList[];
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

  const add = (id: string) => {
    if (!value.includes(id)) onChange([...value, id]);
  };
  const remove = (id: string) => {
    onChange(value.filter((x) => x !== id));
  };

  const isLight = variant === "light";
  const triggerClass = isLight
    ? "w-full min-h-[2.5rem] px-3 py-2 rounded-lg border border-gray-300 bg-white text-gray-900 text-left flex items-center flex-wrap gap-2 disabled:opacity-50 focus:ring-2 focus:ring-primary/20 focus:border-primary"
    : "w-full min-h-[2.5rem] px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-left text-white flex items-center flex-wrap gap-2 disabled:opacity-50";
  const tagClass = isLight
    ? "inline-flex items-center gap-1 px-2 py-0.5 rounded bg-gray-100 text-gray-800 text-sm"
    : "inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-600 text-sm";
  const placeholderClass = isLight ? "text-gray-500" : "text-slate-500";
  const dropdownClass = isLight
    ? "absolute z-20 mt-1 w-full rounded-lg border border-gray-200 bg-white shadow-lg overflow-hidden"
    : "absolute z-20 mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 shadow-lg overflow-hidden";
  const searchInputClass = isLight
    ? "w-full px-3 py-2 border-b border-gray-200 text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-primary"
    : "w-full px-3 py-2 bg-slate-700 border-b border-slate-600 text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-primary";
  const optionClass = (selected: boolean) =>
    isLight
      ? `w-full px-3 py-2 text-left hover:bg-gray-100 flex items-center justify-between ${selected ? "bg-gray-100 text-gray-900 font-medium" : "text-gray-700"}`
      : `w-full px-3 py-2 text-left hover:bg-slate-700 flex items-center justify-between ${selected ? "bg-slate-600 text-white" : "text-slate-300"}`;

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => !disabled && setOpen((o) => !o)}
        disabled={disabled}
        className={triggerClass}
      >
        {selectedUsers.length > 0 ? (
          selectedUsers.map((u) => (
            <span key={u.id} className={tagClass}>
              {userLabel(u)}
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); remove(u.id); }}
                className={isLight ? "hover:text-red-600" : "hover:text-red-300"}
                aria-label="Remove"
              >
                ×
              </button>
            </span>
          ))
        ) : (
          <span className={placeholderClass}>{placeholder}</span>
        )}
        <span className={`ml-auto text-sm ${isLight ? "text-gray-400" : "text-slate-400"}`}>{open ? "▲" : "▼"}</span>
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
            {filtered.length === 0 ? (
              <div className={`px-3 py-2 text-sm ${isLight ? "text-gray-500" : "text-slate-500"}`}>No users match</div>
            ) : (
              filtered.map((u) => (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => add(u.id)}
                  className={optionClass(value.includes(u.id))}
                >
                  <span>{userLabel(u)}</span>
                  {value.includes(u.id) && <span className="text-primary">✓</span>}
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
