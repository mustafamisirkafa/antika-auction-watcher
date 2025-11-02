"""
Feedback Learner Service
Learns from user feedback and adjusts advisor weights and parameters
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import json
import statistics
import redis.asyncio as redis

from backend.services.feedback_collector import (
    FeedbackCollector,
    FeedbackEntry,
    FeedbackType
)


@dataclass
class SenseWeights:
    """Weights for each sense in the advisor"""
    pattern: float = 0.30
    market: float = 0.25
    behavior: float = 0.20
    risk: float = 0.25
    
    def normalize(self):
        """Ensure weights sum to 1.0"""
        total = self.pattern + self.market + self.behavior + self.risk
        if total > 0:
            self.pattern /= total
            self.market /= total
            self.behavior /= total
            self.risk /= total
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    from_dict(cls, data: Dict) -> 'SenseWeights':
        return cls(**data)


@dataclass
class LearningMetrics:
    """Metrics from learning cycle"""
    cycle_id: str
    timestamp: datetime
    feedback_processed: int
    
    # Accuracy metrics
    overall_accuracy: float
    accuracy_by_recommendation: Dict[str, float]
    
    # Helpfulness metrics
    helpfulness_rate: float
    
    # Weight adjustments
    old_weights: SenseWeights
    new_weights: SenseWeights
    weight_changes: Dict[str, float]
    
    # Improvement
    accuracy_improvement: float
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['old_weights'] = self.old_weights.to_dict()
        data['new_weights'] = self.new_weights.to_dict()
        return data


class FeedbackLearner:
    """
    Learns from feedback to improve advisor accuracy
    Adjusts sense weights based on performance
    """
    
    def __init__(
        self,
        feedback_collector: FeedbackCollector,
        redis_client: Optional[redis.Redis] = None
    ):
        """
        Initialize learner
        
        Args:
            feedback_collector: FeedbackCollector instance
            redis_client: Redis async client
        """
        self.collector = feedback_collector
        self.redis = redis_client
        self.weights_key = "advisor:learning:weights"
        self.metrics_key = "advisor:learning:metrics"
        self.learning_rate = 0.1  # How fast to adjust weights
        self.min_feedback_batch = 10  # Minimum feedback before learning
    
    async def initialize(self):
        """Initialize Redis connection"""
        if self.redis is None:
            self.redis = await redis.from_url(
                "redis://localhost:6379",
                encoding="utf-8",
                decode_responses=True
            )
        await self.collector.initialize()
    
    async def get_current_weights(self) -> SenseWeights:
        """
        Get current sense weights from Redis
        
        Returns:
            SenseWeights object
        """
        await self.initialize()
        
        weights_data = await self.redis.get(self.weights_key)
        
        if weights_data:
            return SenseWeights.from_dict(json.loads(weights_data))
        else:
            # Return default weights
            default_weights = SenseWeights()
            await self.save_weights(default_weights)
            return default_weights
    
    async def save_weights(self, weights: SenseWeights):
        """
        Save sense weights to Redis
        
        Args:
            weights: SenseWeights to save
        """
        await self.initialize()
        
        # Ensure normalized
        weights.normalize()
        
        await self.redis.set(
            self.weights_key,
            json.dumps(weights.to_dict())
        )
    
    async def learn_from_feedback(self, force: bool = False) -> Optional[LearningMetrics]:
        """
        Main learning method - analyzes feedback and adjusts weights
        
        Args:
            force: Force learning even if min batch size not met
            
        Returns:
            LearningMetrics if learning occurred, None otherwise
        """
        await self.initialize()
        
        # Get pending feedback
        feedback = await self.collector.get_pending_feedback()
        
        if len(feedback) < self.min_feedback_batch and not force:
            return None
        
        if not feedback:
            return None
        
        # Get current weights
        old_weights = await self.get_current_weights()
        
        # Analyze feedback to determine sense performance
        sense_performance = await self._analyze_sense_performance(feedback)
        
        # Calculate new weights based on performance
        new_weights = await self._calculate_new_weights(old_weights, sense_performance)
        
        # Save new weights
        await self.save_weights(new_weights)
        
        # Calculate metrics
        accuracy = await self._calculate_accuracy(feedback)
        helpfulness = len([f for f in feedback if f.feedback_type == FeedbackType.HELPFUL]) / len(feedback)
        
        # Get previous accuracy for improvement calculation
        prev_metrics = await self.get_recent_metrics(limit=1)
        prev_accuracy = prev_metrics[0].overall_accuracy if prev_metrics else 0.5
        
        # Create learning metrics
        metrics = LearningMetrics(
            cycle_id=f"learn_{int(datetime.utcnow().timestamp())}",
            timestamp=datetime.utcnow(),
            feedback_processed=len(feedback),
            overall_accuracy=accuracy["overall"],
            accuracy_by_recommendation=accuracy["by_recommendation"],
            helpfulness_rate=helpfulness,
            old_weights=old_weights,
            new_weights=new_weights,
            weight_changes={
                "pattern": new_weights.pattern - old_weights.pattern,
                "market": new_weights.market - old_weights.market,
                "behavior": new_weights.behavior - old_weights.behavior,
                "risk": new_weights.risk - old_weights.risk
            },
            accuracy_improvement=accuracy["overall"] - prev_accuracy
        )
        
        # Save metrics
        await self._save_metrics(metrics)
        
        # Mark feedback as processed
        await self.collector.mark_processed([f.feedback_id for f in feedback])
        
        return metrics
    
    async def _analyze_sense_performance(self, feedback: List[FeedbackEntry]) -> Dict[str, float]:
        """
        Analyze which senses are performing well
        
        Args:
            feedback: List of feedback entries
            
        Returns:
            Dict mapping sense name to performance score (0-1)
        """
        # For now, use overall accuracy as baseline
        # In production, would analyze individual sense scores from recommendations
        
        accurate = len([f for f in feedback if f.feedback_type == FeedbackType.ACCURATE])
        helpful = len([f for f in feedback if f.feedback_type == FeedbackType.HELPFUL])
        
        overall_positive = (accurate + helpful) / len(feedback) if feedback else 0.5
        
        # Analyze by recommendation level to infer sense performance
        by_level = {}
        for level in ["strong_buy", "buy", "watch", "skip", "avoid"]:
            level_feedback = [f for f in feedback if f.recommendation_level == level]
            if level_feedback:
                level_positive = len([f for f in level_feedback if f.feedback_type in [FeedbackType.ACCURATE, FeedbackType.HELPFUL]]) / len(level_feedback)
                by_level[level] = level_positive
        
        # Infer sense performance
        # Strong buy/buy rely more on pattern and market
        # Watch/skip rely on behavior and risk
        # Avoid relies heavily on risk
        
        pattern_performance = (
            by_level.get("strong_buy", 0.5) * 0.4 +
            by_level.get("buy", 0.5) * 0.4 +
            overall_positive * 0.2
        )
        
        market_performance = (
            by_level.get("strong_buy", 0.5) * 0.3 +
            by_level.get("buy", 0.5) * 0.3 +
            by_level.get("watch", 0.5) * 0.2 +
            overall_positive * 0.2
        )
        
        behavior_performance = (
            by_level.get("watch", 0.5) * 0.4 +
            by_level.get("skip", 0.5) * 0.3 +
            overall_positive * 0.3
        )
        
        risk_performance = (
            by_level.get("avoid", 0.5) * 0.5 +
            by_level.get("skip", 0.5) * 0.3 +
            overall_positive * 0.2
        )
        
        return {
            "pattern": pattern_performance,
            "market": market_performance,
            "behavior": behavior_performance,
            "risk": risk_performance
        }
    
    async def _calculate_new_weights(
        self,
        old_weights: SenseWeights,
        performance: Dict[str, float]
    ) -> SenseWeights:
        """
        Calculate new weights based on performance
        
        Args:
            old_weights: Current weights
            performance: Performance scores for each sense
            
        Returns:
            New SenseWeights
        """
        # Adjust weights based on performance
        # Better performing senses get slightly higher weight
        
        adjustments = {
            "pattern": (performance["pattern"] - 0.5) * self.learning_rate,
            "market": (performance["market"] - 0.5) * self.learning_rate,
            "behavior": (performance["behavior"] - 0.5) * self.learning_rate,
            "risk": (performance["risk"] - 0.5) * self.learning_rate
        }
        
        new_weights = SenseWeights(
            pattern=max(0.1, min(0.5, old_weights.pattern + adjustments["pattern"])),
            market=max(0.1, min(0.5, old_weights.market + adjustments["market"])),
            behavior=max(0.1, min(0.5, old_weights.behavior + adjustments["behavior"])),
            risk=max(0.1, min(0.5, old_weights.risk + adjustments["risk"]))
        )
        
        # Normalize to ensure they sum to 1
        new_weights.normalize()
        
        return new_weights
    
    async def _calculate_accuracy(self, feedback: List[FeedbackEntry]) -> Dict:
        """
        Calculate accuracy metrics from feedback
        
        Args:
            feedback: List of feedback entries
            
        Returns:
            Dict with accuracy metrics
        """
        if not feedback:
            return {"overall": 0.0, "by_recommendation": {}}
        
        # Overall accuracy
        accurate = len([f for f in feedback if f.feedback_type in [FeedbackType.ACCURATE, FeedbackType.HELPFUL]])
        overall = accurate / len(feedback)
        
        # By recommendation level
        by_recommendation = {}
        for level in ["strong_buy", "buy", "watch", "skip", "avoid"]:
            level_feedback = [f for f in feedback if f.recommendation_level == level]
            if level_feedback:
                level_accurate = len([f for f in level_feedback if f.feedback_type in [FeedbackType.ACCURATE, FeedbackType.HELPFUL]])
                by_recommendation[level] = level_accurate / len(level_feedback)
        
        return {
            "overall": overall,
            "by_recommendation": by_recommendation
        }
    
    async def _save_metrics(self, metrics: LearningMetrics):
        """
        Save learning metrics to Redis
        
        Args:
            metrics: LearningMetrics to save
        """
        await self.initialize()
        
        # Store in a sorted set by timestamp
        await self.redis.zadd(
            self.metrics_key,
            {json.dumps(metrics.to_dict()): metrics.timestamp.timestamp()}
        )
        
        # Keep only last 100 cycles
        count = await self.redis.zcard(self.metrics_key)
        if count > 100:
            await self.redis.zremrangebyrank(self.metrics_key, 0, count - 101)
    
    async def get_recent_metrics(self, limit: int = 10) -> List[LearningMetrics]:
        """
        Get recent learning metrics
        
        Args:
            limit: Number of recent cycles to return
            
        Returns:
            List of LearningMetrics (newest first)
        """
        await self.initialize()
        
        # Get last N entries
        entries = await self.redis.zrange(
            self.metrics_key,
            -limit,
            -1,
            withscores=False
        )
        
        metrics = []
        for entry in reversed(entries):
            data = json.loads(entry)
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            data['old_weights'] = SenseWeights.from_dict(data['old_weights'])
            data['new_weights'] = SenseWeights.from_dict(data['new_weights'])
            metrics.append(LearningMetrics(**data))
        
        return metrics
    
    async def get_learning_progress(self) -> Dict:
        """
        Get overall learning progress and trends
        
        Returns:
            Dict with progress metrics
        """
        recent_metrics = await self.get_recent_metrics(limit=20)
        
        if not recent_metrics:
            return {
                "total_cycles": 0,
                "avg_accuracy": 0.0,
                "accuracy_trend": [],
                "current_weights": (await self.get_current_weights()).to_dict()
            }
        
        # Calculate trends
        accuracy_trend = [m.overall_accuracy for m in reversed(recent_metrics)]
        
        # Calculate improvement
        if len(accuracy_trend) > 1:
            recent_improvement = accuracy_trend[-1] - accuracy_trend[0]
        else:
            recent_improvement = 0.0
        
        return {
            "total_cycles": len(recent_metrics),
            "avg_accuracy": statistics.mean(accuracy_trend),
            "accuracy_trend": accuracy_trend,
            "recent_improvement": recent_improvement,
            "current_weights": (await self.get_current_weights()).to_dict(),
            "latest_cycle": recent_metrics[0].to_dict() if recent_metrics else None
        }
    
    async def reset_weights(self):
        """Reset weights to default values"""
        default_weights = SenseWeights()
        await self.save_weights(default_weights)
    
    async def get_pending_feedback_count(self) -> int:
        """Get count of pending feedback ready for processing"""
        return await self.collector.get_pending_count()
