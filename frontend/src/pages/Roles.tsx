import { useEffect, useMemo, useState } from "react";
import {
  listRoles,
  listPermissions,
  createRole,
  updateRole,
  deleteRole,
  type Role,
  type Permission,
} from "@/api/roles";
import { useModal } from "@/contexts/ModalContext";
import {
  PERMISSION_CATALOG,
  PAGES_BY_PERMISSION,
  visiblePagesFor,
  type CatalogPage,
  type CatalogPermission,
} from "@/lib/permissionCatalog";

/** A catalog page narrowed to the permissions that actually exist in the database. */
interface PageSection {
  page: string;
  route: string | null;
  navGate: string | null;
  note?: string;
  /** Permission rows: catalog label plus the database id to send to the API. */
  rows: { id: string; perm: CatalogPermission }[];
}

function buildSections(permissions: Permission[]): { sections: PageSection[]; extras: Permission[] } {
  const idByCode = new Map(permissions.map((p) => [p.code, p.id]));
  const known = new Set<string>();
  const sections: PageSection[] = [];

  for (const page of PERMISSION_CATALOG as CatalogPage[]) {
    const rows = page.permissions
      .filter((perm) => idByCode.has(perm.code))
      .map((perm) => {
        known.add(perm.code);
        return { id: idByCode.get(perm.code)!, perm };
      });
    sections.push({ page: page.page, route: page.route, navGate: page.navGate, note: page.note, rows });
  }

  const extras = permissions.filter((p) => !known.has(p.code)).sort((a, b) => a.code.localeCompare(b.code));
  return { sections, extras };
}

