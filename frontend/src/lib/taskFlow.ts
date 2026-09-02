/** Task status pipeline — single source of truth for the frontend,
 * mirroring backend tasks.py DEV_TRANSITIONS / QA_TRANSITIONS. */

export const TASK_STATUSES = ["todo", "in_progress", "review", "qa_failed", "done"] as const;

export const TASK_STATUS_LABELS: Record<string, string> = {
  todo: "To do",
  in_progress: "In progress",
  review: "In review",
  qa_failed: "QA failed",
  done: "Done",
};

export const DEV_TRANSITIONS: Record<string, string[]> = {
  todo: ["in_progress"],
  in_progress: ["todo", "review"],
  review: ["in_progress"],
  qa_failed: ["in_progress"],
  done: [],
};

export const QA_TRANSITIONS: Record<string, string[]> = { review: ["done", "qa_failed"] };

/** Statuses a task in `status` may move to for this user. */
export function allowedTargets(status: string, isAdmin: boolean, isQA: boolean): string[] {
  if (isAdmin) return TASK_STATUSES.filter((s) => s !== status);
  const dev = DEV_TRANSITIONS[status] ?? [];
  return isQA ? [...dev, ...(QA_TRANSITIONS[status] ?? [])] : dev;
}

/** Options for a status <select>: the current status plus every legal move. */
export function statusOptionsFor(currentStatus: string, isAdmin: boolean, isQA: boolean): string[] {
  return [currentStatus, ...allowedTargets(currentStatus, isAdmin, isQA)];
}

/** Statuses a brand-new task may start in (server rejects done/qa_failed for non-admins). */
export function newTaskStatusOptions(isAdmin: boolean): string[] {
  return isAdmin ? [...TASK_STATUSES] : ["todo", "in_progress", "review"];
}
