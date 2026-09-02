"""Kanban boards: multiple boards per project, created by admins/managers.
Non-managers see only boards they are members of; board membership also grants
visibility of the tasks placed on that board (see tasks router)."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.database import get_db
from app.models import Board as BoardModel, BoardMember as BoardMemberModel, Project as ProjectModel, Task as TaskModel, User as UserModel, Notification as NotificationModel
from app.schemas.board import BoardCreate, BoardUpdate, BoardResponse, BoardMemberAdd, BoardMemberResponse
from app.schemas.task import TaskResponse
from app.api.deps import require_permission, get_user_permissions, get_user_team_ids, get_manager_scope_user_ids
from app.services.activity_service import log_activity, tasks_updated_this_request, notifications_updated_this_request
from app.services import email_service

router = APIRouter(prefix="/boards", tags=["boards"])


def _is_project_manager(db: Session, project_id: UUID, user, permissions: set, manager_scope: set[UUID] | None) -> bool:
    """Admin, or a manager whose scope covers the project owner (may manage the project's boards)."""
    if "admin:all" in permissions:
        return True
    if manager_scope is None:
        return False
    proj = db.query(ProjectModel).filter(ProjectModel.id == project_id, ProjectModel.deleted_at.is_(None)).first()
    return proj is not None and proj.owner_id is not None and proj.owner_id in manager_scope


def _can_view_board(db: Session, board: BoardModel, user, permissions: set, manager_scope: set[UUID] | None) -> bool:
    # Boards of soft-deleted projects are hidden for everyone
    proj_alive = db.query(ProjectModel.id).filter(
        ProjectModel.id == board.project_id, ProjectModel.deleted_at.is_(None)
    ).first()
    if not proj_alive:
        return False
    if "admin:all" in permissions or board.created_by == user.id:
        return True
    is_member = db.query(BoardMemberModel).filter(
        BoardMemberModel.board_id == board.id, BoardMemberModel.user_id == user.id
    ).first() is not None
    if is_member:
        return True
    return _is_project_manager(db, board.project_id, user, permissions, manager_scope)


def _board_response(db: Session, board: BoardModel) -> BoardResponse:
    member_rows = (
        db.query(BoardMemberModel.user_id, UserModel.full_name, UserModel.email)
        .join(UserModel, UserModel.id == BoardMemberModel.user_id)
        .filter(BoardMemberModel.board_id == board.id)
        .all()
    )
    task_count = db.query(func.count(TaskModel.id)).filter(TaskModel.board_id == board.id).scalar() or 0
    return BoardResponse(
        id=board.id,
        project_id=board.project_id,
        name=board.name,
        position=board.position,
        created_by=board.created_by,
        created_at=board.created_at,
        updated_at=board.updated_at,
        members=[BoardMemberResponse(user_id=r[0], full_name=r[1], email=r[2]) for r in member_rows],
        task_count=task_count,
    )


@router.get("", response_model=list[BoardResponse])
def list_boards(
    db: Session = Depends(get_db),
    user=Depends(require_permission("tasks:read")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
    project_id: UUID | None = Query(None),
):
    qry = db.query(BoardModel).join(ProjectModel, BoardModel.project_id == ProjectModel.id).filter(
        ProjectModel.deleted_at.is_(None)
    )
    if project_id:
        qry = qry.filter(BoardModel.project_id == project_id)
    boards = qry.order_by(BoardModel.position, BoardModel.created_at).all()
    visible = [b for b in boards if _can_view_board(db, b, user, permissions, manager_scope)]
    return [_board_response(db, b) for b in visible]


@router.post("", response_model=BoardResponse, status_code=status.HTTP_201_CREATED)
def create_board(
    data: BoardCreate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    proj = db.query(ProjectModel).filter(ProjectModel.id == data.project_id, ProjectModel.deleted_at.is_(None)).first()
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if not _is_project_manager(db, data.project_id, user, permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins or the project's manager can create boards")
    board = BoardModel(project_id=data.project_id, name=data.name.strip(), position=data.position, created_by=user.id)
    db.add(board)
    db.flush()
    # Creator is always a member; add requested members (must be active users)
    member_ids = {user.id} | set(data.member_ids)
    valid_ids = {
        r[0] for r in db.query(UserModel.id).filter(UserModel.id.in_(member_ids), UserModel.is_active == True).all()
    }
    for uid in valid_ids:
        db.add(BoardMemberModel(board_id=board.id, user_id=uid))
    db.flush()
    log_activity(db, user.id, "board_created", "board", board.id, details=f"Board: {board.name}")
    tasks_updated_this_request.set(True)
    db.commit()
    db.refresh(board)
    return _board_response(db, board)


@router.get("/{board_id}", response_model=BoardResponse)
def get_board(
    board_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("tasks:read")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    board = db.query(BoardModel).filter(BoardModel.id == board_id).first()
    if not board or not _can_view_board(db, board, user, permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    return _board_response(db, board)


@router.get("/{board_id}/tasks", response_model=list[TaskResponse])
def list_board_tasks(
    board_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("tasks:read")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    """All tasks on the board, for members/managers/admins — the kanban view data."""
    board = db.query(BoardModel).filter(BoardModel.id == board_id).first()
    if not board or not _can_view_board(db, board, user, permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    return (
        db.query(TaskModel)
        .filter(TaskModel.board_id == board_id)
        .order_by(TaskModel.column_order, TaskModel.created_at)
        .all()
    )


@router.patch("/{board_id}", response_model=BoardResponse)
def update_board(
    board_id: UUID,
    data: BoardUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    board = db.query(BoardModel).filter(BoardModel.id == board_id).first()
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    if board.created_by != user.id and not _is_project_manager(db, board.project_id, user, permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins, the project's manager, or the board creator can edit it")
    if data.name is not None:
        board.name = data.name.strip()
    if data.position is not None:
        board.position = data.position
    db.commit()
    db.refresh(board)
    return _board_response(db, board)


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_board(
    board_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    board = db.query(BoardModel).filter(BoardModel.id == board_id).first()
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    if board.created_by != user.id and not _is_project_manager(db, board.project_id, user, permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins, the project's manager, or the board creator can delete it")
    name = board.name
    # Detach tasks (they stay on the project, just leave the board)
    db.query(TaskModel).filter(TaskModel.board_id == board_id).update({TaskModel.board_id: None})
    db.delete(board)
    db.flush()
    log_activity(db, user.id, "board_deleted", "board", None, details=f"Board deleted: {name}")
    tasks_updated_this_request.set(True)
    db.commit()


@router.post("/{board_id}/members", response_model=BoardResponse, status_code=status.HTTP_201_CREATED)
def add_board_member(
    board_id: UUID,
    data: BoardMemberAdd,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    board = db.query(BoardModel).filter(BoardModel.id == board_id).first()
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    if board.created_by != user.id and not _is_project_manager(db, board.project_id, user, permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins, the project's manager, or the board creator can manage members")
    target = db.query(UserModel).filter(UserModel.id == data.user_id, UserModel.is_active == True).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or inactive")
    existing = db.query(BoardMemberModel).filter(
        BoardMemberModel.board_id == board_id, BoardMemberModel.user_id == data.user_id
    ).first()
    if not existing:
        db.add(BoardMemberModel(board_id=board_id, user_id=data.user_id))
        if data.user_id != user.id:
            db.add(NotificationModel(
                user_id=data.user_id,
                title="Added to board",
                message=f'You were added to the board "{board.name}"',
                link="/boards",
                type="board",
                reference_id=None,
            ))
            email_service.send_notification(target.email, "Added to board", f'You were added to the board "{board.name}"', "/boards")
        notifications_updated_this_request.set(True)
        tasks_updated_this_request.set(True)
        log_activity(db, user.id, "board_member_added", "board", board.id, details=f"{target.full_name or target.email} added to board: {board.name}")
        db.commit()
    return _board_response(db, board)


@router.delete("/{board_id}/members/{user_id}", response_model=BoardResponse)
def remove_board_member(
    board_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    user=Depends(require_permission("projects:write")),
    permissions=Depends(get_user_permissions),
    manager_scope=Depends(get_manager_scope_user_ids),
):
    board = db.query(BoardModel).filter(BoardModel.id == board_id).first()
    if not board:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Board not found")
    if board.created_by != user.id and not _is_project_manager(db, board.project_id, user, permissions, manager_scope):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins, the project's manager, or the board creator can manage members")
    db.query(BoardMemberModel).filter(
        BoardMemberModel.board_id == board_id, BoardMemberModel.user_id == user_id
    ).delete()
    db.commit()
    return _board_response(db, board)