function Badge({ tone, children }: { tone: "write" | "warn" | "muted"; children: React.ReactNode }) {
  const tones = {
    write: "bg-amber-50 text-amber-700 border-amber-200",
    warn: "bg-red-50 text-red-700 border-red-200",
    muted: "bg-gray-100 text-gray-600 border-gray-200",
  };
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded border text-[10px] font-semibold uppercase tracking-wide ${tones[tone]}`}>
      {children}
    </span>
  );
}

export default function Roles() {
  const { showConfirm, showAlert } = useModal();
  const [items, setItems] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState<"new" | Role | null>(null);
  const [viewRole, setViewRole] = useState<Role | null>(null);
  const [form, setForm] = useState({
    name: "",
    description: "",
    permission_ids: [] as string[],
  });
  const [search, setSearch] = useState("");
  const [permSearch, setPermSearch] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [roleList, permList] = await Promise.all([listRoles(), listPermissions()]);
      setItems(roleList);
      setPermissions(permList);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const codeById = useMemo(
    () => new Map(permissions.map((p) => [p.id, p.code])),
    [permissions]
  );

  const { sections, extras } = useMemo(() => buildSections(permissions), [permissions]);

  const filteredItems = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (r) =>
        (r.name || "").toLowerCase().includes(q) ||
        (r.description || "").toLowerCase().includes(q)
    );
  }, [items, search]);

  /** Codes currently ticked in the form (what the role will hold after saving). */
  const selectedCodes = useMemo(() => {
    const set = new Set<string>();
    for (const id of form.permission_ids) {
      const code = codeById.get(id);
      if (code) set.add(code);
    }
    return set;
  }, [form.permission_ids, codeById]);

  const selectedPages = useMemo(() => visiblePagesFor(selectedCodes), [selectedCodes]);
  const isAdminAll = selectedCodes.has("admin:all");

  /** Sections matching the picker search (page name, label, code or detail). */
  const visibleSections = useMemo(() => {
    const q = permSearch.trim().toLowerCase();
    if (!q) return sections;
    return sections
      .map((s) => ({
        ...s,
        rows: s.page.toLowerCase().includes(q)
          ? s.rows
          : s.rows.filter(
              ({ perm }) =>
                perm.code.toLowerCase().includes(q) ||
                perm.label.toLowerCase().includes(q) ||
                perm.detail.toLowerCase().includes(q)
            ),
      }))
      .filter((s) => s.rows.length > 0);
  }, [sections, permSearch]);

  const visibleExtras = useMemo(() => {
    const q = permSearch.trim().toLowerCase();
    if (!q) return extras;
    return extras.filter((p) => p.code.toLowerCase().includes(q));
  }, [extras, permSearch]);

  const openNew = () => {
    setForm({ name: "", description: "", permission_ids: [] });
    setPermSearch("");
    setModal("new");
  };

  const openEdit = (r: Role) => {
    setForm({
      name: r.name,
      description: r.description || "",
      permission_ids: r.permission_ids || [],
    });
    setPermSearch("");
    setModal(r);
  };

  const openDuplicate = (r: Role) => {
    setForm({
      name: `Copy of ${r.name}`,
      description: r.description || "",
      permission_ids: r.permission_ids || [],
    });
    setPermSearch("");
    setModal("new");
  };

  const togglePermission = (id: string) => {
    setForm((f) => ({
      ...f,
      permission_ids: f.permission_ids.includes(id)
        ? f.permission_ids.filter((p) => p !== id)
        : [...f.permission_ids, id],
    }));
  };

  const setPageSelection = (section: PageSection, on: boolean) => {
    const ids = section.rows.map((r) => r.id);
    setForm((f) => ({
      ...f,
      permission_ids: on
        ? Array.from(new Set([...f.permission_ids, ...ids]))
        : f.permission_ids.filter((p) => !ids.includes(p)),
    }));
  };

  const save = async () => {
    if (modal === null) return;
    try {
      if (modal === "new") {
        await createRole({
          name: form.name,
          description: form.description || undefined,
          permission_ids: form.permission_ids.length ? form.permission_ids : undefined,
        });
      } else {
        await updateRole(modal.id, {
          name: form.name,
          description: form.description || undefined,
          permission_ids: form.permission_ids,
        });
      }
      setModal(null);
      load();
    } catch (e: unknown) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    }
  };

  const remove = (r: Role) => {
    showConfirm({
      title: "Delete role",
      message: `Delete role "${r.name}"? This cannot be undone.`,
      confirmLabel: "Delete",
      variant: "danger",
      onConfirm: async () => {
        try {
          await deleteRole(r.id);
          setModal(null);
          load();
        } catch (e: unknown) {
          showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed to delete role" });
          throw e;
        }
      },
    });
  };

  const inputClass = "w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";

  const codesOf = (r: Role) => {
    const set = new Set<string>();
    for (const id of r.permission_ids || []) {
      const code = codeById.get(id);
      if (code) set.add(code);
    }
    return set;
  };

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="relative flex-1 min-w-[180px] max-w-xs">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search roles by name or description..."
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-gray-300 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary/20 focus:border-primary"
          />
        </div>
        <button
          onClick={openNew}
          className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover whitespace-nowrap"
        >
          Add role
        </button>
      </div>

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-x-auto">
          <table className="w-full min-w-[760px]">
            <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Description</th>
                <th className="px-4 py-3">Permissions</th>
                <th className="px-4 py-3">Pages it can open</th>
                <th className="px-4 py-3 w-32 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    {search ? "No roles match your search." : "No roles yet."}
                  </td>
                </tr>
              ) : (
                filteredItems.map((r) => {
                  const codes = codesOf(r);
                  const pages = visiblePagesFor(codes);
                  return (
                    <tr key={r.id} className="hover:bg-gray-50/80 align-top">
                      <td className="px-4 py-3 font-medium text-gray-900">
                        {r.name}
                        {codes.has("admin:all") && (
                          <span className="ml-2 align-middle">
                            <Badge tone="warn">full access</Badge>
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-600">{r.description || "—"}</td>
                      <td className="px-4 py-3 text-gray-600 text-sm whitespace-nowrap">
                        {codes.size ? `${codes.size} of ${permissions.length}` : "none"}
                      </td>
                      <td className="px-4 py-3 text-gray-600 text-sm">
                        {pages.length === 0 ? (
                          "—"
                        ) : (
                          <span>
                            {pages.slice(0, 4).join(", ")}
                            {pages.length > 4 && (
                              <button
                                type="button"
                                onClick={() => setViewRole(r)}
                                className="ml-1 text-primary hover:underline"
                              >
                                +{pages.length - 4} more
                              </button>
                            )}
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            type="button"
                            onClick={() => setViewRole(r)}
                            title="View page-wise permissions"
                            className="p-1.5 rounded-lg text-gray-500 hover:text-primary hover:bg-gray-100 transition-colors"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                          </button>
                          <button
                            type="button"
                            onClick={() => openEdit(r)}
                            title="Edit"
                            className="p-1.5 rounded-lg text-gray-500 hover:text-primary hover:bg-gray-100 transition-colors"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                            </svg>
                          </button>
                          <button
                            type="button"
                            onClick={() => openDuplicate(r)}
                            title="Duplicate role"
                            className="p-1.5 rounded-lg text-gray-500 hover:text-emerald-600 hover:bg-gray-100 transition-colors"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h2m8 0h2a2 2 0 012 2v2m0 8V6a2 2 0 012-2h-2m-4-1v8m0 0v2m0-2v-2m0-2V9m0 2v2" />
                            </svg>
                          </button>
                          <button
                            type="button"
                            onClick={() => remove(r)}
                            title="Delete role"
                            className="p-1.5 rounded-lg text-gray-500 hover:text-red-600 hover:bg-gray-100 transition-colors"
                          >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Read-only page-wise view of one role */}
      {viewRole && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-10 p-4" onClick={() => setViewRole(null)}>
          <div
            className="bg-white rounded-xl border border-gray-200 shadow-lg w-full max-w-2xl max-h-[90vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-6 pt-6 pb-3 border-b border-gray-100">
              <h2 className="text-lg font-semibold text-gray-900">
                {viewRole.name} — page-wise permissions
              </h2>
              <p className="text-sm text-gray-500 mt-0.5">{viewRole.description || "No description."}</p>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              {(() => {
                const codes = codesOf(viewRole);
                if (codes.has("admin:all")) {
                  return (
                    <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                      This role holds <span className="font-mono">admin:all</span>, which satisfies every permission
                      check in the app: all pages plus Users, Teams, Roles and Booking pages.
                    </div>
                  );
                }
                if (codes.size === 0) {
                  return (
                    <p className="text-sm text-gray-500">
                      No permissions. The holder can sign in and reach only the always-visible screens: Overview (empty),
                      Attendance (own check-in), Messages and Settings.
                    </p>
                  );
                }
                const granted = sections
                  .map((s) => ({ ...s, rows: s.rows.filter(({ perm }) => codes.has(perm.code)) }))
                  .filter((s) => s.rows.length > 0);
                const extraCodes = Array.from(codes).filter((c) => !PAGES_BY_PERMISSION[c]);
                return (
                  <>
                    {granted.map((s) => (
                      <div key={s.page}>
                        <div className="flex items-baseline gap-2 flex-wrap">
                          <p className="text-sm font-semibold text-gray-900">{s.page}</p>
                          {s.route && <span className="text-xs text-gray-400 font-mono">{s.route}</span>}
                          {s.navGate && !codes.has(s.navGate) && (
                            <Badge tone="muted">sidebar link hidden (needs {s.navGate})</Badge>
                          )}
                        </div>
                        <ul className="mt-1 space-y-1">
                          {s.rows.map(({ perm }) => (
                            <li key={perm.code} className="text-sm text-gray-600 flex items-start gap-2">
                              <span className="text-emerald-600 mt-0.5">✓</span>
                              <span>
                                {perm.label} <span className="text-gray-400 font-mono text-xs">{perm.code}</span>
                                <br />
                                <span className="text-xs text-gray-500">{perm.detail}</span>
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                    {extraCodes.length > 0 && (
                      <div>
                        <p className="text-sm font-semibold text-gray-900">Other permissions</p>
                        <p className="text-sm text-gray-600 font-mono">{extraCodes.join(", ")}</p>
                      </div>
                    )}
                  </>
                );
              })()}
            </div>
            <div className="px-6 py-3 border-t border-gray-100 flex justify-end gap-2">
              <button
                onClick={() => {
                  const r = viewRole;
                  setViewRole(null);
                  openEdit(r);
                }}
                className="px-4 py-2 text-primary font-medium hover:underline"
              >
                Edit this role
              </button>
              <button onClick={() => setViewRole(null)} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover">
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {modal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-10 p-4" onClick={() => setModal(null)}>
          <div
            className="bg-white rounded-xl border border-gray-200 shadow-lg w-full max-w-3xl max-h-[92vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-6 pt-6 pb-4 border-b border-gray-100">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                {modal === "new" ? "New role" : `Edit role: ${modal.name}`}
              </h2>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className={labelClass}>Name</label>
                  <input
                    placeholder="e.g. designer"
                    value={form.name}
                    onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                    className={inputClass}
                  />
                </div>
                <div>
                  <label className={labelClass}>Description</label>
                  <input
                    placeholder="What this role is for"
                    value={form.description}
                    onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                    className={inputClass}
                  />
                </div>
              </div>
            </div>

            {/* Running summary of what the role will be able to open */}
            <div className="px-6 py-3 bg-gray-50 border-b border-gray-100">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <p className="text-sm text-gray-700">
                  <span className="font-semibold">{selectedCodes.size}</span> of {permissions.length} permissions ·{" "}
                  <span className="font-semibold">{selectedPages.length}</span> page
                  {selectedPages.length === 1 ? "" : "s"} in the sidebar
                </p>
                <div className="relative w-full sm:w-64">
                  <input
                    type="text"
                    value={permSearch}
                    onChange={(e) => setPermSearch(e.target.value)}
                    placeholder="Filter by page or permission..."
                    className="w-full px-3 py-1.5 rounded-lg border border-gray-300 text-sm text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  />
                </div>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {isAdminAll
                  ? "admin:all is selected — this role passes every permission check, so every page is open regardless of the boxes below."
                  : selectedPages.length > 0
                    ? `Will see: ${selectedPages.join(", ")}`
                    : "Will see only the always-visible screens: Overview, Attendance, Messages, Settings."}
              </p>
            </div>

            {/* Page-wise permission picker */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              {visibleSections.map((s) => {
                const allOn = s.rows.length > 0 && s.rows.every((r) => form.permission_ids.includes(r.id));
                const someOn = s.rows.some((r) => form.permission_ids.includes(r.id));
                return (
                  <div key={s.page} className="rounded-lg border border-gray-200">
                    <div className="flex items-start justify-between gap-3 px-3 py-2 bg-gray-50/80 border-b border-gray-200 rounded-t-lg">
                      <div className="min-w-0">
                        <div className="flex items-baseline gap-2 flex-wrap">
                          <p className="text-sm font-semibold text-gray-900">{s.page}</p>
                          {s.route && <span className="text-xs text-gray-400 font-mono">{s.route}</span>}
                          {s.navGate === null && s.route && <Badge tone="muted">always visible</Badge>}
                          {someOn && !allOn && <Badge tone="muted">partial</Badge>}
                        </div>
                        {s.note && <p className="text-xs text-gray-500 mt-0.5">{s.note}</p>}
                      </div>
                      {s.rows.length > 0 && (
                        <button
                          type="button"
                          onClick={() => setPageSelection(s, !allOn)}
                          className="shrink-0 text-xs font-medium text-primary hover:underline whitespace-nowrap"
                        >
                          {allOn ? "Clear page" : "Select all"}
                        </button>
                      )}
                    </div>
                    {s.rows.length === 0 ? (
                      <p className="px-3 py-2 text-xs text-gray-500">
                        No permission controls this screen — any signed-in internal user can open it.
                      </p>
                    ) : (
                      <div className="divide-y divide-gray-100">
                        {s.rows.map(({ id, perm }) => {
                          const alsoOn = (PAGES_BY_PERMISSION[perm.code] || []).filter((p) => p !== s.page);
                          return (
                            <label key={`${s.page}-${perm.code}`} className="flex items-start gap-3 px-3 py-2 cursor-pointer hover:bg-gray-50/60">
                              <input
                                type="checkbox"
                                checked={form.permission_ids.includes(id)}
                                onChange={() => togglePermission(id)}
                                className="mt-1 rounded border-gray-300 text-primary focus:ring-primary/20"
                              />
                              <span className="min-w-0">
                                <span className="flex items-center gap-2 flex-wrap">
                                  <span className="text-sm font-medium text-gray-800">{perm.label}</span>
                                  <span className="text-xs text-gray-400 font-mono">{perm.code}</span>
                                  {perm.write && <Badge tone="write">write</Badge>}
                                  {perm.sensitive && <Badge tone="warn">sensitive</Badge>}
                                </span>
                                <span className="block text-xs text-gray-500 mt-0.5">{perm.detail}</span>
                                {alsoOn.length > 0 && (
                                  <span className="block text-xs text-gray-400 mt-0.5">
                                    Same code also affects: {alsoOn.join(", ")}
                                  </span>
                                )}
                              </span>
                            </label>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}

              {visibleExtras.length > 0 && (
                <div className="rounded-lg border border-gray-200">
                  <div className="px-3 py-2 bg-gray-50/80 border-b border-gray-200 rounded-t-lg">
                    <p className="text-sm font-semibold text-gray-900">Other permissions</p>
                    <p className="text-xs text-gray-500 mt-0.5">
                      In the database but not yet mapped to a page in src/lib/permissionCatalog.ts.
                    </p>
                  </div>
                  <div className="px-3 py-2 flex flex-wrap gap-x-4 gap-y-2">
                    {visibleExtras.map((p) => (
                      <label key={p.id} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={form.permission_ids.includes(p.id)}
                          onChange={() => togglePermission(p.id)}
                          className="rounded border-gray-300 text-primary focus:ring-primary/20"
                        />
                        <span className="font-mono text-xs">{p.code}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {visibleSections.length === 0 && visibleExtras.length === 0 && (
                <p className="text-sm text-gray-500">No permission matches "{permSearch}".</p>
              )}
            </div>

            <div className="px-6 py-3 border-t border-gray-100 flex justify-end gap-2">
              <button onClick={() => setModal(null)} className="px-4 py-2 text-gray-600 hover:text-gray-900 font-medium">
                Cancel
              </button>
              <button onClick={save} className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover">
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
