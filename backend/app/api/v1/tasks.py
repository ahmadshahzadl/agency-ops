from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Task as TaskModel, Project as ProjectModel, Client as ClientModel, Notification as NotificationModel, Board as BoardModel, BoardMember as BoardMemberModel, User as UserModel
from app.services import email_service
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, VALID_STATUSES, VALID_ITEM_TYPES, VALID_SEVERITIES
from sqlalchemy import or_
from app.api.deps import get_current_user, require_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids
from app.services.cleanup_service import purge_entity_artifacts
from app.services.activity_service import log_activity, tasks_updated_this_request, notifications_updated_this_request

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Status pipeline. Dev transitions are open to the assignee/managers; the
# review -> done|qa_failed gate needs tasks:qa_approve (or admin:all).
DEV_TRANSITIONS: dict[str, set[str]] = {
    "todo": {"in_progress"},
    "in_progress": {"todo", "review"},
    "review": {"in_progress"},
    "qa_failed": {"in_progress"},
    "done": set(),
}
QA_TRANSITIONS: dict[str, set[str]] = {"review": {"done", "qa_failed"}}


def get_user_board_ids(db: Session, user_id: UUID) -> set[UUID]:
    """Board ids the user is a member of (grants visibility of tasks on those boards)."""
    rows = db.query(BoardMemberModel.board_id).filter(BoardMemberModel.user_id == user_id).all()
    return {r[0] for r in rows}


def _can_place_on_board(
    db: Session,
    board: BoardModel,
    user_id: UUID,
    is_admin: bool,
    manager_scope: set[UUID] | None,
    board_ids: set[UUID],
) -> bool:
    """Admin, board creator, board member, or a manager who owns the board's project scope."""
    if is_admin or board.created_by == user_id or board.id in board_ids:
        return True
    if manager_scope is not None:
        proj = db.query(ProjectModel).filter(ProjectModel.id == board.project_id).first()
        return proj is not None and proj.owner_id is not None and proj.owner_id in manager_scope
    return False


def _validate_board_placement(
    db: Session,
    board_id: UUID,
    task_project_id: UUID | None,
    user_id: UUID,
    is_admin: bool,
    manager_scope: set[UUID] | None,
) -> None:
    board = db.query(BoardModel).filter(BoardModel.id == board_id).first()
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    if task_project_id != board.project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Task must belong to the board's project")
    if not _can_place_on_board(db, board, user_id, is_admin, manager_scope, get_user_board_ids(db, user_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this board")


def _validate_bug_fields(item_type: str | None, severity: str | None) -> None:
    if item_type is not None and item_type not in VALID_ITEM_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"item_type must be one of: {', '.join(VALID_ITEM_TYPES)}")
    if severity is not None and severity not in VALID_SEVERITIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"severity must be one of: {', '.join(VALID_SEVERITIES)}")


def _notify_task_assignee(db: Session, assignee_id: UUID, task_title: str, task_id: UUID) -> None:
    """Create a notification (and email) for the assignee when a task is assigned to them."""
    n = NotificationModel(
        user_id=assignee_id,
        title="Task assigned",
        message=f'You were assigned a task: "{task_title}"',
        link=f"/tasks?highlight={task_id}",
        type="task",
        reference_id=None,
    )
    db.add(n)
    db.flush()
    assignee = db.query(UserModel).filter(UserModel.id == assignee_id).first()
    if assignee:
        email_service.send_notification(
            assignee.email, "Task assigned", f'You were assigned a task: "{task_title}"', f"/tasks?highlight={task_id}"
        )


