"""
Agent Manager Service for Antika Auction Watcher.
Manages AI agent lifecycle with Redis-backed quota enforcement.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlmodel import Session, select
from fastapi import HTTPException
import redis.asyncio as redis
import json
import logging

from backend.models.team_models import Team, Plan, AgentConfig, Usage
from backend.services.plan_seeder import get_plan_limit

logger = logging.getLogger(__name__)


class AgentManager:
    """
    Manages AI agents for teams with plan-based quota enforcement.
    Uses Redis for real-time active agent tracking.
    """
    
    def __init__(self, redis_client: redis.Redis, db_session: Session):
        """
        Initialize agent manager.
        
        Args:
            redis_client: Redis client for tracking active agents
            db_session: Database session
        """
        self.redis = redis_client
        self.db = db_session
    
    async def can_start_agent(self, team_id: int) -> bool:
        """
        Check if team can start a new agent based on plan limits.
        
        Args:
            team_id: Team ID
            
        Returns:
            True if team can start agent, False otherwise
        """
        # Get team plan
        team = await self._get_team(team_id)
        plan_limit = get_plan_limit(team.plan_code)
        
        # Get active agent count from Redis
        active_count = await self._get_active_agent_count(team_id)
        
        logger.info(f"Team {team_id} has {active_count}/{plan_limit} active agents")
        
        return active_count < plan_limit
    
    async def start_agent(
        self,
        team_id: int,
        agent_config: Dict[str, Any],
        user_id: int
    ) -> AgentConfig:
        """
        Start a new AI agent for a team.
        Enforces plan limits and creates agent configuration.
        
        Args:
            team_id: Team ID
            agent_config: Agent configuration dictionary
            user_id: User ID who is starting the agent
            
        Returns:
            Created AgentConfig
            
        Raises:
            HTTPException: If plan limit reached or team not found
        """
        # Check if team can start agent
        if not await self.can_start_agent(team_id):
            team = await self._get_team(team_id)
            plan_limit = get_plan_limit(team.plan_code)
            raise HTTPException(
                status_code=402,
                detail=f"Plan limit reached. Your {team.plan_code} plan allows {plan_limit} active agents. Upgrade to enable more."
            )
        
        # Create agent configuration in database
        agent = AgentConfig(
            team_id=team_id,
            name=agent_config.get("name", "Unnamed Agent"),
            agent_type=agent_config.get("type", "watcher"),
            status="running",
            config_json=json.dumps(agent_config),
            created_by=user_id,
            last_started_at=datetime.utcnow()
        )
        
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        
        # Add to Redis active agents set
        await self.redis.sadd(f"team:{team_id}:active_agents", str(agent.id))
        
        # Increment daily starts counter
        today = datetime.utcnow().strftime("%Y-%m-%d")
        await self.redis.incr(f"team:{team_id}:starts:{today}")
        
        logger.info(f"Started agent {agent.id} for team {team_id}")
        
        return agent
    
    async def stop_agent(self, team_id: int, agent_id: int) -> AgentConfig:
        """
        Stop a running agent.
        
        Args:
            team_id: Team ID
            agent_id: Agent ID
            
        Returns:
            Updated AgentConfig
            
        Raises:
            HTTPException: If agent not found
        """
        # Get agent from database
        statement = select(AgentConfig).where(
            AgentConfig.id == agent_id,
            AgentConfig.team_id == team_id
        )
        agent = self.db.exec(statement).first()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Update agent status
        agent.status = "stopped"
        agent.last_stopped_at = datetime.utcnow()
        
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        
        # Remove from Redis active agents set
        await self.redis.srem(f"team:{team_id}:active_agents", str(agent_id))
        
        logger.info(f"Stopped agent {agent_id} for team {team_id}")
        
        return agent
    
    async def pause_agent(self, team_id: int, agent_id: int) -> AgentConfig:
        """
        Pause a running agent (keeps in active count but not executing).
        
        Args:
            team_id: Team ID
            agent_id: Agent ID
            
        Returns:
            Updated AgentConfig
        """
        statement = select(AgentConfig).where(
            AgentConfig.id == agent_id,
            AgentConfig.team_id == team_id
        )
        agent = self.db.exec(statement).first()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        agent.status = "paused"
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        
        logger.info(f"Paused agent {agent_id} for team {team_id}")
        
        return agent
    
    async def get_active_agents(self, team_id: int) -> List[AgentConfig]:
        """
        Get all active agents for a team.
        
        Args:
            team_id: Team ID
            
        Returns:
            List of active AgentConfig objects
        """
        statement = select(AgentConfig).where(
            AgentConfig.team_id == team_id,
            AgentConfig.status.in_(["running", "paused"])
        )
        agents = self.db.exec(statement).all()
        return list(agents)
    
    async def get_agent_by_id(self, team_id: int, agent_id: int) -> Optional[AgentConfig]:
        """
        Get agent by ID.
        
        Args:
            team_id: Team ID
            agent_id: Agent ID
            
        Returns:
            AgentConfig or None
        """
        statement = select(AgentConfig).where(
            AgentConfig.id == agent_id,
            AgentConfig.team_id == team_id
        )
        return self.db.exec(statement).first()
    
    async def get_usage_stats(self, team_id: int) -> Dict[str, Any]:
        """
        Get current usage statistics for a team.
        
        Args:
            team_id: Team ID
            
        Returns:
            Dictionary with usage statistics
        """
        team = await self._get_team(team_id)
        plan_limit = get_plan_limit(team.plan_code)
        active_count = await self._get_active_agent_count(team_id)
        
        # Get daily starts
        today = datetime.utcnow().strftime("%Y-%m-%d")
        daily_starts = await self.redis.get(f"team:{team_id}:starts:{today}")
        daily_starts = int(daily_starts) if daily_starts else 0
        
        # Get all agents (active and inactive)
        statement = select(AgentConfig).where(AgentConfig.team_id == team_id)
        all_agents = self.db.exec(statement).all()
        
        return {
            "team_id": team_id,
            "plan_code": team.plan_code,
            "agent_limit": plan_limit,
            "active_agents": active_count,
            "available_slots": plan_limit - active_count,
            "daily_starts": daily_starts,
            "total_agents": len(all_agents),
            "utilization_percent": round((active_count / plan_limit) * 100, 2) if plan_limit > 0 else 0
        }
    
    async def cleanup_stale_agents(self, team_id: int):
        """
        Cleanup stale agent entries in Redis.
        Ensures Redis set matches database state.
        
        Args:
            team_id: Team ID
        """
        # Get active agents from database
        active_agents = await self.get_active_agents(team_id)
        active_ids = {str(agent.id) for agent in active_agents}
        
        # Get active agents from Redis
        redis_ids = await self.redis.smembers(f"team:{team_id}:active_agents")
        redis_ids = {id.decode() if isinstance(id, bytes) else id for id in redis_ids}
        
        # Remove stale entries
        stale_ids = redis_ids - active_ids
        if stale_ids:
            await self.redis.srem(f"team:{team_id}:active_agents", *stale_ids)
            logger.info(f"Cleaned up {len(stale_ids)} stale agent entries for team {team_id}")
    
    # Private helper methods
    
    async def _get_team(self, team_id: int) -> Team:
        """Get team by ID or raise HTTPException."""
        statement = select(Team).where(Team.id == team_id)
        team = self.db.exec(statement).first()
        
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        return team
    
    async def _get_active_agent_count(self, team_id: int) -> int:
        """Get active agent count from Redis."""
        count = await self.redis.scard(f"team:{team_id}:active_agents")
        return count
