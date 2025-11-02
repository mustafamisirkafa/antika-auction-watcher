"""
Usage Tracker Service for Antika Auction Watcher.
Tracks active agents and daily starts, saves hourly summaries.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlmodel import Session, select
import redis.asyncio as redis
import asyncio
import logging

from backend.models.team_models import Team, Usage

logger = logging.getLogger(__name__)


class UsageTracker:
    """
    Tracks and aggregates team usage statistics.
    Runs as a background task to save hourly summaries.
    """
    
    def __init__(self, redis_client: redis.Redis, db_session: Session):
        """
        Initialize usage tracker.
        
        Args:
            redis_client: Redis client
            db_session: Database session
        """
        self.redis = redis_client
        self.db = db_session
        self._running = False
    
    async def record_usage_snapshot(self, team_id: int) -> Usage:
        """
        Record current usage snapshot for a team.
        
        Args:
            team_id: Team ID
            
        Returns:
            Created Usage record
        """
        # Get active agent count
        active_count = await self.redis.scard(f"team:{team_id}:active_agents")
        
        # Get daily starts
        today = datetime.utcnow().strftime("%Y-%m-%d")
        daily_starts = await self.redis.get(f"team:{team_id}:starts:{today}")
        daily_starts = int(daily_starts) if daily_starts else 0
        
        # Create usage record
        usage = Usage(
            team_id=team_id,
            active_agents=active_count,
            daily_starts=daily_starts,
            timestamp=datetime.utcnow()
        )
        
        self.db.add(usage)
        self.db.commit()
        self.db.refresh(usage)
        
        logger.info(f"Recorded usage for team {team_id}: {active_count} active, {daily_starts} starts")
        
        return usage
    
    async def record_all_teams_usage(self) -> List[Usage]:
        """
        Record usage snapshots for all teams.
        
        Returns:
            List of created Usage records
        """
        # Get all teams
        statement = select(Team)
        teams = self.db.exec(statement).all()
        
        usage_records = []
        for team in teams:
            try:
                usage = await self.record_usage_snapshot(team.id)
                usage_records.append(usage)
            except Exception as e:
                logger.error(f"Failed to record usage for team {team.id}: {e}")
        
        logger.info(f"Recorded usage for {len(usage_records)} teams")
        return usage_records
    
    async def get_usage_history(
        self,
        team_id: int,
        hours: int = 24
    ) -> List[Usage]:
        """
        Get usage history for a team.
        
        Args:
            team_id: Team ID
            hours: Number of hours to retrieve
            
        Returns:
            List of Usage records
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        statement = select(Usage).where(
            Usage.team_id == team_id,
            Usage.timestamp >= cutoff
        ).order_by(Usage.timestamp.desc())
        
        usage_records = self.db.exec(statement).all()
        return list(usage_records)
    
    async def get_usage_summary(
        self,
        team_id: int,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get usage summary statistics for a team.
        
        Args:
            team_id: Team ID
            hours: Number of hours to analyze
            
        Returns:
            Dictionary with summary statistics
        """
        history = await self.get_usage_history(team_id, hours)
        
        if not history:
            return {
                "team_id": team_id,
                "hours": hours,
                "avg_active_agents": 0,
                "max_active_agents": 0,
                "min_active_agents": 0,
                "total_starts": 0,
                "data_points": 0
            }
        
        active_counts = [record.active_agents for record in history]
        total_starts = max((record.daily_starts for record in history), default=0)
        
        return {
            "team_id": team_id,
            "hours": hours,
            "avg_active_agents": round(sum(active_counts) / len(active_counts), 2),
            "max_active_agents": max(active_counts),
            "min_active_agents": min(active_counts),
            "total_starts": total_starts,
            "data_points": len(history),
            "latest_snapshot": history[0].timestamp.isoformat() if history else None
        }
    
    async def cleanup_old_usage_records(self, days: int = 30):
        """
        Delete usage records older than specified days.
        
        Args:
            days: Number of days to retain
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        statement = select(Usage).where(Usage.timestamp < cutoff)
        old_records = self.db.exec(statement).all()
        
        for record in old_records:
            self.db.delete(record)
        
        self.db.commit()
        
        logger.info(f"Deleted {len(old_records)} usage records older than {days} days")
    
    async def cleanup_old_start_counters(self, days: int = 7):
        """
        Cleanup old daily start counters from Redis.
        
        Args:
            days: Number of days to retain
        """
        # Get all team IDs
        statement = select(Team.id)
        team_ids = self.db.exec(statement).all()
        
        # Calculate cutoff date
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        deleted = 0
        for team_id in team_ids:
            # Check last N days
            for i in range(days + 1, days + 30):  # Check 7-37 days ago
                date_str = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
                key = f"team:{team_id}:starts:{date_str}"
                if await self.redis.delete(key):
                    deleted += 1
        
        logger.info(f"Cleaned up {deleted} old start counter keys from Redis")
    
    async def run_hourly_task(self):
        """
        Run hourly usage tracking task.
        Records snapshots and performs cleanup.
        """
        self._running = True
        
        logger.info("Starting hourly usage tracker")
        
        while self._running:
            try:
                # Record usage for all teams
                await self.record_all_teams_usage()
                
                # Cleanup old data (run once per day at midnight)
                now = datetime.utcnow()
                if now.hour == 0:
                    await self.cleanup_old_usage_records(days=30)
                    await self.cleanup_old_start_counters(days=7)
                
                # Wait 1 hour
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in usage tracker: {e}", exc_info=True)
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    def stop(self):
        """Stop the hourly task."""
        self._running = False
        logger.info("Stopping hourly usage tracker")


async def start_usage_tracking(redis_client: redis.Redis, db_session: Session):
    """
    Start background usage tracking task.
    
    Args:
        redis_client: Redis client
        db_session: Database session
    """
    tracker = UsageTracker(redis_client, db_session)
    await tracker.run_hourly_task()
