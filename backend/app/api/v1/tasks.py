from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Task as TaskModel, Project as ProjectModel, Client as ClientModel
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse
from app.api.deps import get_current_user, require_permission, get_user_permissions, get_user_team_ids

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _can_access_task_project(project_id: UUID, db: Session, team_ids: set[UUID], is_admin: bool) -> bool:
    if is_admin:
        return True
    proj = db.query(ProjectModel).filter(ProjectModel.id == project_id).first()
    return proj and proj.client and proj.client.team_id in team_ids


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    db: Session = Depends(get_db),
    user=Depends(require_permission("tasks:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    project_id: UUID | None = None,
    assignee_id: UUID | None = None,
    status_filter: str | None = None,
):
    qry = db.query(TaskModel).join(ProjectModel).join(ClientModel)
    if "admin:all" not in permissions:
        if not team_ids:
            return []
        qry = qry.filter(ClientModel.team_id.in_(team_ids))
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
):
    if not _can_access_task_project(data.project_id, db, team_ids, "admin:all" in permissions):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot add task to this project")
    task = TaskModel(
        project_id=data.project_id,
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        assignee_id=data.assignee_id,
        due_date=data.due_date,
        order_index=data.order_index,
        created_by=user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("tasks:read")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if not _can_access_task_project(task.project_id, db, team_ids, "admin:all" in permissions):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: UUID,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("tasks:write")),
    permissions=Depends(get_user_permissions),
    team_ids=Depends(get_user_team_ids),
):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if not _can_access_task_project(task.project_id, db, team_ids, "admin:all" in permissions):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(task, k, v)
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
):
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if not _can_access_task_project(task.project_id, db, team_ids, "admin:all" in permissions):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    db.delete(task)
    db.commit()
