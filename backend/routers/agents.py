"""
Agent Management API for Antika Auction Watcher.
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session
from pydantic import BaseModel
from datetime import datetime
import redis.asyncio as redis

from backend.models.team_models import AgentConfig
from backend.services.agent_manager import AgentManager
from backend.services.usage_tracker import UsageTracker
from backend.middleware.team_context import get_team_context, TeamContext
from backend.db.database import get_session as get_db
from backend.routers.auth import get_current_user
from backend.realtime.redis_manager import RedisManager

def get_redis():
    """Get Redis client dependency."""
    from backend.main import redis_manager
    return redis_manager.redis

router = APIRouter(prefix="/agents", tags=["agents"])


# Request/Response Models

class AgentStartRequest(BaseModel):
    """Request model for starting an agent."""
    name: str
    type: str = "watcher"  # watcher, bidder, analyzer
    config: Dict[str, Any] = {}


class AgentResponse(BaseModel):
    """Response model for agent."""
    id: int
    team_id: int
    name: str
    agent_type: str
    status: str
    created_by: int
    created_at: datetime
    last_started_at: datetime | None
    last_stopped_at: datetime | None


class UsageStatsResponse(BaseModel):
    """Response model for usage statistics."""
    team_id: int
    plan_code: str
    agent_limit: int
    active_agents: int
    available_slots: int
    daily_starts: int
    total_agents: int
    utilization_percent: float


# Endpoints

@router.post("/start", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def start_agent(
    agent_data: AgentStartRequest,
    request: Request,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    current_user = Depends(get_current_user),
    team_context: TeamContext = Depends(get_team_context)
):
    """
    Start a new AI agent.
    Enforces plan limits.
    Requires ANALYST role or higher.
    """
    if not team_context.can_manage_agents():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage agents"
        )
    
    # Create agent manager
    agent_manager = AgentManager(redis_client, db)
    
    # Prepare agent config
    agent_config = {
        "name": agent_data.name,
        "type": agent_data.type,
        **agent_data.config
    }
    
    # Start agent (will check limits)
    try:
        agent = await agent_manager.start_agent(
            team_id=team_context.team_id,
            agent_config=agent_config,
            user_id=current_user.id
        )
    except HTTPException as e:
        # Re-raise with user-friendly message
        if e.status_code == 402:
            raise HTTPException(
                status_code=402,
                detail={
                    "message": e.detail,
                    "plan_code": team_context.team.plan_code,
                    "upgrade_url": "/settings/plan"
                }
            )
        raise
    
    return AgentResponse(
        id=agent.id,
        team_id=agent.team_id,
        name=agent.name,
        agent_type=agent.agent_type,
        status=agent.status,
        created_by=agent.created_by,
        created_at=agent.created_at,
        last_started_at=agent.last_started_at,
        last_stopped_at=agent.last_stopped_at
    )


@router.post("/{agent_id}/stop", response_model=AgentResponse)
async def stop_agent(
    agent_id: int,
    request: Request,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    current_user = Depends(get_current_user),
    team_context: TeamContext = Depends(get_team_context)
):
    """
    Stop a running agent.
    Requires ANALYST role or higher.
    """
    if not team_context.can_manage_agents():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage agents"
        )
    
    # Create agent manager
    agent_manager = AgentManager(redis_client, db)
    
    # Stop agent
    agent = await agent_manager.stop_agent(
        team_id=team_context.team_id,
        agent_id=agent_id
    )
    
    return AgentResponse(
        id=agent.id,
        team_id=agent.team_id,
        name=agent.name,
        agent_type=agent.agent_type,
        status=agent.status,
        created_by=agent.created_by,
        created_at=agent.created_at,
        last_started_at=agent.last_started_at,
        last_stopped_at=agent.last_stopped_at
    )


@router.post("/{agent_id}/pause", response_model=AgentResponse)
async def pause_agent(
    agent_id: int,
    request: Request,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    current_user = Depends(get_current_user),
    team_context: TeamContext = Depends(get_team_context)
):
    """
    Pause a running agent.
    Keeps agent in active count but stops execution.
    """
    if not team_context.can_manage_agents():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to manage agents"
        )
    
    agent_manager = AgentManager(redis_client, db)
    agent = await agent_manager.pause_agent(team_context.team_id, agent_id)
    
    return AgentResponse(
        id=agent.id,
        team_id=agent.team_id,
        name=agent.name,
        agent_type=agent.agent_type,
        status=agent.status,
        created_by=agent.created_by,
        created_at=agent.created_at,
        last_started_at=agent.last_started_at,
        last_stopped_at=agent.last_stopped_at
    )


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    request: Request,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    current_user = Depends(get_current_user),
    team_context: TeamContext = Depends(get_team_context)
):
    """
    List all agents for the team.
    Requires at least VIEWER role.
    """
    if not team_context.can_view():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view agents"
        )
    
    agent_manager = AgentManager(redis_client, db)
    agents = await agent_manager.get_active_agents(team_context.team_id)
    
    return [
        AgentResponse(
            id=agent.id,
            team_id=agent.team_id,
            name=agent.name,
            agent_type=agent.agent_type,
            status=agent.status,
            created_by=agent.created_by,
            created_at=agent.created_at,
            last_started_at=agent.last_started_at,
            last_stopped_at=agent.last_stopped_at
        )
        for agent in agents
    ]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    request: Request,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    current_user = Depends(get_current_user),
    team_context: TeamContext = Depends(get_team_context)
):
    """
    Get agent details.
    """
    if not team_context.can_view():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to view agents"
        )
    
    agent_manager = AgentManager(redis_client, db)
    agent = await agent_manager.get_agent_by_id(team_context.team_id, agent_id)
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return AgentResponse(
        id=agent.id,
        team_id=agent.team_id,
        name=agent.name,
        agent_type=agent.agent_type,
        status=agent.status,
        created_by=agent.created_by,
        created_at=agent.created_at,
        last_started_at=agent.last_started_at,
        last_stopped_at=agent.last_stopped_at
    )


@router.get("/usage/{team_id}", response_model=UsageStatsResponse)
async def get_usage_stats(
    team_id: int,
    request: Request,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    current_user = Depends(get_current_user)
):
    """
    Get current usage statistics for a team.
    User must be a member of the team.
    """
    # Validate team membership
    request.headers.__dict__["_list"] = [
        (b"x-team-id", str(team_id).encode())
    ]
    team_context = await get_team_context(request, db, current_user.id, require_team=True)
    
    # Get usage stats
    agent_manager = AgentManager(redis_client, db)
    stats = await agent_manager.get_usage_stats(team_id)
    
    return UsageStatsResponse(**stats)
