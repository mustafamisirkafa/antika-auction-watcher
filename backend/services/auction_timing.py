"""
Auction Timing Intelligence Service (Phase 10.5).
Tracks price patterns, detects sniping windows, manages escalation cooldowns.
"""
import logging
import time
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class TimingIntel:
    """
    Provides timing intelligence for anti-sniping and bid escalation.
    
    Features:
    - Price pattern tracking (Redis Streams)
    - Sniping window detection
    - Microburst detection
    - Escalation cooldown management
    """
    
    def __init__(self, redis_client, config):
        self.redis = redis_client
        self.config = config
        self.max_history = 20  # Keep last N price updates
    
    async def on_price(
        self, auction_id: str, item_id: str, price: float, ts: Optional[float] = None
    ):
        """
        Record price update for timing analysis.
        
        Args:
            auction_id: Auction ID
            item_id: Item/lot ID
            price: New price
            ts: Timestamp (epoch seconds, defaults to now)
        """
        if ts is None:
            ts = time.time()
        
        key = f"tim:{auction_id}:{item_id}"
        
        # Add to Redis Stream (maintains order, trimmed to max length)
        await self.redis.xadd(
            key,
            {"p": str(price), "t": str(ts)},
            maxlen=self.max_history
        )
        
        logger.debug(f"Price tracked: {auction_id}/{item_id} @ {price} (ts={ts})")
    
    async def sniping_window(
        self,
        auction_id: str,
        item_id: str,
        now_ts: Optional[float] = None,
        scheduled_end_ts: Optional[float] = None
    ) -> bool:
        """
        Determine if we're in the sniping window.
        
        Strategy:
        1. If scheduled_end_ts known ? time-based check
        2. Else ? heuristic based on price update cadence
        
        Args:
            auction_id: Auction ID
            item_id: Item ID
            now_ts: Current timestamp (defaults to now)
            scheduled_end_ts: Scheduled auction end time (if known)
        
        Returns:
            True if in sniping window
        """
        if now_ts is None:
            now_ts = time.time()
        
        # Strategy 1: Time-based (if end time known)
        if scheduled_end_ts:
            time_remaining = scheduled_end_ts - now_ts
            is_sniping = time_remaining <= self.config.SNIPING_WINDOW_SEC
            
            logger.debug(
                f"Sniping window (time-based): {is_sniping} "
                f"(remaining={time_remaining:.1f}s)"
            )
            
            return is_sniping
        
        # Strategy 2: Heuristic (burst activity detection)
        is_sniping = await self._recent_burst_activity(
            auction_id, item_id, threshold_sec=2.0, min_count=3
        )
        
        logger.debug(f"Sniping window (heuristic): {is_sniping}")
        
        return is_sniping
    
    async def _recent_burst_activity(
        self, auction_id: str, item_id: str, threshold_sec: float = 2.0, min_count: int = 3
    ) -> bool:
        """
        Detect burst activity (rapid price updates).
        
        Heuristic: If last N updates are all within threshold_sec apart ? burst
        
        Args:
            auction_id: Auction ID
            item_id: Item ID
            threshold_sec: Max seconds between updates
            min_count: Min number of updates to check
        
        Returns:
            True if burst detected
        """
        key = f"tim:{auction_id}:{item_id}"
        
        # Get recent entries
        entries = await self.redis.xrevrange(key, count=min_count + 1)
        
        if len(entries) < min_count:
            return False  # Not enough data
        
        # Extract timestamps
        timestamps = []
        for entry_id, data in entries:
            ts = float(data.get(b"t", 0))
            timestamps.append(ts)
        
        timestamps.sort()
        
        # Check inter-arrival times
        for i in range(len(timestamps) - 1):
            delta = timestamps[i + 1] - timestamps[i]
            if delta > threshold_sec:
                return False  # Gap too large
        
        # All deltas within threshold ? burst
        return True
    
    async def recent_microburst(
        self, auction_id: str, item_id: str, threshold_sec: float = 1.0
    ) -> bool:
        """
        Check if last two price updates were within threshold (microburst).
        
        Args:
            auction_id: Auction ID
            item_id: Item ID
            threshold_sec: Max seconds between updates
        
        Returns:
            True if microburst detected
        """
        key = f"tim:{auction_id}:{item_id}"
        
        # Get last 2 entries
        entries = await self.redis.xrevrange(key, count=2)
        
        if len(entries) < 2:
            return False
        
        # Extract timestamps
        ts1 = float(entries[0][1].get(b"t", 0))
        ts2 = float(entries[1][1].get(b"t", 0))
        
        delta = abs(ts1 - ts2)
        
        is_microburst = delta <= threshold_sec
        
        logger.debug(f"Microburst check: {is_microburst} (delta={delta:.2f}s)")
        
        return is_microburst
    
    async def get_price_history(
        self, auction_id: str, item_id: str, count: int = 10
    ) -> List[Tuple[float, float]]:
        """
        Get recent price history.
        
        Args:
            auction_id: Auction ID
            item_id: Item ID
            count: Number of entries
        
        Returns:
            List of (timestamp, price) tuples
        """
        key = f"tim:{auction_id}:{item_id}"
        
        entries = await self.redis.xrevrange(key, count=count)
        
        history = []
        for entry_id, data in entries:
            ts = float(data.get(b"t", 0))
            price = float(data.get(b"p", 0))
            history.append((ts, price))
        
        return history
    
    async def next_allowed_escalation_at(
        self, auction_id: str, item_id: str
    ) -> float:
        """
        Get timestamp when next escalation is allowed.
        
        Args:
            auction_id: Auction ID
            item_id: Item ID
        
        Returns:
            Epoch timestamp (ms) when next escalation allowed
        """
        key = f"escal_cool:{auction_id}:{item_id}"
        value = await self.redis.get(key)
        
        if value is None:
            return 0.0  # No cooldown active
        
        return float(value)
    
    async def record_escalation(self, auction_id: str, item_id: str):
        """
        Record an escalation and set cooldown.
        
        Args:
            auction_id: Auction ID
            item_id: Item ID
        """
        # Increment escalation counter
        count_key = f"escal_cnt:{auction_id}:{item_id}"
        count = await self.redis.incr(count_key)
        await self.redis.expire(count_key, 300)  # 5 min TTL
        
        # Set cooldown
        cool_key = f"escal_cool:{auction_id}:{item_id}"
        next_allowed = time.time() * 1000 + self.config.ESCALATION_COOLDOWN_MS
        await self.redis.setex(
            cool_key,
            int(self.config.ESCALATION_COOLDOWN_MS / 1000) + 1,
            str(next_allowed)
        )
        
        logger.info(
            f"Escalation recorded: {auction_id}/{item_id} "
            f"(count={count}, cooldown={self.config.ESCALATION_COOLDOWN_MS}ms)"
        )
        
        return count
    
    async def get_escalation_count(self, auction_id: str, item_id: str) -> int:
        """
        Get current escalation count for item.
        
        Args:
            auction_id: Auction ID
            item_id: Item ID
        
        Returns:
            Escalation count
        """
        key = f"escal_cnt:{auction_id}:{item_id}"
        count = await self.redis.get(key)
        
        return int(count) if count else 0
    
    async def reset_escalation_count(self, auction_id: str, item_id: str):
        """Reset escalation count (e.g., after auction ends)."""
        key = f"escal_cnt:{auction_id}:{item_id}"
        await self.redis.delete(key)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get timing intel statistics."""
        # TODO: Aggregate stats from Redis
        return {
            "enabled": self.config.ANTI_SNIPING_ENABLED,
            "sniping_window_sec": self.config.SNIPING_WINDOW_SEC,
            "microbuffer_sec": self.config.MICROBUFFER_SEC,
            "max_escalations": self.config.MAX_ESCALATIONS_PER_ITEM
        }
