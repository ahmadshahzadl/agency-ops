import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { DndContext, DragOverlay, PointerSensor, useDraggable, useDroppable, useSensor, useSensors, type DragEndEvent, type DragStartEvent } from "@dnd-kit/core";
import { useAuth } from "@/store/auth";
import { allowedTargets } from "@/lib/taskFlow";
import { listProjects, type Project } from "@/api/projects";
import { listBoards, createBoard, deleteBoard, listBoardTasks, addBoardMember, removeBoardMember, type Board } from "@/api/boards";
import { createTask, updateTask, deleteTask, type Task } from "@/api/tasks";
import { uploadAttachment } from "@/api/attachments";
import { ImageDropInput } from "@/components/ImageDropInput";
import { listAssignableUsers, type UserList } from "@/api/users";
import { listMilestones, type Milestone } from "@/api/milestones";
import { createShareLink, listShareLinks, revokeShareLink, shareUrlFor, type ShareLink } from "@/api/share";
import { AttachmentsSection } from "@/components/AttachmentsSection";
import { NotesSection } from "@/components/NotesSection";

const COLUMNS = [
  { key: "todo", label: "To do", accent: "border-gray-300" },
  { key: "in_progress", label: "In progress", accent: "border-blue-400" },
  { key: "review", label: "In review", accent: "border-amber-400" },
  { key: "qa_failed", label: "QA failed", accent: "border-red-400" },
  { key: "done", label: "Done", accent: "border-green-400" },
] as const;

const SEVERITY_STYLES: Record<string, string> = {
  low: "bg-gray-100 text-gray-600",
  medium: "bg-amber-100 text-amber-700",
  high: "bg-orange-100 text-orange-700",
  critical: "bg-red-100 text-red-700",
};



