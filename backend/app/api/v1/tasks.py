from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Task as TaskModel, Project as ProjectModel, Client as ClientModel, Notification as NotificationModel
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from sqlalchemy import or_
from app.api.deps import get_current_user, require_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids
from app.services.activity_service import log_activity, tasks_updated_this_request, notifications_updated_this_request

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _notify_task_assignee(db: Session, assignee_id: UUID, task_title: str, task_id: UUID) -> None:
    """Create a notification for the assignee when a task is assigned to them."""
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
):
    qry = db.query(TaskModel).outerjoin(ProjectModel, TaskModel.project_id == ProjectModel.id)
    if "admin:all" not in permissions:
        # Manager: tasks they created OR tasks assigned to their team. Member: only tasks assigned to them.
        if manager_scope is not None:
            qry = qry.filter(
                or_(
                    TaskModel.created_by == user.id,
                    TaskModel.assignee_id.in_(manager_scope),
                )
            )
        else:
            qry = qry.filter(TaskModel.assignee_id == user.id)
    if project_id:
        qry = qry.filter(TaskModel.project_id == project_id)
    if assignee_id:
        qry = qry.filter(TaskModel.assignee_id == assignee_id)
    if status_filter:
        qry = qry.filter(TaskModel.status == status_filter)
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
    if data.project_id is not None and not _can_access_task_project(data.project_id, db, team_ids, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot add task to this project")
    task = TaskModel(
        project_id=data.project_id,
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        assignee_id=assignee_id,
        due_date=data.due_date,
        order_index=data.order_index,
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


def _can_access_task(task: TaskModel, user_id: UUID, is_admin: bool, manager_scope: set[UUID] | None) -> bool:
    """True if user can view/edit: admin, assignee, or manager (created task or task assigned to their team)."""
    if is_admin:
        return True
    if task.assignee_id == user_id:
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
    if not _can_access_task(task, user.id, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


# Fields members (assignees) may update on their own tasks; managers/admins can update any field.
ASSIGNEE_EDITABLE_FIELDS = {"status", "description", "priority", "due_date"}


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
    if not _can_access_task(task, user.id, "admin:all" in permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    updates = data.model_dump(exclude_unset=True)
    is_manager_or_admin = "admin:all" in permissions or manager_scope is not None
    if not is_manager_or_admin:
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
    status_change = updates.get("status")
    for k, v in updates.items():
        setattr(task, k, v)
    db.flush()
    if "assignee_id" in updates and task.assignee_id is not None and task.assignee_id != user.id:
        _notify_task_assignee(db, task.assignee_id, task.title, task.id)
        notifications_updated_this_request.set(True)
    action = "task_completed" if status_change == "done" else "task_updated"
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
    db.delete(task)
    db.flush()
    log_activity(db, user.id, "task_deleted", "task", None, details=f"Task deleted: {title}")
    tasks_updated_this_request.set(True)
    db.commit()
