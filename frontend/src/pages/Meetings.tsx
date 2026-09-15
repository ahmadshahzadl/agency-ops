import { useEffect, useState } from "react";
import { listMeetings, createMeeting, updateMeeting, deleteMeeting, assignMeeting, listBookingAssignees, type Meeting, type BookingAssignee } from "@/api/meetings";
import { listProjectNames } from "@/api/projects";
import { listAssignableUsers, type UserList } from "@/api/users";
import { SearchableUserMultiSelect } from "@/components/SearchableUserMultiSelect";
import { useAuth } from "@/store/auth";
import { NotesSection } from "@/components/NotesSection";
import { AttachmentsSection } from "@/components/AttachmentsSection";
import { useModal } from "@/contexts/ModalContext";
import { BulkActionsBar } from "@/components/BulkActionsBar";

export default function MeetingsPage() {
  const { showConfirm, showAlert } = useModal();
  const { hasPermission, user } = useAuth();
  const canBulk = hasPermission("admin:all");
  const canWrite = hasPermission("meetings:write");
  const canAssign = hasPermission("admin:all") || hasPermission("bookings:manage");
  const [items, setItems] = useState<Meeting[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleting, setBulkDeleting] = useState(false);
  const [projectNames, setProjectNames] = useState<{ id: string; name: string }[]>([]);
  const [assignableUsers, setAssignableUsers] = useState<UserList[]>([]);
  const [loading, setLoading] = useState(true);
  const [projectFilter, setProjectFilter] = useState("");
  const [searchText, setSearchText] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [assignedFilter, setAssignedFilter] = useState("");
  const [assignees, setAssignees] = useState<BookingAssignee[]>([]);
  const [assigning, setAssigning] = useState<string | null>(null);
  const [modal, setModal] = useState<"new" | Meeting | null>(null);
  const [form, setForm] = useState({
    title: "",
    description: "",
    start_at: "",
    end_at: "",
    location: "",
    attendee_ids: [] as string[],
  });

  const load = () => {
    listProjectNames().then(setProjectNames).catch(() => setProjectNames([]));
    const params = {
      ...(projectFilter ? { project_id: projectFilter } : {}),
      ...(sourceFilter ? { source: sourceFilter } : {}),
      ...(assignedFilter ? { assigned: assignedFilter } : {}),
    };
    listMeetings(params)
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, [projectFilter, sourceFilter, assignedFilter]);

  useEffect(() => {
    if (canAssign) listBookingAssignees().then(setAssignees).catch(() => setAssignees([]));
  }, [canAssign]);

  const assign = async (m: Meeting, userId: string | null) => {
    setAssigning(m.id);
    try {
      const updated = await assignMeeting(m.id, userId);
      setItems((list) => list.map((x) => (x.id === m.id ? updated : x)));
      if (modal && modal !== "new" && modal.id === m.id) setModal(updated);
    } catch (e: unknown) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed to assign" });
    } finally {
      setAssigning(null);
    }
  };

  useEffect(() => {
    const onMeetingsUpdated = () => load();
    window.addEventListener("ws:meetings_updated", onMeetingsUpdated);
    return () => window.removeEventListener("ws:meetings_updated", onMeetingsUpdated);
  }, []);

  useEffect(() => {
    if (canWrite) listAssignableUsers().then(setAssignableUsers).catch(() => {});
  }, [canWrite]);

  const openNew = () => {
    const now = new Date();
    const start = new Date(now);
    start.setHours(10, 0, 0, 0);
    const end = new Date(now);
    end.setHours(11, 0, 0, 0);
    setForm({
      title: "",
      description: "",
      start_at: start.toISOString().slice(0, 16),
      end_at: end.toISOString().slice(0, 16),
      location: "",
      attendee_ids: [],
    });
    setModal("new");
  };
  const openEdit = (m: Meeting) => {
    setForm({
      title: m.title,
      description: m.description || "",
      start_at: m.start_at.slice(0, 16),
      end_at: m.end_at.slice(0, 16),
      location: m.location || "",
      attendee_ids: m.attendee_ids ?? [],
    });
    setModal(m);
  };

  const save = async () => {
    if (modal === null) return;
    const basePayload = {
      title: form.title,
      description: form.description || undefined,
      start_at: new Date(form.start_at).toISOString(),
      end_at: new Date(form.end_at).toISOString(),
      location: form.location || undefined,
      attendee_ids: form.attendee_ids,
    };
    try {
      if (modal === "new") {
        await createMeeting(basePayload);
      } else {
        await updateMeeting(modal.id, basePayload);
      }
      setModal(null);
      load();
    } catch (e: unknown) {
      showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
    }
  };

  const remove = (id: string) => {
    showConfirm({
      title: "Delete meeting",
      message: "Delete this meeting?",
      confirmLabel: "Delete",
      variant: "danger",
      onConfirm: async () => {
        try {
          await deleteMeeting(id);
          setModal(null);
          setSelectedIds((s) => {
            const next = new Set(s);
            next.delete(id);
            return next;
          });
          load();
        } catch (e: unknown) {
          showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed" });
          throw e;
        }
      },
    });
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };
  const toggleSelectAll = () => {
    if (selectedIds.size === filteredItems.length) setSelectedIds(new Set());
    else setSelectedIds(new Set(filteredItems.map((m) => m.id)));
  };
  const bulkDelete = () => {
    const ids = Array.from(selectedIds);
    showConfirm({
      title: "Delete meetings",
      message: `Delete ${ids.length} meeting(s)? This cannot be undone.`,
      confirmLabel: "Delete all",
      variant: "danger",
      onConfirm: async () => {
        setBulkDeleting(true);
        try {
          for (const id of ids) {
            try {
              await deleteMeeting(id);
            } catch (e) {
              showAlert({ title: "Error", message: e instanceof Error ? e.message : "Failed to delete meeting" });
              throw e;
            }
          }
          setSelectedIds(new Set());
          setModal(null);
          load();
        } finally {
          setBulkDeleting(false);
        }
      },
    });
  };

  const projectMap = Object.fromEntries(projectNames.map((p) => [p.id, p.name]));
  const searchLower = searchText.trim().toLowerCase();
  const filteredItems = searchLower
    ? items.filter(
        (m) =>
          (m.title ?? "").toLowerCase().includes(searchLower) ||
          (m.description ?? "").toLowerCase().includes(searchLower) ||
          (m.location ?? "").toLowerCase().includes(searchLower) ||
          (m.invitee_name ?? "").toLowerCase().includes(searchLower) ||
          (m.invitee_email ?? "").toLowerCase().includes(searchLower) ||
          (m.project_id && (projectMap[m.project_id] ?? "").toLowerCase().includes(searchLower))
      )
    : items;
  const inputClass = "w-full px-3 py-2 rounded-lg border border-gray-300 text-gray-900 focus:ring-2 focus:ring-primary/20 focus:border-primary";
  const labelClass = "block text-sm font-medium text-gray-700 mb-1";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <label className="text-sm font-medium text-gray-700">Project</label>
          <select
            value={projectFilter}
            onChange={(e) => setProjectFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[180px]"
          >
            <option value="">All projects</option>
            {projectNames.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <label className="text-sm font-medium text-gray-700">Search</label>
          <input
            type="search"
            placeholder="Title, description, location..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm min-w-[200px]"
          />
        </div>
        {canAssign && (
          <>
            <label className="text-sm font-medium text-gray-700">Type</label>
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm"
            >
              <option value="">All types</option>
              <option value="external">Bookings (website + Calendly)</option>
              <option value="website">Website</option>
              <option value="calendly">Calendly</option>
              <option value="manual">Manual</option>
            </select>
            <label className="text-sm font-medium text-gray-700">Owner</label>
            <select
              value={assignedFilter}
              onChange={(e) => setAssignedFilter(e.target.value)}
              className="px-3 py-2 rounded-lg border border-gray-300 text-gray-900 bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm"
            >
              <option value="">Anyone</option>
              <option value="unassigned">Unassigned</option>
              <option value="me">Mine</option>
              {assignees.filter((a) => a.id !== user?.id).map((a) => (
                <option key={a.id} value={a.id}>{a.full_name || a.email}</option>
              ))}
            </select>
          </>
        )}
        {canWrite && (
          <button
            onClick={openNew}
            className="px-4 py-2 rounded-lg bg-primary text-white font-medium hover:bg-primary-hover"
          >
            Add meeting
          </button>
        )}
      </div>

      {canBulk && (
        <BulkActionsBar
          selectedCount={selectedIds.size}
          entityName="meetings"
          onClear={() => setSelectedIds(new Set())}
          onDelete={bulkDelete}
          loading={bulkDeleting}
        />
      )}

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="rounded-xl bg-white border border-gray-100 shadow-sm overflow-x-auto">
          <table className="w-full min-w-[640px]">
            <thead className="bg-gray-50 text-left text-sm font-medium text-gray-600">
              <tr>
                {canBulk && (
                  <th className="px-4 py-3 w-10">
                    <input
                      type="checkbox"
                      checked={filteredItems.length > 0 && selectedIds.size === filteredItems.length}
                      onChange={toggleSelectAll}
                      className="rounded border-gray-300 text-primary focus:ring-primary/20"
                    />
                  </th>
                )}
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Source</th>
                <th className="px-4 py-3">Owner</th>
                <th className="px-4 py-3">Project</th>
                <th className="px-4 py-3">Start</th>
                <th className="px-4 py-3">End</th>
                {canWrite && <th className="px-4 py-3 w-24 text-right">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {filteredItems.map((m) => (
                <tr key={m.id} className={`hover:bg-gray-50/80 ${selectedIds.has(m.id) ? "bg-primary/5" : ""}`}>
                  {canBulk && (
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(m.id)}
                        onChange={() => toggleSelect(m.id)}
                        className="rounded border-gray-300 text-primary focus:ring-primary/20"
                      />
                    </td>
                  )}
                  <td className="px-4 py-3">
                    <div className={`font-medium ${m.status === "canceled" ? "text-gray-400 line-through" : "text-gray-900"}`}>{m.title}</div>
                    {m.invitee_email && (
                      <div className="text-xs text-gray-500 mt-0.5">
                        {m.company_name ? <span className="font-medium text-gray-700">{m.company_name} · </span> : null}
                        {m.invitee_name ? `${m.invitee_name} · ` : ""}
                        <a href={`mailto:${m.invitee_email}`} className="hover:text-primary" onClick={(e) => e.stopPropagation()}>{m.invitee_email}</a>
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {m.source === "website" ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-100">Website</span>
                      ) : m.source === "calendly" ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-100">Calendly</span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">Manual</span>
                      )}
                      {m.status === "canceled" && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-100" title={m.cancel_reason ?? undefined}>Canceled</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {canAssign && m.source !== "manual" ? (
                      <div className="flex items-center gap-1.5">
                        <select
                          value={m.assigned_to ?? ""}
                          disabled={assigning === m.id}
                          onChange={(e) => assign(m, e.target.value || null)}
                          onClick={(e) => e.stopPropagation()}
                          className={`px-2 py-1 rounded-lg border text-xs bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary min-w-[140px] ${m.assigned_to ? "border-gray-300 text-gray-800" : "border-amber-300 text-amber-800 bg-amber-50"}`}
                          title="Solutions engineer who owns this prospect"
                        >
                          <option value="">Unassigned</option>
                          {assignees.map((a) => (
                            <option key={a.id} value={a.id}>{a.full_name || a.email}</option>
                          ))}
                        </select>
                        {!m.assigned_to && user && assignees.some((a) => a.id === user.id) && (
                          <button type="button" onClick={() => assign(m, user.id)} disabled={assigning === m.id} className="text-xs text-primary hover:underline whitespace-nowrap">
                            Assign to me
                          </button>
                        )}
                      </div>
                    ) : (
                      <span className="text-sm">{m.assigned_to_name || (m.source !== "manual" ? <span className="text-amber-700">Unassigned</span> : "—")}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{m.project_id ? projectMap[m.project_id] || m.project_id : "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{new Date(m.start_at).toLocaleString()}</td>
                  <td className="px-4 py-3 text-gray-600">{new Date(m.end_at).toLocaleString()}</td>
                  {canWrite && (
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button type="button" onClick={() => openEdit(m)} title="Edit" className="p-1.5 rounded-lg text-gray-500 hover:text-primary hover:bg-gray-100 transition-colors">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                          </svg>
                        </button>
                        <button type="button" onClick={() => remove(m.id)} title="Delete" className="p-1.5 rounded-lg text-gray-500 hover:text-red-600 hover:bg-gray-100 transition-colors">
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {modal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-10" onClick={() => setModal(null)}>
          <div className="bg-white rounded-xl border border-gray-200 shadow-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-semibold text-gray-900 mb-4">{modal === "new" ? "New meeting" : "Edit meeting"}</h2>
            {modal !== "new" && ((modal as Meeting).source === "calendly" || (modal as Meeting).source === "website") && (
              <div className="mb-4 rounded-lg border border-blue-100 bg-blue-50/60 p-3 text-sm text-gray-700 space-y-1">
                <div className="font-medium text-blue-800">{(modal as Meeting).source === "website" ? "Booked on the website" : "Booked via Calendly"}</div>
                {(modal as Meeting).invitee_name || (modal as Meeting).invitee_email ? (
                  <div>
                    {(modal as Meeting).invitee_name}
                    {(modal as Meeting).invitee_email && (
                      <>
                        {(modal as Meeting).invitee_name ? " · " : ""}
                        <a href={`mailto:${(modal as Meeting).invitee_email}`} className="text-primary hover:underline">{(modal as Meeting).invitee_email}</a>
                      </>
                    )}
                  </div>
                ) : null}
                {(modal as Meeting).status === "canceled" && (
                  <div className="text-red-700">{(modal as Meeting).cancel_reason || "Canceled"}</div>
                )}
                {(modal as Meeting).company_name && (
                  <div>Company: <span className="font-medium">{(modal as Meeting).company_name}</span>{(modal as Meeting).lead_status ? <span className="text-gray-500"> · lead {(modal as Meeting).lead_status}</span> : null}</div>
                )}
                <div className="flex items-center gap-2 flex-wrap">
                  <span>Owner:</span>
                  {canAssign ? (
                    <select
                      value={(modal as Meeting).assigned_to ?? ""}
                      disabled={assigning === (modal as Meeting).id}
                      onChange={(e) => assign(modal as Meeting, e.target.value || null)}
                      className="px-2 py-1 rounded-lg border border-gray-300 text-xs bg-white focus:ring-2 focus:ring-primary/20 focus:border-primary"
                    >
                      <option value="">Unassigned</option>
                      {assignees.map((a) => (
                        <option key={a.id} value={a.id}>{a.full_name || a.email}</option>
                      ))}
                    </select>
                  ) : (
                    <span className="font-medium">{(modal as Meeting).assigned_to_name || "Unassigned"}</span>
                  )}
                </div>
                {(modal as Meeting).lead_id && (
                  <a href="/leads" className="text-primary hover:underline">Open in Leads</a>
                )}
                {(modal as Meeting).invitee_timezone && (
                  <div className="text-xs text-gray-500">Invitee timezone: {(modal as Meeting).invitee_timezone}</div>
                )}
                {(modal as Meeting).answers && Object.keys((modal as Meeting).answers ?? {}).length > 0 && (
                  <dl className="mt-1 space-y-0.5">
                    {Object.entries((modal as Meeting).answers ?? {}).map(([k, v]) => (
                      <div key={k} className="text-xs"><span className="text-gray-500">{k}:</span> <span className="text-gray-800 whitespace-pre-wrap">{String(v)}</span></div>
                    ))}
                  </dl>
                )}
                <div className="text-xs text-gray-500">
                  {(modal as Meeting).source === "website"
                    ? "The invitee can cancel or reschedule from the link in their confirmation email; changes sync here."
                    : "Time and invitee are managed in Calendly; a reschedule there arrives as a new booking."}
                </div>
              </div>
            )}
            <div className="space-y-3">
              <input
                placeholder="Title"
                value={form.title}
                onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                className={inputClass}
              />
              <textarea
                placeholder="Description"
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                className={inputClass}
                rows={2}
              />
              <div>
                <label className={labelClass}>Start</label>
                <input
                  type="datetime-local"
                  value={form.start_at}
                  onChange={(e) => setForm((f) => ({ ...f, start_at: e.target.value }))}
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>End</label>
                <input
                  type="datetime-local"
                  value={form.end_at}
                  onChange={(e) => setForm((f) => ({ ...f, end_at: e.target.value }))}
                  className={inputClass}
                />
              </div>
              <input
                placeholder="Location"
                value={form.location}
                onChange={(e) => setForm((f) => ({ ...f, location: e.target.value }))}
                className={inputClass}
              />
              <div>
                <label className={labelClass}>Assign attendees</label>
                <SearchableUserMultiSelect
                  users={assignableUsers}
                  value={form.attendee_ids}
                  onChange={(ids) => setForm((f) => ({ ...f, attendee_ids: ids }))}
                  placeholder="Search and add attendees..."
                  variant="light"
                />
              </div>
            </div>
            <NotesSection entityType="meeting" entityId={modal !== "new" ? (modal as Meeting).id : undefined} />
            <AttachmentsSection entityType="meeting" entityId={modal !== "new" ? (modal as Meeting).id : undefined} />
            <div className="flex justify-end gap-2 mt-4">
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
