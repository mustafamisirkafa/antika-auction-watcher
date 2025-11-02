"""
Feedback Collector Service
Collects, stores, and manages user feedback for advisor recommendations
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json
import redis.asyncio as redis


class FeedbackType(str, Enum):
    """Types of feedback users can provide"""
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"
    ACCURATE = "accurate"
    INACCURATE = "inaccurate"


class OutcomeType(str, Enum):
    """Actual auction outcomes"""
    WON = "won"
    LOST = "lost"
    SKIPPED = "skipped"


@dataclass
class FeedbackEntry:
    """Individual feedback entry"""
    feedback_id: str
    item_id: str
    recommendation_id: str
    user_id: str
    feedback_type: FeedbackType
    recommendation_level: str  # strong_buy, buy, watch, skip, avoid
    confidence: float
    suggested_max_bid: Optional[float]
    
    # Actual outcome
    actual_outcome: Optional[OutcomeType] = None
    won: Optional[bool] = None
    final_price: Optional[float] = None
    profitable: Optional[bool] = None
    profit_amount: Optional[float] = None
    
    # Metadata
    comment: Optional[str] = None
    timestamp: datetime = None
    processed: bool = False
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['feedback_type'] = self.feedback_type.value if isinstance(self.feedback_type, Enum) else self.feedback_type
        if self.actual_outcome:
            data['actual_outcome'] = self.actual_outcome.value if isinstance(self.actual_outcome, Enum) else self.actual_outcome
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FeedbackEntry':
        """Create from dictionary"""
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp']) if isinstance(data['timestamp'], str) else data['timestamp']
        data['feedback_type'] = FeedbackType(data['feedback_type'])
        if data.get('actual_outcome'):
            data['actual_outcome'] = OutcomeType(data['actual_outcome'])
        return cls(**data)


@dataclass
class FeedbackSummary:
    """Summary of feedback statistics"""
    total_feedback: int
    helpful_count: int
    not_helpful_count: int
    accurate_count: int
    inaccurate_count: int
    
    # By recommendation level
    by_recommendation: Dict[str, Dict[str, int]]
    
    # Accuracy metrics
    accuracy_rate: float
    helpfulness_rate: float
    
    # Outcome metrics
    total_with_outcome: int
    won_count: int
    lost_count: int
    win_rate: float
    
    # Time range
    start_date: datetime
    end_date: datetime
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "total_feedback": self.total_feedback,
            "helpful_count": self.helpful_count,
            "not_helpful_count": self.not_helpful_count,
            "accurate_count": self.accurate_count,
            "inaccurate_count": self.inaccurate_count,
            "by_recommendation": self.by_recommendation,
            "accuracy_rate": self.accuracy_rate,
            "helpfulness_rate": self.helpfulness_rate,
            "total_with_outcome": self.total_with_outcome,
            "won_count": self.won_count,
            "lost_count": self.lost_count,
            "win_rate": self.win_rate,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat()
        }


class FeedbackCollector:
    """
    Collects and manages user feedback for learning
    Uses Redis for fast storage and retrieval
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """
        Initialize collector with Redis client
        
        Args:
            redis_client: Redis async client (creates new if None)
        """
        self.redis = redis_client
        self.feedback_key = "advisor:feedback:pending"
        self.processed_key = "advisor:feedback:processed"
        self.summary_key = "advisor:feedback:summary"
    
    async def initialize(self):
        """Initialize Redis connection if not provided"""
        if self.redis is None:
            self.redis = await redis.from_url(
                "redis://localhost:6379",
                encoding="utf-8",
                decode_responses=True
            )
    
    async def add_feedback(
        self,
        item_id: str,
        recommendation_id: str,
        user_id: str,
        feedback_type: FeedbackType,
        recommendation_level: str,
        confidence: float,
        suggested_max_bid: Optional[float] = None,
        comment: Optional[str] = None,
        actual_outcome: Optional[Dict] = None
    ) -> FeedbackEntry:
        """
        Add new feedback entry
        
        Args:
            item_id: Item identifier
            recommendation_id: Recommendation identifier
            user_id: User identifier
            feedback_type: Type of feedback (helpful, not_helpful, etc.)
            recommendation_level: Recommendation that was given
            confidence: Confidence of the recommendation
            suggested_max_bid: Suggested max bid (if any)
            comment: Optional user comment
            actual_outcome: Actual auction outcome data
            
        Returns:
            FeedbackEntry object
        """
        await self.initialize()
        
        feedback_id = f"fb_{item_id}_{user_id}_{int(datetime.utcnow().timestamp())}"
        
        # Create feedback entry
        entry = FeedbackEntry(
            feedback_id=feedback_id,
            item_id=item_id,
            recommendation_id=recommendation_id,
            user_id=user_id,
            feedback_type=feedback_type,
            recommendation_level=recommendation_level,
            confidence=confidence,
            suggested_max_bid=suggested_max_bid,
            comment=comment,
            actual_outcome=OutcomeType(actual_outcome.get("outcome")) if actual_outcome and "outcome" in actual_outcome else None,
            won=actual_outcome.get("won") if actual_outcome else None,
            final_price=actual_outcome.get("final_price") if actual_outcome else None,
            profitable=actual_outcome.get("profitable") if actual_outcome else None,
            profit_amount=actual_outcome.get("profit_amount") if actual_outcome else None
        )
        
        # Store in Redis
        await self.redis.hset(
            self.feedback_key,
            feedback_id,
            json.dumps(entry.to_dict())
        )
        
        return entry
    
    async def get_pending_feedback(self, limit: Optional[int] = None) -> List[FeedbackEntry]:
        """
        Get all pending (unprocessed) feedback
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of FeedbackEntry objects
        """
        await self.initialize()
        
        feedback_dict = await self.redis.hgetall(self.feedback_key)
        
        entries = [
            FeedbackEntry.from_dict(json.loads(data))
            for data in feedback_dict.values()
            if not json.loads(data).get("processed", False)
        ]
        
        # Sort by timestamp (oldest first)
        entries.sort(key=lambda x: x.timestamp)
        
        if limit:
            entries = entries[:limit]
        
        return entries
    
    async def mark_processed(self, feedback_ids: List[str]):
        """
        Mark feedback entries as processed
        
        Args:
            feedback_ids: List of feedback IDs to mark
        """
        await self.initialize()
        
        for feedback_id in feedback_ids:
            # Get entry
            data = await self.redis.hget(self.feedback_key, feedback_id)
            if data:
                entry_dict = json.loads(data)
                entry_dict["processed"] = True
                
                # Move to processed set
                await self.redis.hset(
                    self.processed_key,
                    feedback_id,
                    json.dumps(entry_dict)
                )
                
                # Remove from pending
                await self.redis.hdel(self.feedback_key, feedback_id)
    
    async def get_feedback_by_item(self, item_id: str) -> List[FeedbackEntry]:
        """
        Get all feedback for a specific item
        
        Args:
            item_id: Item identifier
            
        Returns:
            List of FeedbackEntry objects
        """
        await self.initialize()
        
        # Check both pending and processed
        pending = await self.redis.hgetall(self.feedback_key)
        processed = await self.redis.hgetall(self.processed_key)
        
        all_feedback = {**pending, **processed}
        
        entries = [
            FeedbackEntry.from_dict(json.loads(data))
            for data in all_feedback.values()
            if json.loads(data).get("item_id") == item_id
        ]
        
        return entries
    
    async def get_feedback_by_user(self, user_id: str, limit: int = 100) -> List[FeedbackEntry]:
        """
        Get feedback from specific user
        
        Args:
            user_id: User identifier
            limit: Maximum entries to return
            
        Returns:
            List of FeedbackEntry objects
        """
        await self.initialize()
        
        processed = await self.redis.hgetall(self.processed_key)
        
        entries = [
            FeedbackEntry.from_dict(json.loads(data))
            for data in processed.values()
            if json.loads(data).get("user_id") == user_id
        ]
        
        # Sort by timestamp (newest first)
        entries.sort(key=lambda x: x.timestamp, reverse=True)
        
        return entries[:limit]
    
    async def get_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> FeedbackSummary:
        """
        Get feedback summary statistics
        
        Args:
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            FeedbackSummary object
        """
        await self.initialize()
        
        # Default to last 30 days
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Get all processed feedback
        processed = await self.redis.hgetall(self.processed_key)
        
        entries = [
            FeedbackEntry.from_dict(json.loads(data))
            for data in processed.values()
        ]
        
        # Filter by date
        entries = [
            e for e in entries
            if start_date <= e.timestamp <= end_date
        ]
        
        if not entries:
            return FeedbackSummary(
                total_feedback=0,
                helpful_count=0,
                not_helpful_count=0,
                accurate_count=0,
                inaccurate_count=0,
                by_recommendation={},
                accuracy_rate=0.0,
                helpfulness_rate=0.0,
                total_with_outcome=0,
                won_count=0,
                lost_count=0,
                win_rate=0.0,
                start_date=start_date,
                end_date=end_date
            )
        
        # Count by type
        helpful = len([e for e in entries if e.feedback_type == FeedbackType.HELPFUL])
        not_helpful = len([e for e in entries if e.feedback_type == FeedbackType.NOT_HELPFUL])
        accurate = len([e for e in entries if e.feedback_type == FeedbackType.ACCURATE])
        inaccurate = len([e for e in entries if e.feedback_type == FeedbackType.INACCURATE])
        
        # Count by recommendation level
        by_recommendation = {}
        for level in ["strong_buy", "buy", "watch", "skip", "avoid"]:
            level_entries = [e for e in entries if e.recommendation_level == level]
            if level_entries:
                by_recommendation[level] = {
                    "total": len(level_entries),
                    "helpful": len([e for e in level_entries if e.feedback_type == FeedbackType.HELPFUL]),
                    "accurate": len([e for e in level_entries if e.feedback_type == FeedbackType.ACCURATE])
                }
        
        # Outcome metrics
        with_outcome = [e for e in entries if e.actual_outcome is not None]
        won = len([e for e in with_outcome if e.won])
        
        return FeedbackSummary(
            total_feedback=len(entries),
            helpful_count=helpful,
            not_helpful_count=not_helpful,
            accurate_count=accurate,
            inaccurate_count=inaccurate,
            by_recommendation=by_recommendation,
            accuracy_rate=accurate / len(entries) if entries else 0.0,
            helpfulness_rate=helpful / len(entries) if entries else 0.0,
            total_with_outcome=len(with_outcome),
            won_count=won,
            lost_count=len(with_outcome) - won,
            win_rate=won / len(with_outcome) if with_outcome else 0.0,
            start_date=start_date,
            end_date=end_date
        )
    
    async def get_pending_count(self) -> int:
        """Get count of pending feedback entries"""
        await self.initialize()
        return await self.redis.hlen(self.feedback_key)
    
    async def clear_old_feedback(self, days: int = 90):
        """
        Clear feedback older than specified days
        
        Args:
            days: Number of days to keep
        """
        await self.initialize()
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        processed = await self.redis.hgetall(self.processed_key)
        
        to_delete = []
        for feedback_id, data in processed.items():
            entry_dict = json.loads(data)
            timestamp = datetime.fromisoformat(entry_dict["timestamp"])
            if timestamp < cutoff_date:
                to_delete.append(feedback_id)
        
        if to_delete:
            await self.redis.hdel(self.processed_key, *to_delete)
        
        return len(to_delete)