function TaskCard({ task, users, onClick, dragging }: { task: Task; users: UserList[]; onClick?: () => void; dragging?: boolean }) {
  const assignee = users.find((u) => u.id === task.assignee_id);
  const initials = assignee ? (assignee.full_name || assignee.email || "?").split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase() : null;
  return (
    <div
      onClick={onClick}
      className={`bg-white dark:bg-gray-700 rounded-xl border border-gray-200 dark:border-gray-600 p-3 shadow-sm hover:shadow-md transition-shadow cursor-grab select-none ${dragging ? "opacity-90 rotate-1 shadow-lg" : ""}`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-gray-900 dark:text-gray-100 leading-snug">{task.title}</p>
        {initials && (
          <span className="w-6 h-6 shrink-0 rounded-full bg-primary text-white text-[10px] font-semibold flex items-center justify-center" title={assignee?.full_name || assignee?.email || ""}>
            {initials}
          </span>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-1.5 mt-2">
        {task.item_type === "bug" && (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-red-50 text-red-600 border border-red-200">BUG</span>
        )}
        {task.severity && (
          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${SEVERITY_STYLES[task.severity] ?? "bg-gray-100 text-gray-600"}`}>{task.severity}</span>
        )}
        {task.priority && task.priority !== "medium" && (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 dark:bg-gray-600 text-gray-500 dark:text-gray-300">{task.priority}</span>
        )}
        {task.due_date && (
          <span className="ml-auto text-[10px] text-gray-400">{task.due_date}</span>
        )}
      </div>
      {task.status === "qa_failed" && task.qa_notes && (
        <p className="mt-2 text-[11px] text-red-600 dark:text-red-400 line-clamp-2">QA: {task.qa_notes}</p>
      )}
    </div>
  );
}

function DraggableCard({ task, users, onClick }: { task: Task; users: UserList[]; onClick: () => void }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: task.id });
  return (
    <div ref={setNodeRef} {...listeners} {...attributes} className={isDragging ? "opacity-30" : ""}>
      <TaskCard task={task} users={users} onClick={onClick} />
    </div>
  );
}

function Column({ colKey, label, accent, tasks, users, highlight, onCardClick }: {
  colKey: string; label: string; accent: string; tasks: Task[]; users: UserList[];
  highlight: "valid" | "invalid" | null; onCardClick: (t: Task) => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: colKey });
  return (
    <div
      ref={setNodeRef}
      className={`flex flex-col w-64 shrink-0 rounded-xl border-t-4 ${accent} bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 transition-colors ${
        isOver && highlight === "valid" ? "ring-2 ring-primary/50 bg-primary/5" : ""
      } ${highlight === "invalid" ? "opacity-50" : ""}`}
    >
      <div className="flex items-center justify-between px-3 py-2.5">
        <span className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">{label}</span>
        <span className="text-xs font-medium text-gray-400 bg-gray-200 dark:bg-gray-700 rounded-full px-2 py-0.5">{tasks.length}</span>
      </div>
      <div className="flex-1 flex flex-col gap-2 px-2 pb-2 overflow-y-auto min-h-[120px]">
        {tasks.map((t) => (
          <DraggableCard key={t.id} task={t} users={users} onClick={() => onCardClick(t)} />
        ))}
      </div>
    </div>
  );
}

export default function Boards() {
  const { user, hasPermission } = useAuth();
  const isAdmin = hasPermission("admin:all");
  const isQA = user?.permissions.includes("tasks:qa_approve") || isAdmin;
  const canManage = isAdmin || !!user?.can_manage_tasks;

  const [searchParams, setSearchParams] = useSearchParams();
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [allBoards, setAllBoards] = useState<Board[]>([]);
  const [projectSearch, setProjectSearch] = useState("");
  // The page opens on the project grid; a project is only selected by click or by URL (?project=).
  const [projectId, setProjectId] = useState<string>(() => searchParams.get("project") ?? "");
  const [boards, setBoards] = useState<Board[]>([]);
  const [boardId, setBoardId] = useState<string>(() => searchParams.get("board") ?? "");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [users, setUsers] = useState<UserList[]>([]);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [activeTask, setActiveTask] = useState<Task | null>(null);
  const [detailTask, setDetailTask] = useState<Task | null>(null);
  const [editing, setEditing] = useState(false);
  const [editForm, setEditForm] = useState({ title: "", description: "", priority: "medium", due_date: "", item_type: "task", severity: "", steps_to_reproduce: "", environment: "", milestone_id: "" });
  const [saving, setSaving] = useState(false);
  const [qaFailTask, setQaFailTask] = useState<Task | null>(null);
  const [qaNotes, setQaNotes] = useState("");
  const [showNewBoard, setShowNewBoard] = useState(false);
  const [showMembers, setShowMembers] = useState(false);
  const [showNewTask, setShowNewTask] = useState(false);
  const [newBoardName, setNewBoardName] = useState("");
  const [newTask, setNewTask] = useState({ title: "", description: "", item_type: "task", severity: "", steps_to_reproduce: "", environment: "", priority: "medium", assignee_id: "", due_date: "", milestone_id: "" });
  const [newTaskFiles, setNewTaskFiles] = useState<File[]>([]);
  const [addMemberId, setAddMemberId] = useState("");
  const [showShare, setShowShare] = useState(false);
  const [shareLinks, setShareLinks] = useState<ShareLink[]>([]);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));
  const board = boards.find((b) => b.id === boardId) || null;

  const showError = useCallback((msg: string) => {
    setError(msg);
    window.setTimeout(() => setError(null), 4500);
  }, []);

  const loadProjectGrid = useCallback(() => {
    setProjectsLoading(true);
    Promise.all([listProjects({ limit: 500 }).catch(() => [] as Project[]), listBoards().catch(() => [] as Board[])])
      .then(([ps, bs]) => { setProjects(ps); setAllBoards(bs); })
      .finally(() => setProjectsLoading(false));
  }, []);

  useEffect(() => {
    loadProjectGrid();
    listAssignableUsers().then(setUsers).catch(() => {});
  }, [loadProjectGrid]);

  // Keep the selection in the URL so a refresh or a shared link lands on the same board.
  useEffect(() => {
    const next = new URLSearchParams();
    if (projectId) next.set("project", projectId);
    if (projectId && boardId) next.set("board", boardId);
    if (next.toString() !== searchParams.toString()) setSearchParams(next, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, boardId]);

  const refreshBoards = useCallback(async (pid: string, keepBoard = false) => {
    const bs = await listBoards(pid).catch(() => [] as Board[]);
    setBoards(bs);
    setBoardId((cur) => ((keepBoard || cur) && bs.some((b) => b.id === cur) ? cur : bs[0]?.id ?? ""));
    setAllBoards((all) => [...all.filter((b) => b.project_id !== pid), ...bs]);
  }, []);

  const boardsByProject = useMemo(() => {
    const m: Record<string, Board[]> = {};
    for (const b of allBoards) (m[b.project_id] ??= []).push(b);
    return m;
  }, [allBoards]);

  const visibleProjects = useMemo(() => {
    const q = projectSearch.trim().toLowerCase();
    const list = projects.filter((p) => !q || p.name.toLowerCase().includes(q) || (p.client_name ?? "").toLowerCase().includes(q));
    // Projects with boards first, then by name
    return list.sort((a, b) => ((boardsByProject[b.id]?.length ?? 0) > 0 ? 1 : 0) - ((boardsByProject[a.id]?.length ?? 0) > 0 ? 1 : 0) || a.name.localeCompare(b.name));
  }, [projects, projectSearch, boardsByProject]);

  const currentProject = projects.find((p) => p.id === projectId) || null;
  const openProject = (pid: string) => { setBoardId(""); setProjectId(pid); };
  const backToProjects = () => { setProjectId(""); setBoardId(""); setBoards([]); loadProjectGrid(); };

  useEffect(() => {
    if (projectId) refreshBoards(projectId);
    else { setBoards([]); setBoardId(""); }
    if (projectId) listMilestones(projectId).then(setMilestones).catch(() => setMilestones([]));
    else setMilestones([]);
  }, [projectId, refreshBoards]);

  const refreshTasks = useCallback(async () => {
    if (!boardId) { setTasks([]); return; }
    setTasks(await listBoardTasks(boardId).catch(() => [] as Task[]));
  }, [boardId]);

  useEffect(() => { refreshTasks(); }, [refreshTasks]);

  // Refetch when other users move cards (activity websocket dispatches this)
  useEffect(() => {
    const h = () => refreshTasks();
    window.addEventListener("ws:tasks_updated", h);
    return () => window.removeEventListener("ws:tasks_updated", h);
  }, [refreshTasks]);

  const byColumn = useMemo(() => {
    const map: Record<string, Task[]> = {};
    for (const c of COLUMNS) map[c.key] = [];
    for (const t of tasks) (map[t.status] ?? (map[t.status] = [])).push(t);
    return map;
  }, [tasks]);

  const validTargets = useMemo(
    () => (activeTask ? allowedTargets(activeTask.status, isAdmin, !!isQA) : []),
    [activeTask, isAdmin, isQA]
  );

  const moveTask = useCallback(async (task: Task, newStatus: string, notes?: string) => {
    try {
      const payload: Record<string, unknown> = { status: newStatus };
      if (notes) payload.qa_notes = notes;
      const updated = await updateTask(task.id, payload as Partial<Task>);
      setTasks((ts) => ts.map((t) => (t.id === updated.id ? updated : t)));
      setDetailTask((d) => (d && d.id === updated.id ? updated : d));
    } catch (e) {
      showError(e instanceof Error ? e.message : "Move rejected");
    }
  }, [showError]);

  const onDragStart = (ev: DragStartEvent) => {
    setActiveTask(tasks.find((t) => t.id === ev.active.id) ?? null);
  };

  const onDragEnd = (ev: DragEndEvent) => {
    const task = tasks.find((t) => t.id === ev.active.id);
    setActiveTask(null);
    if (!task || !ev.over) return;
    const target = String(ev.over.id);
    if (target === task.status) return;
    if (target === "qa_failed" && !task.qa_notes) {
      setQaFailTask(task);
      setQaNotes("");
      return;
    }
    moveTask(task, target);
  };

  const inputClass = "w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm";

  // Mirrors the backend rule: managers/admins, QA, the assignee and anyone on the task's board may edit.
  const canEditTask = (t: Task) =>
    canManage || !!isQA || t.assignee_id === user?.id || !!board?.members.some((m) => m.user_id === user?.id);

  const openDetail = (t: Task) => {
    setDetailTask(t);
    setEditing(false);
  };

  const startEdit = (t: Task) => {
    setEditForm({
      title: t.title,
      description: t.description ?? "",
      priority: t.priority || "medium",
      due_date: t.due_date ?? "",
      item_type: t.item_type || "task",
      severity: t.severity ?? "",
      steps_to_reproduce: t.steps_to_reproduce ?? "",
      environment: t.environment ?? "",
      milestone_id: t.milestone_id ?? "",
    });
    setEditing(true);
  };

  const saveEdit = async () => {
    if (!detailTask || !editForm.title.trim()) return;
    // Send only what changed, so members never trip the field allowlist on untouched manager-only fields.
    const next: Partial<Task> = {
      title: editForm.title.trim(),
      description: editForm.description || null,
      priority: editForm.priority,
      due_date: editForm.due_date || null,
      item_type: editForm.item_type,
      severity: editForm.item_type === "bug" && editForm.severity ? editForm.severity : null,
      steps_to_reproduce: editForm.steps_to_reproduce || null,
      environment: editForm.environment || null,
    };
    if (canManage) next.milestone_id = editForm.milestone_id || null;
    const changed: Partial<Task> = {};
    for (const [k, v] of Object.entries(next) as [keyof Task, Task[keyof Task]][]) {
      if ((detailTask[k] ?? null) !== (v ?? null)) (changed as Record<string, unknown>)[k] = v;
    }
    if (Object.keys(changed).length === 0) { setEditing(false); return; }
    setSaving(true);
    try {
      const updated = await updateTask(detailTask.id, changed);
      setDetailTask(updated);
      setTasks((ts) => ts.map((t) => (t.id === updated.id ? updated : t)));
      setEditing(false);
    } catch (e) {
      showError(e instanceof Error ? e.message : "Could not save changes");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="h-full flex flex-col gap-4">
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-2.5">{error}</div>
      )}

      {/* Project grid: the landing view */}
      {!projectId && (
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Choose a project</h2>
              <p className="text-sm text-gray-500">Each project has its own boards. Pick one to open its kanban.</p>
            </div>
            <input
              type="search"
              placeholder="Search projects or clients…"
              value={projectSearch}
              onChange={(e) => setProjectSearch(e.target.value)}
              className={`${inputClass} !w-auto min-w-[240px]`}
            />
          </div>
          {projectsLoading ? (
            <p className="text-sm text-gray-400">Loading projects…</p>
          ) : visibleProjects.length === 0 ? (
            <div className="rounded-xl border border-dashed border-gray-300 dark:border-gray-600 p-10 text-center text-sm text-gray-400">
              {projects.length === 0 ? "No projects you can see yet." : "No projects match."}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {visibleProjects.map((p) => {
                const pb = boardsByProject[p.id] ?? [];
                const total = p.task_count ?? null;
                const done = p.task_done_count ?? null;
                const pct = total && total > 0 && done != null ? Math.round((done / total) * 100) : null;
                return (
                  <button
                    key={p.id}
                    onClick={() => openProject(p.id)}
                    className="text-left rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-4 shadow-sm hover:shadow-md hover:border-primary/40 transition-all group"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="font-semibold text-gray-900 dark:text-gray-100 truncate group-hover:text-primary">{p.name}</p>
                        {p.client_name && <p className="text-xs text-gray-500 truncate">{p.client_name}</p>}
                      </div>
                      <span className={`shrink-0 px-2 py-0.5 rounded-full text-[10px] font-medium border ${p.status === "active" ? "bg-green-50 text-green-700 border-green-200" : "bg-gray-50 text-gray-500 border-gray-200"}`}>{p.status}</span>
                    </div>
                    <div className="mt-3 flex items-center justify-between text-xs text-gray-500">
                      <span>{pb.length === 0 ? "No boards yet" : pb.length === 1 ? "1 board" : `${pb.length} boards`}</span>
                      {total != null && <span>{done ?? 0}/{total} tasks</span>}
                    </div>
                    {pct != null && (
                      <div className="mt-2 h-1.5 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
                        <div className="h-full bg-primary rounded-full" style={{ width: `${pct}%` }} />
                      </div>
                    )}
                    {pb.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1">
                        {pb.slice(0, 4).map((b) => (
                          <span key={b.id} className="px-2 py-0.5 rounded-md text-[11px] bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">{b.name}</span>
                        ))}
                        {pb.length > 4 && <span className="text-[11px] text-gray-400">+{pb.length - 4}</span>}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Toolbar */}
      {projectId && (
      <div className="flex flex-wrap items-center gap-3">
        <button onClick={backToProjects} className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm font-medium text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700" title="Back to all projects">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" /></svg>
          Projects
        </button>
        <div className="min-w-0">
          <p className="font-semibold text-gray-900 dark:text-gray-100 leading-tight truncate">{currentProject?.name ?? "Project"}</p>
          {currentProject?.client_name && <p className="text-xs text-gray-500 truncate">{currentProject.client_name}</p>}
        </div>
        <span className="hidden sm:block h-6 w-px bg-gray-200 dark:bg-gray-700" />
        <div className="flex items-center gap-1 flex-wrap">
          {boards.map((b) => (
            <button
              key={b.id}
              onClick={() => setBoardId(b.id)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                b.id === boardId ? "bg-primary text-white" : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
              }`}
            >
              {b.name}
            </button>
          ))}
          {canManage && projectId && (
            <button onClick={() => { setNewBoardName(""); setShowNewBoard(true); }} className="px-3 py-1.5 rounded-lg text-sm font-medium text-primary hover:bg-primary/10">
              + New board
            </button>
          )}
        </div>
        {board && (
          <div className="ml-auto flex items-center gap-2">
            {canManage && (
              <>
                <button
                  onClick={async () => {
                    setShowShare(true);
                    setShareLinks(await listShareLinks(projectId).catch(() => [] as ShareLink[]));
                  }}
                  className="px-3 py-1.5 rounded-lg text-sm font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                >
                  Share progress
                </button>
                <button onClick={() => setShowMembers(true)} className="px-3 py-1.5 rounded-lg text-sm font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600">
                  Members ({board.members.length})
                </button>
                <button
                  onClick={async () => {
                    if (!window.confirm(`Delete board "${board.name}"? Tasks stay on the project.`)) return;
                    try { await deleteBoard(board.id); await refreshBoards(projectId); } catch (e) { showError(e instanceof Error ? e.message : "Delete failed"); }
                  }}
                  className="px-3 py-1.5 rounded-lg text-sm font-medium text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                >
                  Delete
                </button>
              </>
            )}
            <button onClick={() => setShowNewTask(true)} className="px-4 py-1.5 rounded-lg bg-primary text-white text-sm font-medium hover:bg-primary-hover shadow-sm">
              + Add task
            </button>
          </div>
        )}
      </div>
      )}

      {/* Board */}
      {!projectId ? null : !board ? (
        <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">
          {canManage ? "No boards yet — create one to get started." : "No boards you're a member of in this project."}
        </div>
      ) : (
        <DndContext sensors={sensors} onDragStart={onDragStart} onDragEnd={onDragEnd}>
          <div className="flex-1 flex gap-3 overflow-x-auto pb-2">
            {COLUMNS.map((c) => (
              <Column
                key={c.key}
                colKey={c.key}
                label={c.label}
                accent={c.accent}
                tasks={byColumn[c.key] ?? []}
                users={users}
                highlight={activeTask ? (validTargets.includes(c.key) ? "valid" : c.key === activeTask.status ? null : "invalid") : null}
                onCardClick={openDetail}
              />
            ))}
          </div>
          <DragOverlay>{activeTask ? <div className="w-60"><TaskCard task={activeTask} users={users} dragging /></div> : null}</DragOverlay>
        </DndContext>
      )}

      {/* Task detail modal */}
      {detailTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => setDetailTask(null)}>
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-lg p-4 sm:p-6 max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            {editing ? (
              <>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Edit {editForm.item_type === "bug" ? "bug" : "task"}</h3>
                <div className="mt-3 space-y-3">
                  <input autoFocus className={inputClass} placeholder="Title" value={editForm.title} onChange={(e) => setEditForm({ ...editForm, title: e.target.value })} />
                  <textarea rows={4} className={inputClass} placeholder="Description" value={editForm.description} onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} />
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <select className={inputClass} value={editForm.item_type} onChange={(e) => setEditForm({ ...editForm, item_type: e.target.value, severity: e.target.value === "bug" ? editForm.severity || "medium" : "" })}>
                      <option value="task">Task</option>
                      <option value="bug">Bug</option>
                    </select>
                    <select className={inputClass} value={editForm.priority} onChange={(e) => setEditForm({ ...editForm, priority: e.target.value })}>
                      <option value="low">Low priority</option>
                      <option value="medium">Medium priority</option>
                      <option value="high">High priority</option>
                    </select>
                  </div>
                  {editForm.item_type === "bug" && (
                    <>
                      <select className={inputClass} value={editForm.severity} onChange={(e) => setEditForm({ ...editForm, severity: e.target.value })}>
                        <option value="low">Severity: low</option>
                        <option value="medium">Severity: medium</option>
                        <option value="high">Severity: high</option>
                        <option value="critical">Severity: critical</option>
                      </select>
                      <textarea rows={3} className={inputClass} placeholder="Steps to reproduce" value={editForm.steps_to_reproduce} onChange={(e) => setEditForm({ ...editForm, steps_to_reproduce: e.target.value })} />
                      <input className={inputClass} placeholder="Environment (e.g. prod, Chrome 130, iOS)" value={editForm.environment} onChange={(e) => setEditForm({ ...editForm, environment: e.target.value })} />
                    </>
                  )}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <label className="text-xs text-gray-500">
                      Due date
                      <input type="date" className={`${inputClass} mt-1`} value={editForm.due_date} onChange={(e) => setEditForm({ ...editForm, due_date: e.target.value })} />
                    </label>
                    {canManage && milestones.length > 0 && (
                      <label className="text-xs text-gray-500">
                        Milestone
                        <select className={`${inputClass} mt-1`} value={editForm.milestone_id} onChange={(e) => setEditForm({ ...editForm, milestone_id: e.target.value })}>
                          <option value="">No milestone</option>
                          {milestones.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                        </select>
                      </label>
                    )}
                  </div>
                </div>
                <div className="mt-4 flex justify-end gap-2">
                  <button onClick={() => setEditing(false)} className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">Cancel</button>
                  <button disabled={saving || !editForm.title.trim()} onClick={saveEdit} className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-white hover:bg-primary-hover disabled:opacity-50">
                    {saving ? "Saving…" : "Save"}
                  </button>
                </div>
              </>
            ) : (
            <>
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{detailTask.title}</h3>
              <div className="flex items-center gap-2 shrink-0">
                {canEditTask(detailTask) && (
                  <button onClick={() => startEdit(detailTask)} className="px-2.5 py-1 rounded-lg text-xs font-medium bg-primary/10 text-primary hover:bg-primary/20">Edit</button>
                )}
                <span className="px-2 py-1 rounded-lg text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">{COLUMNS.find((c) => c.key === detailTask.status)?.label ?? detailTask.status}</span>
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {detailTask.item_type === "bug" && <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-red-50 text-red-600 border border-red-200">BUG</span>}
              {detailTask.severity && <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${SEVERITY_STYLES[detailTask.severity] ?? ""}`}>{detailTask.severity}</span>}
              <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-300">{detailTask.priority}</span>
            </div>
            {detailTask.description && <p className="mt-3 text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{detailTask.description}</p>}
            {detailTask.item_type === "bug" && (
              <div className="mt-3 space-y-2">
                {detailTask.steps_to_reproduce && (
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase">Steps to reproduce</p>
                    <p className="text-sm text-gray-600 dark:text-gray-300 whitespace-pre-wrap">{detailTask.steps_to_reproduce}</p>
                  </div>
                )}
                {detailTask.environment && (
                  <div>
                    <p className="text-xs font-semibold text-gray-500 uppercase">Environment</p>
                    <p className="text-sm text-gray-600 dark:text-gray-300">{detailTask.environment}</p>
                  </div>
                )}
              </div>
            )}
            {detailTask.qa_notes && (
              <div className="mt-3 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 p-3">
                <p className="text-xs font-semibold text-amber-700 dark:text-amber-400 uppercase">QA notes</p>
                <p className="text-sm text-amber-800 dark:text-amber-300 whitespace-pre-wrap">{detailTask.qa_notes}</p>
              </div>
            )}
            <div className="mt-3 text-xs text-gray-400 flex flex-wrap items-center gap-x-2 gap-y-1">
              {user?.can_manage_tasks ? (
                <label className="inline-flex items-center gap-1.5">
                  Assignee:
                  <select
                    className="px-2 py-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-xs text-gray-700 dark:text-gray-200"
                    value={detailTask.assignee_id ?? ""}
                    onChange={async (e) => {
                      const v = e.target.value || null;
                      try {
                        const updated = await updateTask(detailTask.id, { assignee_id: v });
                        setDetailTask(updated);
                        refreshTasks();
                      } catch (err) {
                        showError(err instanceof Error ? err.message : "Could not change assignee");
                      }
                    }}
                  >
                    <option value="">Unassigned</option>
                    {users.map((u) => <option key={u.id} value={u.id}>{u.full_name || u.email}</option>)}
                  </select>
                </label>
              ) : (
                <span>Assignee: {users.find((u) => u.id === detailTask.assignee_id)?.full_name ?? "—"}</span>
              )}
              {detailTask.due_date && <span>· Due {detailTask.due_date}</span>}
              {detailTask.milestone_id && <span>· ⚑ {milestones.find((m) => m.id === detailTask.milestone_id)?.name ?? "milestone"}</span>}
            </div>
            <AttachmentsSection entityType="task" entityId={detailTask.id} />
            <NotesSection entityType="task" entityId={detailTask.id} title="Comments" defaultPrivate={false} />
            {/* Action buttons for the allowed transitions */}
            <div className="mt-5 flex flex-wrap gap-2">
              {allowedTargets(detailTask.status, isAdmin, !!isQA).map((target) => {
                const label =
                  target === "done" ? "Approve → Done"
                  : target === "qa_failed" ? "Fail QA"
                  : target === "review" ? "Submit for review"
                  : target === "in_progress" ? (detailTask.status === "qa_failed" ? "Rework" : "Start")
                  : "Back to To do";
                const danger = target === "qa_failed";
                return (
                  <button
                    key={target}
                    onClick={() => {
                      if (target === "qa_failed") { setQaFailTask(detailTask); setQaNotes(""); return; }
                      moveTask(detailTask, target);
                    }}
                    className={`px-3 py-1.5 rounded-lg text-sm font-medium ${danger ? "bg-red-600 text-white hover:bg-red-700" : target === "done" ? "bg-green-600 text-white hover:bg-green-700" : "bg-primary text-white hover:bg-primary-hover"}`}
                  >
                    {label}
                  </button>
                );
              })}
              {user?.can_manage_tasks && (
                <button
                  onClick={async () => {
                    if (!window.confirm(`Delete "${detailTask.title}"? This cannot be undone.`)) return;
                    try {
                      await deleteTask(detailTask.id);
                      setDetailTask(null);
                      refreshTasks();
                    } catch (err) {
                      showError(err instanceof Error ? err.message : "Delete failed");
                    }
                  }}
                  className="px-3 py-1.5 rounded-lg text-sm font-medium text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                >
                  Delete
                </button>
              )}
              <button onClick={() => setDetailTask(null)} className="ml-auto px-3 py-1.5 rounded-lg text-sm font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200">Close</button>
            </div>
            </>
            )}
          </div>
        </div>
      )}

      {/* QA fail modal */}
      {qaFailTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Fail QA: {qaFailTask.title}</h3>
            <p className="text-sm text-gray-500 mt-1">Explain what failed — the assignee will be notified.</p>
            <textarea autoFocus rows={4} className={`${inputClass} mt-3`} placeholder="e.g. Crashes when submitting the form on mobile" value={qaNotes} onChange={(e) => setQaNotes(e.target.value)} />
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setQaFailTask(null)} className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">Cancel</button>
              <button
                disabled={!qaNotes.trim()}
                onClick={async () => { await moveTask(qaFailTask, "qa_failed", qaNotes.trim()); setQaFailTask(null); }}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
              >
                Fail QA
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Share progress modal */}
      {showShare && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => setShowShare(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-lg p-4 sm:p-6" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Client progress links</h3>
            <p className="text-sm text-gray-500 mt-1">
              Anyone with a link sees a read-only progress page for this project — task titles and status only, no assignees, notes, or internal details.
            </p>
            <ul className="mt-4 space-y-2">
              {shareLinks.map((l) => (
                <li key={l.id} className="flex items-center gap-2 rounded-lg border border-gray-200 dark:border-gray-600 px-3 py-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{l.label || "Progress link"}</p>
                    <p className="text-xs text-gray-400 truncate">{shareUrlFor(l.token)}</p>
                  </div>
                  <button
                    onClick={async () => {
                      await navigator.clipboard.writeText(shareUrlFor(l.token)).catch(() => {});
                      setCopiedId(l.id);
                      window.setTimeout(() => setCopiedId(null), 1500);
                    }}
                    className="px-2.5 py-1 rounded-lg text-xs font-medium bg-primary/10 text-primary hover:bg-primary/20"
                  >
                    {copiedId === l.id ? "Copied!" : "Copy"}
                  </button>
                  <a href={shareUrlFor(l.token)} target="_blank" rel="noreferrer" className="px-2.5 py-1 rounded-lg text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200">
                    Open
                  </a>
                  <button
                    onClick={async () => {
                      try {
                        await revokeShareLink(l.id);
                        setShareLinks((ls) => ls.filter((x) => x.id !== l.id));
                      } catch (e) { showError(e instanceof Error ? e.message : "Revoke failed"); }
                    }}
                    className="px-2.5 py-1 rounded-lg text-xs font-medium text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                  >
                    Revoke
                  </button>
                </li>
              ))}
              {shareLinks.length === 0 && <li className="text-sm text-gray-400 py-2">No active links.</li>}
            </ul>
            <div className="mt-4 flex justify-between">
              <button
                onClick={async () => {
                  try {
                    const l = await createShareLink(projectId);
                    setShareLinks((ls) => [l, ...ls]);
                  } catch (e) { showError(e instanceof Error ? e.message : "Could not create link"); }
                }}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-white hover:bg-primary-hover"
              >
                + New link
              </button>
              <button onClick={() => setShowShare(false)} className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">Close</button>
            </div>
          </div>
        </div>
      )}

      {/* New board modal */}
      {showNewBoard && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-md p-6">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">New board</h3>
            <input autoFocus className={`${inputClass} mt-3`} placeholder="Board name (e.g. Sprint 1, Bugs)" value={newBoardName} onChange={(e) => setNewBoardName(e.target.value)} />
            <p className="text-xs text-gray-400 mt-2">Add members after creating — only members (plus managers and admins) can see the board.</p>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setShowNewBoard(false)} className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">Cancel</button>
              <button
                disabled={!newBoardName.trim()}
                onClick={async () => {
                  try {
                    const b = await createBoard({ project_id: projectId, name: newBoardName.trim() });
                    setShowNewBoard(false);
                    await refreshBoards(projectId, true);
                    setBoardId(b.id);
                  } catch (e) { showError(e instanceof Error ? e.message : "Could not create board"); }
                }}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-white hover:bg-primary-hover disabled:opacity-50"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Members modal */}
      {showMembers && board && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={() => setShowMembers(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-md p-6" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Board members</h3>
            <ul className="mt-3 divide-y divide-gray-100 dark:divide-gray-700">
              {board.members.map((m) => (
                <li key={m.user_id} className="flex items-center justify-between py-2">
                  <span className="text-sm text-gray-700 dark:text-gray-200">{m.full_name || m.email}</span>
                  <button
                    onClick={async () => {
                      try {
                        const b = await removeBoardMember(board.id, m.user_id);
                        setBoards((bs) => bs.map((x) => (x.id === b.id ? b : x)));
                      } catch (e) { showError(e instanceof Error ? e.message : "Remove failed"); }
                    }}
                    className="text-xs font-medium text-red-500 hover:underline"
                  >
                    Remove
                  </button>
                </li>
              ))}
              {board.members.length === 0 && <li className="py-2 text-sm text-gray-400">No members yet.</li>}
            </ul>
            <div className="mt-3 flex gap-2">
              <select className={inputClass} value={addMemberId} onChange={(e) => setAddMemberId(e.target.value)}>
                <option value="">Add member…</option>
                {users.filter((u) => !board.members.some((m) => m.user_id === u.id)).map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name || u.email}</option>
                ))}
              </select>
              <button
                disabled={!addMemberId}
                onClick={async () => {
                  try {
                    const b = await addBoardMember(board.id, addMemberId);
                    setBoards((bs) => bs.map((x) => (x.id === b.id ? b : x)));
                    setAddMemberId("");
                  } catch (e) { showError(e instanceof Error ? e.message : "Add failed"); }
                }}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-white hover:bg-primary-hover disabled:opacity-50"
              >
                Add
              </button>
            </div>
          </div>
        </div>
      )}

      {/* New task modal */}
      {showNewTask && board && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-lg p-4 sm:p-6 max-h-[85vh] overflow-y-auto">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Add {newTask.item_type === "bug" ? "bug" : "task"} to {board.name}</h3>
            <div className="mt-3 space-y-3">
              <input autoFocus className={inputClass} placeholder="Title" value={newTask.title} onChange={(e) => setNewTask({ ...newTask, title: e.target.value })} />
              <textarea rows={3} className={inputClass} placeholder="Description" value={newTask.description} onChange={(e) => setNewTask({ ...newTask, description: e.target.value })} />
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <select className={inputClass} value={newTask.item_type} onChange={(e) => setNewTask({ ...newTask, item_type: e.target.value, severity: e.target.value === "bug" ? newTask.severity || "medium" : "" })}>
                  <option value="task">Task</option>
                  <option value="bug">Bug</option>
                </select>
                <select className={inputClass} value={newTask.priority} onChange={(e) => setNewTask({ ...newTask, priority: e.target.value })}>
                  <option value="low">Low priority</option>
                  <option value="medium">Medium priority</option>
                  <option value="high">High priority</option>
                </select>
              </div>
              {newTask.item_type === "bug" && (
                <>
                  <select className={inputClass} value={newTask.severity} onChange={(e) => setNewTask({ ...newTask, severity: e.target.value })}>
                    <option value="low">Severity: low</option>
                    <option value="medium">Severity: medium</option>
                    <option value="high">Severity: high</option>
                    <option value="critical">Severity: critical</option>
                  </select>
                  <textarea rows={3} className={inputClass} placeholder="Steps to reproduce" value={newTask.steps_to_reproduce} onChange={(e) => setNewTask({ ...newTask, steps_to_reproduce: e.target.value })} />
                  <input className={inputClass} placeholder="Environment (e.g. prod, Chrome 130, iOS)" value={newTask.environment} onChange={(e) => setNewTask({ ...newTask, environment: e.target.value })} />
                </>
              )}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <select className={inputClass} value={newTask.assignee_id} onChange={(e) => setNewTask({ ...newTask, assignee_id: e.target.value })}>
                  <option value="">Unassigned</option>
                  {users.map((u) => <option key={u.id} value={u.id}>{u.full_name || u.email}</option>)}
                </select>
                <input type="date" className={inputClass} value={newTask.due_date} onChange={(e) => setNewTask({ ...newTask, due_date: e.target.value })} />
              </div>
              {milestones.length > 0 && (
                <select className={inputClass} value={newTask.milestone_id} onChange={(e) => setNewTask({ ...newTask, milestone_id: e.target.value })}>
                  <option value="">No milestone</option>
                  {milestones.filter((m) => m.state !== "completed").map((m) => (
                    <option key={m.id} value={m.id}>{m.name}{m.due_date ? ` (due ${m.due_date})` : ""}</option>
                  ))}
                </select>
              )}
              <ImageDropInput files={newTaskFiles} onChange={setNewTaskFiles} />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setShowNewTask(false)} className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">Cancel</button>
              <button
                disabled={!newTask.title.trim()}
                onClick={async () => {
                  try {
                    const created = await createTask({
                      title: newTask.title.trim(),
                      description: newTask.description || null,
                      project_id: board.project_id,
                      board_id: board.id,
                      status: "todo",
                      priority: newTask.priority,
                      item_type: newTask.item_type,
                      severity: newTask.item_type === "bug" && newTask.severity ? newTask.severity : null,
                      steps_to_reproduce: newTask.steps_to_reproduce || null,
                      environment: newTask.environment || null,
                      assignee_id: newTask.assignee_id || null,
                      due_date: newTask.due_date || null,
                      milestone_id: newTask.milestone_id || null,
                    });
                    for (const f of newTaskFiles) {
                      try { await uploadAttachment("task", created.id, f); } catch { /* task exists; skip failed image */ }
                    }
                    setNewTaskFiles([]);
                    setShowNewTask(false);
                    setNewTask({ title: "", description: "", item_type: "task", severity: "", steps_to_reproduce: "", environment: "", priority: "medium", assignee_id: "", due_date: "", milestone_id: "" });
                    refreshTasks();
                  } catch (e) { showError(e instanceof Error ? e.message : "Could not create task"); }
                }}
                className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-white hover:bg-primary-hover disabled:opacity-50"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
