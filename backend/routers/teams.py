"""
Team Management API for Antika Auction Watcher.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select
from pydantic import BaseModel
from datetime import datetime

from backend.db.models import User
from backend.models.team_models import Team, Membership, MemberRole
from backend.middleware.team_context import TeamContext, get_team_context
from backend.db.database import get_session as get_db
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/teams", tags=["teams"])


# Request/Response Models

class TeamCreate(BaseModel):
    """Request model for creating a team."""
    name: str
    plan_code: str = "FREE"


class TeamResponse(BaseModel):
    """Response model for team."""
    id: int
    name: str
    owner_id: int
    plan_code: str
    created_at: datetime
    member_count: Optional[int] = None


class MembershipCreate(BaseModel):
    """Request model for adding a team member."""
    user_id: int
    role: str = "VIEWER"


class MembershipResponse(BaseModel):
    """Response model for membership."""
    id: int
    team_id: int
    user_id: int
    role: str
    joined_at: datetime
    user_email: Optional[str] = None


class MembershipUpdate(BaseModel):
    """Request model for updating membership role."""
    role: str


# Endpoints

@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new team.
    User who creates the team becomes the owner.
    """
    # Validate plan code
    from backend.services.plan_seeder import validate_plan_code
    if not validate_plan_code(team_data.plan_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid plan code: {team_data.plan_code}"
        )
    
    # Create team
    team = Team(
        name=team_data.name,
        owner_id=current_user.id,
        plan_code=team_data.plan_code
    )
    
    db.add(team)
    db.commit()
    db.refresh(team)
    
    # Add owner as member with OWNER role
    membership = Membership(
        team_id=team.id,
        user_id=current_user.id,
        role=MemberRole.OWNER
    )
    
    db.add(membership)
    db.commit()
    
    return TeamResponse(
        id=team.id,
        name=team.name,
        owner_id=team.owner_id,
        plan_code=team.plan_code,
        created_at=team.created_at,
        member_count=1
    )


@router.get("", response_model=List[TeamResponse])
async def list_teams(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all teams the current user is a member of.
    """
    # Get user's memberships
    statement = select(Membership).where(Membership.user_id == current_user.id)
    memberships = db.exec(statement).all()
    
    teams = []
    for membership in memberships:
        # Get team
        team_statement = select(Team).where(Team.id == membership.team_id)
        team = db.exec(team_statement).first()
        
        if team:
            # Count members
            member_count_statement = select(Membership).where(Membership.team_id == team.id)
            member_count = len(db.exec(member_count_statement).all())
            
            teams.append(TeamResponse(
                id=team.id,
                name=team.name,
                owner_id=team.owner_id,
                plan_code=team.plan_code,
                created_at=team.created_at,
                member_count=member_count
            ))
    
    return teams


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get team details.
    User must be a member of the team.
    """
    # Set team ID in header for context extraction
    request.headers.__dict__["_list"] = [
        (b"x-team-id", str(team_id).encode())
    ]
    
    team_context = await get_team_context(request, db, current_user.id, require_team=True)
    
    # Count members
    member_count_statement = select(Membership).where(Membership.team_id == team_id)
    member_count = len(db.exec(member_count_statement).all())
    
    return TeamResponse(
        id=team_context.team.id,
        name=team_context.team.name,
        owner_id=team_context.team.owner_id,
        plan_code=team_context.team.plan_code,
        created_at=team_context.team.created_at,
        member_count=member_count
    )


@router.get("/{team_id}/members", response_model=List[MembershipResponse])
async def list_team_members(
    team_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all members of a team.
    User must be a member of the team.
    """
    # Validate team context
    request.headers.__dict__["_list"] = [
        (b"x-team-id", str(team_id).encode())
    ]
    team_context = await get_team_context(request, db, current_user.id, require_team=True)
    
    # Get memberships
    statement = select(Membership).where(Membership.team_id == team_id)
    memberships = db.exec(statement).all()
    
    # Enrich with user email
    result = []
    for membership in memberships:
        user_statement = select(User).where(User.id == membership.user_id)
        user = db.exec(user_statement).first()
        
        result.append(MembershipResponse(
            id=membership.id,
            team_id=membership.team_id,
            user_id=membership.user_id,
            role=membership.role,
            joined_at=membership.joined_at,
            user_email=user.email if user else None
        ))
    
    return result


@router.post("/{team_id}/members", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
async def add_team_member(
    team_id: int,
    membership_data: MembershipCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Add a member to a team.
    Requires ADMIN or OWNER role.
    """
    # Validate team context and permissions
    request.headers.__dict__["_list"] = [
        (b"x-team-id", str(team_id).encode())
    ]
    team_context = await get_team_context(request, db, current_user.id, require_team=True)
    
    if not team_context.can_manage_members():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMIN or OWNER can add members"
        )
    
    # Check if user exists
    user_statement = select(User).where(User.id == membership_data.user_id)
    user = db.exec(user_statement).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {membership_data.user_id} not found"
        )
    
    # Check if already a member
    existing_statement = select(Membership).where(
        Membership.team_id == team_id,
        Membership.user_id == membership_data.user_id
    )
    existing = db.exec(existing_statement).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of this team"
        )
    
    # Create membership
    membership = Membership(
        team_id=team_id,
        user_id=membership_data.user_id,
        role=membership_data.role,
        invited_by=current_user.id
    )
    
    db.add(membership)
    db.commit()
    db.refresh(membership)
    
    return MembershipResponse(
        id=membership.id,
        team_id=membership.team_id,
        user_id=membership.user_id,
        role=membership.role,
        joined_at=membership.joined_at,
        user_email=user.email
    )


@router.patch("/{team_id}/members/{user_id}", response_model=MembershipResponse)
async def update_member_role(
    team_id: int,
    user_id: int,
    update_data: MembershipUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a team member's role.
    Requires ADMIN or OWNER role.
    Cannot change owner role.
    """
    # Validate team context and permissions
    request.headers.__dict__["_list"] = [
        (b"x-team-id", str(team_id).encode())
    ]
    team_context = await get_team_context(request, db, current_user.id, require_team=True)
    
    if not team_context.can_manage_members():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMIN or OWNER can update member roles"
        )
    
    # Get membership
    statement = select(Membership).where(
        Membership.team_id == team_id,
        Membership.user_id == user_id
    )
    membership = db.exec(statement).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found"
        )
    
    # Cannot change owner role
    if membership.role == MemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change owner role"
        )
    
    # Update role
    membership.role = update_data.role
    db.add(membership)
    db.commit()
    db.refresh(membership)
    
    # Get user email
    user_statement = select(User).where(User.id == user_id)
    user = db.exec(user_statement).first()
    
    return MembershipResponse(
        id=membership.id,
        team_id=membership.team_id,
        user_id=membership.user_id,
        role=membership.role,
        joined_at=membership.joined_at,
        user_email=user.email if user else None
    )


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: int,
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a member from a team.
    Requires ADMIN or OWNER role.
    Cannot remove owner.
    """
    # Validate team context and permissions
    request.headers.__dict__["_list"] = [
        (b"x-team-id", str(team_id).encode())
    ]
    team_context = await get_team_context(request, db, current_user.id, require_team=True)
    
    if not team_context.can_manage_members():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMIN or OWNER can remove members"
        )
    
    # Get membership
    statement = select(Membership).where(
        Membership.team_id == team_id,
        Membership.user_id == user_id
    )
    membership = db.exec(statement).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membership not found"
        )
    
    # Cannot remove owner
    if membership.role == MemberRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove team owner"
        )
    
    # Delete membership
    db.delete(membership)
    db.commit()
    
    return None
