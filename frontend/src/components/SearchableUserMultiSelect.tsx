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
}

export function SearchableUserMultiSelect({
  users,
  value,
  onChange,
  placeholder = "Search and add attendees...",
  disabled = false,
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

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => !disabled && setOpen((o) => !o)}
        disabled={disabled}
        className="w-full min-h-[2.5rem] px-3 py-2 rounded-lg bg-slate-700 border border-slate-600 text-left text-white flex items-center flex-wrap gap-2 disabled:opacity-50"
      >
        {selectedUsers.length > 0 ? (
          selectedUsers.map((u) => (
            <span
              key={u.id}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-600 text-sm"
            >
              {userLabel(u)}
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  remove(u.id);
                }}
                className="hover:text-red-300"
                aria-label="Remove"
              >
                ×
              </button>
            </span>
          ))
        ) : (
          <span className="text-slate-500">{placeholder}</span>
        )}
        <span className="ml-auto text-slate-400 text-sm">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="absolute z-20 mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 shadow-lg overflow-hidden">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name or email..."
            className="w-full px-3 py-2 bg-slate-700 border-b border-slate-600 text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-primary"
            autoFocus
          />
          <div className="max-h-48 overflow-y-auto">
            {filtered.length === 0 ? (
              <div className="px-3 py-2 text-slate-500 text-sm">No users match</div>
            ) : (
              filtered.map((u) => (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => add(u.id)}
                  className={`w-full px-3 py-2 text-left hover:bg-slate-700 flex items-center justify-between ${
                    value.includes(u.id) ? "bg-slate-600 text-white" : "text-slate-300"
                  }`}
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
