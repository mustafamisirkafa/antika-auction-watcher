"""
Bid Dispatcher Service for AutoBid (Phase 10).
Executes bids with retry logic and idempotency.
"""
import asyncio
import logging
import random
from typing import Dict, Any, Optional, Literal
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)


BidResult = Literal["accepted", "rejected", "timeout", "error"]


class BidDispatcher:
    """
    Dispatches bids to auction platform with retry logic.
    
    Features:
    - Idempotency (deduplicate same bid)
    - Retry with jitter backoff
    - Session management (keep login warm)
    - Anti-bot delays
    """
    
    def __init__(self, redis_client, event_bus):
        self.redis = redis_client
        self.event_bus = event_bus
        self.max_retries = 2
        self.base_delay_ms = 100
        self.max_delay_ms = 250
    
    async def dispatch_bid(
        self,
        team_id: int,
        auction_id: str,
        item_id: str,
        bid_amount: float,
        mode: Literal["shadow", "auto"]
    ) -> Dict[str, Any]:
        """
        Dispatch bid to auction platform.
        
        Args:
            team_id: Team ID
            auction_id: Auction ID
            item_id: Item/lot ID
            bid_amount: Bid amount
            mode: "shadow" (simulate only) or "auto" (real bid)
        
        Returns:
            Result dict with status, latency, etc.
        """
        start_time = datetime.utcnow()
        
        # Generate idempotency key
        idem_key = self._generate_idempotency_key(auction_id, item_id, bid_amount)
        
        # Check if already processed
        if await self._check_idempotency(idem_key):
            logger.info(f"Bid already processed (idempotent): {idem_key}")
            return {
                "result": "duplicate",
                "auction_id": auction_id,
                "item_id": item_id,
                "bid_amount": bid_amount,
                "latency_ms": 0
            }
        
        # Shadow mode: simulate only
        if mode == "shadow":
            result = await self._simulate_bid(auction_id, item_id, bid_amount)
        else:
            # Real mode: execute with retry
            result = await self._execute_bid_with_retry(
                team_id, auction_id, item_id, bid_amount
            )
        
        # Calculate latency
        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        result["latency_ms"] = round(latency_ms, 2)
        
        # Mark as processed (idempotency)
        await self._mark_processed(idem_key)
        
        # Publish bid result event
        await self.event_bus.publish_bid_result(result)
        
        logger.info(
            f"Bid dispatched: {auction_id}/{item_id} @ {bid_amount} ? {result['result']} "
            f"({latency_ms:.0f}ms)"
        )
        
        return result
    
    async def _execute_bid_with_retry(
        self, team_id: int, auction_id: str, item_id: str, bid_amount: float
    ) -> Dict[str, Any]:
        """Execute bid with retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                # Get or create session for team
                session = await self._get_session(team_id)
                
                # Execute bid
                result = await self._execute_bid(
                    session, auction_id, item_id, bid_amount
                )
                
                return {
                    "result": result,
                    "auction_id": auction_id,
                    "item_id": item_id,
                    "bid_amount": bid_amount,
                    "attempt": attempt + 1
                }
            
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"Bid attempt {attempt + 1} failed: {e}"
                )
                
                if attempt < self.max_retries:
                    # Jitter backoff
                    delay = random.uniform(self.base_delay_ms, self.max_delay_ms) / 1000.0
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        return {
            "result": "error",
            "auction_id": auction_id,
            "item_id": item_id,
            "bid_amount": bid_amount,
            "error": last_error,
            "attempts": self.max_retries + 1
        }
    
    async def _execute_bid(
        self, session: Any, auction_id: str, item_id: str, bid_amount: float
    ) -> BidResult:
        """
        Execute actual bid via auction platform API.
        
        This is a stub - in production, would use headless browser or API client.
        """
        # Simulate network delay + processing
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Simulate anti-bot delay
        await asyncio.sleep(random.uniform(0.05, 0.15))
        
        # Simulate success/failure
        success_rate = 0.85  # 85% success rate
        if random.random() < success_rate:
            return "accepted"
        else:
            # Simulate rejection reasons
            reasons = ["rejected", "timeout"]
            return random.choice(reasons)
    
    async def _simulate_bid(
        self, auction_id: str, item_id: str, bid_amount: float
    ) -> Dict[str, Any]:
        """Simulate bid (shadow mode)."""
        # Simulate realistic delay
        await asyncio.sleep(random.uniform(0.2, 0.4))
        
        return {
            "result": "simulated",
            "auction_id": auction_id,
            "item_id": item_id,
            "bid_amount": bid_amount,
            "mode": "shadow"
        }
    
    async def _get_session(self, team_id: int) -> Any:
        """
        Get or create warm session for team.
        
        In production:
        - Maintain pool of logged-in sessions per team
        - Rotate sessions to avoid detection
        - Refresh cookies periodically
        """
        # Stub: return mock session
        return {"team_id": team_id, "logged_in": True}
    
    def _generate_idempotency_key(
        self, auction_id: str, item_id: str, bid_amount: float
    ) -> str:
        """Generate idempotency key for bid."""
        data = f"{auction_id}:{item_id}:{bid_amount}"
        return f"idem:bid:{hashlib.md5(data.encode()).hexdigest()}"
    
    async def _check_idempotency(self, key: str) -> bool:
        """Check if bid was already processed."""
        exists = await self.redis.exists(key)
        return exists > 0
    
    async def _mark_processed(self, key: str):
        """Mark bid as processed (idempotency)."""
        await self.redis.setex(key, 300, "1")  # 5 minutes TTL
    
    async def acquire_lock(self, auction_id: str) -> bool:
        """
        Acquire concurrency lock for auction.
        
        Prevents multiple bids from same team racing.
        """
        lock_key = f"lock:autobid:{auction_id}"
        acquired = await self.redis.setnx(lock_key, "1")
        
        if acquired:
            await self.redis.expire(lock_key, 2)  # 2 second TTL
            return True
        
        return False
    
    async def release_lock(self, auction_id: str):
        """Release auction lock."""
        lock_key = f"lock:autobid:{auction_id}"
        await self.redis.delete(lock_key)
