"""
Team Context Middleware for Antika Auction Watcher.
Extracts team context from request headers and validates membership.
"""
from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
import logging

from backend.models.team_models import Team, Membership, MemberRole
from backend.db.models import User

logger = logging.getLogger(__name__)


class TeamContext:
    """
    Team context attached to request for access control.
    """
    def __init__(
        self,
        team_id: int,
        team: Team,
        user_id: int,
        membership: Membership,
        role: str
    ):
        self.team_id = team_id
        self.team = team
        self.user_id = user_id
        self.membership = membership
        self.role = role
    
    def is_owner(self) -> bool:
        """Check if user is team owner."""
        return self.role == MemberRole.OWNER
    
    def is_admin(self) -> bool:
        """Check if user is admin or owner."""
        return self.role in [MemberRole.OWNER, MemberRole.ADMIN]
    
    def is_analyst(self) -> bool:
        """Check if user has analyst access or higher."""
        return self.role in [MemberRole.OWNER, MemberRole.ADMIN, MemberRole.ANALYST]
    
    def can_manage_agents(self) -> bool:
        """Check if user can start/stop agents."""
        return self.role in [MemberRole.OWNER, MemberRole.ADMIN, MemberRole.ANALYST]
    
    def can_manage_members(self) -> bool:
        """Check if user can add/remove team members."""
        return self.role in [MemberRole.OWNER, MemberRole.ADMIN]
    
    def can_view(self) -> bool:
        """Check if user has at least viewer access."""
        return self.role in [MemberRole.OWNER, MemberRole.ADMIN, MemberRole.ANALYST, MemberRole.VIEWER]


async def get_team_context(
    request: Request,
    db: Session,
    user_id: int,
    require_team: bool = True
) -> Optional[TeamContext]:
    """
    Extract and validate team context from request.
    
    Args:
        request: FastAPI request
        db: Database session
        user_id: Current user ID
        require_team: If True, raise exception if team not found
        
    Returns:
        TeamContext or None
        
    Raises:
        HTTPException: If team not found or user not member
    """
    # Get team ID from header
    team_id_str = request.headers.get("X-Team-Id")
    
    if not team_id_str:
        if require_team:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Team-Id header required"
            )
        return None
    
    try:
        team_id = int(team_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid team ID format"
        )
    
    # Get team
    team_statement = select(Team).where(Team.id == team_id)
    team = db.exec(team_statement).first()
    
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team {team_id} not found"
        )
    
    # Get membership
    membership_statement = select(Membership).where(
        Membership.team_id == team_id,
        Membership.user_id == user_id
    )
    membership = db.exec(membership_statement).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User {user_id} is not a member of team {team_id}"
        )
    
    # Create context
    context = TeamContext(
        team_id=team_id,
        team=team,
        user_id=user_id,
        membership=membership,
        role=membership.role
    )
    
    logger.info(f"Team context: user {user_id}, team {team_id}, role {context.role}")
    
    return context


def require_role(min_role: MemberRole):
    """
    Decorator to require minimum role for endpoint.
    
    Usage:
        @router.get("/agents")
        @require_role(MemberRole.ANALYST)
        async def list_agents(team_context: TeamContext = Depends(get_team_context)):
            ...
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            # Get team_context from kwargs
            team_context = kwargs.get("team_context")
            
            if not team_context:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Team context required"
                )
            
            # Check role hierarchy
            role_hierarchy = {
                MemberRole.VIEWER: 1,
                MemberRole.ANALYST: 2,
                MemberRole.ADMIN: 3,
                MemberRole.OWNER: 4
            }
            
            user_role_level = role_hierarchy.get(team_context.role, 0)
            required_role_level = role_hierarchy.get(min_role, 0)
            
            if user_role_level < required_role_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Minimum role required: {min_role}"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class TeamContextMiddleware:
    """
    Middleware to inject team context into request state.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        """
        Process request and inject team context if available.
        """
        # Skip for public endpoints
        public_paths = ["/health", "/api/v1/auth", "/api/v1/plans", "/docs", "/openapi.json"]
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)
        
        # Extract team context if header present
        team_id = request.headers.get("X-Team-Id")
        if team_id:
            request.state.team_id = team_id
            logger.debug(f"Team context middleware: team_id={team_id}")
        
        response = await call_next(request)
        return response
