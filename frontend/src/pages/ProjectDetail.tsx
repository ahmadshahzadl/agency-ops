import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuth } from "@/store/auth";
import { getProject, type Project } from "@/api/projects";
import { listTasks, type Task } from "@/api/tasks";
import { listBoards, type Board } from "@/api/boards";
import { MilestonesSection } from "@/components/MilestonesSection";
import { NotesSection } from "@/components/NotesSection";
import { AttachmentsSection } from "@/components/AttachmentsSection";
import { CredentialsSection } from "@/components/CredentialsSection";

const STATUS_BADGE: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  active: "bg-green-100 text-green-700",
  on_hold: "bg-amber-100 text-amber-700",
  completed: "bg-blue-100 text-blue-700",
  cancelled: "bg-red-100 text-red-600",
};

const TASK_STATUS_LABELS: Record<string, string> = {
  todo: "To do",
  in_progress: "In progress",
  review: "In review",
  qa_failed: "QA failed",
  done: "Done",
};

const TASK_DOT: Record<string, string> = {
  todo: "bg-gray-300",
  in_progress: "bg-blue-500",
  review: "bg-amber-500",
  qa_failed: "bg-red-500",
  done: "bg-green-500",
};

export default function ProjectDetail() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("projects:write") || hasPermission("admin:all");

  const [project, setProject] = useState<Project | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [boards, setBoards] = useState<Board[]>([]);
  const [notFound, setNotFound] = useState(false);

  const load = useCallback(() => {
    if (!projectId) return;
    getProject(projectId).then(setProject).catch(() => setNotFound(true));
    listTasks({ project_id: projectId }).then(setTasks).catch(() => setTasks([]));
    listBoards(projectId).then(setBoards).catch(() => setBoards([]));
  }, [projectId]);

  useEffect(() => { load(); }, [load]);

  if (notFound) {
    return (
      <div className="text-center py-16 text-gray-500">
        <p>Project not found or you don't have access to it.</p>
        <Link to="/projects" className="text-primary hover:underline text-sm">← Back to projects</Link>
      </div>
    );
  }
  if (!project) return <div className="py-16 text-center text-gray-400">Loading…</div>;

  const total = project.task_count ?? tasks.length;
  const done = project.task_done_count ?? tasks.filter((t) => t.status === "done").length;
  const percent = total ? Math.round((done * 100) / total) : 0;
  const statusCounts = tasks.reduce<Record<string, number>>((acc, t) => {
    acc[t.status] = (acc[t.status] || 0) + 1;
    return acc;
  }, {});
  const openTasks = tasks.filter((t) => t.status !== "done").slice(0, 10);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-5">
        <div className="flex flex-wrap items-start gap-3">
          <div className="min-w-0">
            <Link to="/projects" className="text-xs text-gray-400 hover:text-primary">← Projects</Link>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mt-0.5">{project.name}</h1>
            <div className="mt-1.5 flex flex-wrap items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <span className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${STATUS_BADGE[project.status] ?? "bg-gray-100 text-gray-600"}`}>{project.status}</span>
              {project.pipeline_stage && <span className="text-xs capitalize">stage: {project.pipeline_stage}</span>}
              {project.client_name && <span className="text-xs">· {project.client_name}</span>}
              {(project.start_date || project.end_date) && (
                <span className="text-xs">· {project.start_date ?? "…"} → {project.end_date ?? "…"}</span>
              )}
              {project.budget != null && <span className="text-xs">· budget {Number(project.budget).toLocaleString()}</span>}
            </div>
          </div>
          {canWrite && (
            <button
              onClick={() => navigate(`/projects?edit=${project.id}`)}
              className="ml-auto px-3.5 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-sm font-medium text-gray-600 dark:text-gray-300 hover:border-primary hover:text-primary"
            >
              Edit project
            </button>
          )}
        </div>
        {project.description && <p className="mt-3 text-sm text-gray-600 dark:text-gray-300 whitespace-pre-line">{project.description}</p>}

        {/* Progress */}
        <div className="mt-4">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
            <span>{done} of {total} tasks done</span>
            <span className="font-semibold text-primary">{percent}%</span>
          </div>
          <div className="h-2 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
            <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${percent}%` }} />
          </div>
        </div>

        {/* Task status chips */}
        {total > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {Object.entries(TASK_STATUS_LABELS).map(([s, label]) => (
              <span key={s} className="inline-flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/60 rounded-full px-2.5 py-1">
                <span className={`w-2 h-2 rounded-full ${TASK_DOT[s]}`} />
                {label}: <b className="text-gray-700 dark:text-gray-200">{statusCounts[s] || 0}</b>
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="grid lg:grid-cols-2 gap-5 items-start">
        {/* Open tasks */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-[11px] uppercase tracking-wide text-gray-400 font-semibold">Open tasks</h2>
            <Link to="/tasks" className="text-xs text-primary hover:underline">All tasks →</Link>
          </div>
          <ul className="divide-y divide-gray-50 dark:divide-gray-700">
            {openTasks.map((t) => (
              <li key={t.id} className="py-2 flex items-center gap-2 text-sm">
                <span className={`w-2 h-2 rounded-full shrink-0 ${TASK_DOT[t.status] ?? "bg-gray-300"}`} />
                <span className="truncate text-gray-700 dark:text-gray-200">
                  {t.item_type === "bug" && <span className="text-red-500 mr-1" title="Bug">●</span>}
                  {t.title}
                </span>
                <span className="ml-auto shrink-0 text-[11px] text-gray-400">{TASK_STATUS_LABELS[t.status] ?? t.status}{t.due_date ? ` · ${t.due_date}` : ""}</span>
              </li>
            ))}
            {openTasks.length === 0 && <li className="py-3 text-xs text-gray-400">No open tasks — everything's done (or nothing's started).</li>}
          </ul>
        </div>

        {/* Boards */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-[11px] uppercase tracking-wide text-gray-400 font-semibold">Boards</h2>
            <Link to="/boards" className="text-xs text-primary hover:underline">Open boards →</Link>
          </div>
          <div className="space-y-2">
            {boards.map((b) => (
              <Link key={b.id} to="/boards" className="flex items-center gap-2 rounded-lg border border-gray-100 dark:border-gray-700 px-3 py-2 hover:border-primary/40 transition-colors">
                <span className="text-sm font-medium text-gray-800 dark:text-gray-100">{b.name}</span>
                <span className="ml-auto text-xs text-gray-400">{b.task_count} tasks · {b.members.length} members</span>
              </Link>
            ))}
            {boards.length === 0 && <p className="text-xs text-gray-400 py-2">No boards yet — create one from the Boards page, or the first client-reported issue will create one automatically.</p>}
          </div>
        </div>
      </div>

      {/* Full-width sections (shared components, same as the edit modal) */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
        <MilestonesSection projectId={project.id} />
        <NotesSection entityType="project" entityId={project.id} />
        <AttachmentsSection entityType="project" entityId={project.id} />
        <CredentialsSection projectId={project.id} />
      </div>
    </div>
  );
}