def _can_access_task_project(
    project_id: UUID | None,
    db: Session,
    team_ids: set[UUID],
    is_admin: bool,
    manager_scope: set[UUID] | None = None,
) -> bool:
    """When project_id is None, allow (task without project). Else check access."""
    if project_id is None:
        return True
    if is_admin:
        return True
    proj = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    if not proj or not proj.client:
        return False
    if manager_scope is not None:
        return proj.owner_id is not None and proj.owner_id in manager_scope
    return proj.client.team_id in team_ids


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    db: Session = Depends(get_db),
    user=Depends(require_permission("tasks:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    project_id: UUID | None = None,
    assignee_id: UUID | None = None,
    status_filter: str | None = None,
    board_id: UUID | None = None,
):
    qry = db.query(TaskModel).outerjoin(ProjectModel, TaskModel.project_id == ProjectModel.id)
    if "admin:all" not in permissions:
        # Manager: tasks they created OR tasks assigned to their team. Member: tasks assigned
        # to them. Both additionally see all tasks on boards they belong to (e.g. QA review queue).
        board_ids = get_user_board_ids(db, user.id)
        clauses = [TaskModel.assignee_id == user.id]
        if manager_scope is not None:
            clauses = [TaskModel.created_by == user.id, TaskModel.assignee_id.in_(manager_scope)]
        if board_ids:
            clauses.append(TaskModel.board_id.in_(board_ids))
        qry = qry.filter(or_(*clauses))
    if project_id:
        qry = qry.filter(TaskModel.project_id == project_id)
    if assignee_id:
        qry = qry.filter(TaskModel.assignee_id == assignee_id)
    if status_filter:
        qry = qry.filter(TaskModel.status == status_filter)
    if board_id:
        qry = qry.filter(TaskModel.board_id == board_id)
    qry = qry.order_by(TaskModel.order_index, TaskModel.created_at)
    return qry.offset(skip).limit(limit).all()


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    data: TaskCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("tasks:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    is_manager_or_admin = "admin:all" in permissions or manager_scope is not None
    # Members can create tasks only for themselves (assignee = self)
    if not is_manager_or_admin:
        if data.assignee_id is not None and data.assignee_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Members can only create tasks assigned to themselves")
        assignee_id = user.id
    else:
        assignee_id = data.assignee_id
        # Mirror update_task: non-admin managers may only assign within their scope
        if (
            "admin:all" not in permissions
            and assignee_id is not None
            and assignee_id != user.id
            and assignee_id not in manager_scope
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Managers can only assign tasks to themselves or to their team members")
    if data.project_id is not None and not _can_access_task_project(data.project_id, db, team_ids, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot add task to this project")
    if data.status not in VALID_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"status must be one of: {', '.join(VALID_STATUSES)}")
    if data.status in ("done", "qa_failed") and "admin:all" not in permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="New tasks cannot start in a QA outcome state")
    _validate_bug_fields(data.item_type, data.severity)
    if data.board_id is not None:
        _validate_board_placement(db, data.board_id, data.project_id, user.id, "admin:all" in permissions, manager_scope)
    task = TaskModel(
        project_id=data.project_id,
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        assignee_id=assignee_id,
        due_date=data.due_date,
        order_index=data.order_index,
        item_type=data.item_type,
        severity=data.severity,
        steps_to_reproduce=data.steps_to_reproduce,
        environment=data.environment,
        board_id=data.board_id,
        column_order=data.column_order,
        created_by=user.id,
    )
    db.add(task)
    db.flush()
    if assignee_id is not None and assignee_id != user.id:
        _notify_task_assignee(db, assignee_id, task.title, task.id)
        notifications_updated_this_request.set(True)
    log_activity(db, user.id, "task_created", "task", task.id, details=f"Task: {task.title}")
    tasks_updated_this_request.set(True)
    db.commit()
    db.refresh(task)
    return task


def _can_access_task(
    task: TaskModel,
    user_id: UUID,
    is_admin: bool,
    manager_scope: set[UUID] | None,
    board_ids: set[UUID] = frozenset(),
) -> bool:
    """True if user can view/edit: admin, assignee, board member, or manager (created task or task assigned to their team)."""
    if is_admin:
        return True
    if task.assignee_id == user_id:
        return True
    if task.board_id is not None and task.board_id in board_ids:
        return True
    if manager_scope is not None:
        return task.created_by == user_id or (task.assignee_id is not None and task.assignee_id in manager_scope)
    return False


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("tasks:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if not _can_access_task(task, user.id, "admin:all" in permissions, manager_scope, get_user_board_ids(db, user.id)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


# Fields members (assignees) may update on their own tasks; managers/admins can update any field.
ASSIGNEE_EDITABLE_FIELDS = {
    "status", "description", "priority", "due_date",
    "item_type", "severity", "steps_to_reproduce", "environment",
    "board_id", "column_order",
}
# Fields a QA reviewer (non-assignee) may touch when acting on a task in review.
QA_ACTION_FIELDS = {"status", "qa_notes", "column_order"}


def _apply_status_transition(task: TaskModel, updates: dict, user, permissions: set[str]) -> str | None:
    """Validate and enrich a status change. Returns the activity action, or None if no change.

    Raises 400/403 on invalid or unauthorized transitions. Mutates `updates`
    handling for qa_by/qa_at via the task directly after callers setattr.
    """
    new_status = updates.get("status")
    if new_status is None or new_status == task.status:
        return None
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"status must be one of: {', '.join(VALID_STATUSES)}")
    is_admin = "admin:all" in permissions
    is_qa = "tasks:qa_approve" in permissions
    old = task.status if task.status in VALID_STATUSES else "todo"
    allowed = set(DEV_TRANSITIONS.get(old, set()))
    if is_qa:
        allowed |= QA_TRANSITIONS.get(old, set())
    if not is_admin and new_status not in allowed:
        if old == "review" and new_status in ("done", "qa_failed"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only QA (tasks:qa_approve) can approve or fail a task in review")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Invalid transition: {old} → {new_status}")
    if old == "review" and new_status in ("done", "qa_failed"):
        if new_status == "qa_failed" and not (updates.get("qa_notes") or task.qa_notes):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="qa_notes is required when failing QA")
        task.qa_by = user.id
        task.qa_at = datetime.utcnow()
        return "task_qa_approved" if new_status == "done" else "task_qa_failed"
    return "task_completed" if new_status == "done" else "task_updated"


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("tasks:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    board_ids = get_user_board_ids(db, user.id)
    if not _can_access_task(task, user.id, "admin:all" in permissions, manager_scope, board_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    updates = data.model_dump(exclude_unset=True)
    is_manager_or_admin = "admin:all" in permissions or manager_scope is not None
    # A QA reviewer (non-assignee) may act on a task in review: approve/fail with notes.
    is_qa_action = (
        "tasks:qa_approve" in permissions
        and task.status == "review"
        and set(updates) <= QA_ACTION_FIELDS
    )
    if not is_manager_or_admin and not is_qa_action:
        if task.assignee_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the assignee can update this task")
        for k in updates:
            if k not in ASSIGNEE_EDITABLE_FIELDS:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Members may only update: {', '.join(sorted(ASSIGNEE_EDITABLE_FIELDS))}")
    # Manager (non-admin) can reassign only to self or someone in their team
    if is_manager_or_admin and "admin:all" not in permissions and "assignee_id" in updates:
        new_assignee = updates["assignee_id"]
        if new_assignee is not None and new_assignee != user.id and new_assignee not in manager_scope:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Managers can only assign tasks to themselves or to their team members")
    _validate_bug_fields(updates.get("item_type"), updates.get("severity"))
    if "board_id" in updates and updates["board_id"] is not None and "admin:all" not in permissions:
        target_project = updates.get("project_id", task.project_id)
        _validate_board_placement(db, updates["board_id"], target_project, user.id, False, manager_scope)
    status_change = updates.get("status")
    action = _apply_status_transition(task, updates, user, permissions) or "task_updated"
    for k, v in updates.items():
        setattr(task, k, v)
    db.flush()
    if "assignee_id" in updates and task.assignee_id is not None and task.assignee_id != user.id:
        _notify_task_assignee(db, task.assignee_id, task.title, task.id)
        notifications_updated_this_request.set(True)
    if action in ("task_qa_approved", "task_qa_failed") and task.assignee_id is not None and task.assignee_id != user.id:
        outcome = "approved" if action == "task_qa_approved" else "failed QA"
        qa_message = f'"{task.title}" was {outcome}' + (f": {task.qa_notes}" if action == "task_qa_failed" and task.qa_notes else "")
        n = NotificationModel(
            user_id=task.assignee_id,
            title=f"Task {outcome}",
            message=qa_message,
            link=f"/tasks?highlight={task.id}",
            type="task",
            reference_id=None,
        )
        db.add(n)
        db.flush()
        notifications_updated_this_request.set(True)
        qa_assignee = db.query(UserModel).filter(UserModel.id == task.assignee_id).first()
        if qa_assignee:
            email_service.send_notification(qa_assignee.email, f"Task {outcome}", qa_message, f"/tasks?highlight={task.id}")
    log_activity(db, user.id, action, "task", task.id, details=f"Task: {task.title}" + (f" → {status_change}" if status_change else ""))
    tasks_updated_this_request.set(True)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("tasks:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if "admin:all" not in permissions and manager_scope is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only managers or admins can delete tasks")
    if not _can_access_task(task, user.id, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    title = task.title
    purge_entity_artifacts(db, "task", task.id)
    db.delete(task)
    db.flush()
    log_activity(db, user.id, "task_deleted", "task", None, details=f"Task deleted: {title}")
    tasks_updated_this_request.set(True)
    db.commit()
