"""Admin-only: CRUD teams, manage team members."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Team as TeamModel, TeamMember
from app.schemas.team import TeamCreate, TeamUpdate, TeamResponse, TeamWithMembersResponse
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/teams", tags=["teams"])


def _team_to_response(t: TeamModel) -> TeamWithMembersResponse:
    return TeamWithMembersResponse(
        id=t.id,
        name=t.name,
        description=t.description,
        team_type=getattr(t, "team_type", None),
        user_ids=[u.id for u in t.users],
    )


@router.get("/my", response_model=list[TeamWithMembersResponse])
def list_my_teams(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Teams the current user is a member of (for dropdowns when not admin)."""
    return [_team_to_response(t) for t in user.teams]


@router.get("", response_model=list[TeamWithMembersResponse])
def list_teams(
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    teams = db.query(TeamModel).all()
    return [_team_to_response(t) for t in teams]


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
def create_team(
    data: TeamCreate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    team = TeamModel(
        name=data.name,
        description=data.description,
        team_type=getattr(data, "team_type", None),
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.get("/{team_id}", response_model=TeamWithMembersResponse)
def get_team(
    team_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    return _team_to_response(team)


@router.patch("/{team_id}", response_model=TeamResponse)
def update_team(
    team_id: UUID,
    data: TeamUpdate,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    if data.name is not None:
        team.name = data.name
    if data.description is not None:
        team.description = data.description
    if data.team_type is not None:
        team.team_type = data.team_type
    db.commit()
    db.refresh(team)
    return team


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    db.delete(team)
    db.commit()


@router.post("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def add_team_member(
    team_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    team = db.query(TeamModel).filter(TeamModel.id == team_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
    if db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id).first():
        return  # already member
    db.add(TeamMember(team_id=team_id, user_id=user_id))
    db.commit()


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_member(
    team_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    _user=Depends(require_admin),
):
    db.query(TeamMember).filter(TeamMember.team_id == team_id, TeamMember.user_id == user_id).delete()
    db.commit()
