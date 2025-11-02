"""
Delay Queue Service for AutoBid (Phase 10.5).
Handles "hold" decisions with scheduled retry.
"""
import asyncio
import logging
import time
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class DelayQueue:
    """
    Redis-based delay queue for AutoBid hold retries.
    
    Uses Redis Sorted Set (ZADD) with score = retry timestamp.
    """
    
    def __init__(self, redis_client, event_bus):
        self.redis = redis_client
        self.event_bus = event_bus
        self.queue_key = "dq:autobid"
        self._running = False
        self._poller_task: Optional[asyncio.Task] = None
    
    async def enqueue(
        self,
        auction_id: str,
        item_id: str,
        team_id: int,
        current_price: float,
        delay_ms: int,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Enqueue a hold decision for retry.
        
        Args:
            auction_id: Auction ID
            item_id: Item ID
            team_id: Team ID
            current_price: Current price
            delay_ms: Delay before retry (milliseconds)
            context: Additional context
        """
        # Calculate retry timestamp
        retry_at_ms = time.time() * 1000 + delay_ms
        
        # Create payload
        payload = {
            "auction_id": auction_id,
            "item_id": item_id,
            "team_id": team_id,
            "current_price": current_price,
            "context": context or {},
            "enqueued_at": time.time()
        }
        
        member = json.dumps(payload)
        
        # Add to sorted set (score = retry timestamp)
        await self.redis.zadd(self.queue_key, {member: retry_at_ms})
        
        logger.debug(
            f"Enqueued hold retry: {auction_id}/{item_id} "
            f"(delay={delay_ms}ms, retry_at={retry_at_ms})"
        )
    
    async def dequeue_due_items(self) -> List[Dict[str, Any]]:
        """
        Dequeue items that are due for retry.
        
        Returns:
            List of due items
        """
        now_ms = time.time() * 1000
        
        # Get items with score <= now
        items = await self.redis.zrangebyscore(
            self.queue_key,
            min=0,
            max=now_ms,
            start=0,
            num=10  # Process up to 10 at a time
        )
        
        if not items:
            return []
        
        due_items = []
        
        for item_str in items:
            try:
                payload = json.loads(item_str)
                due_items.append(payload)
                
                # Remove from queue
                await self.redis.zrem(self.queue_key, item_str)
            
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in delay queue: {item_str}")
                await self.redis.zrem(self.queue_key, item_str)
        
        if due_items:
            logger.info(f"Dequeued {len(due_items)} due items")
        
        return due_items
    
    async def start_poller(self, interval_ms: int = 200):
        """
        Start background poller that processes due items.
        
        Args:
            interval_ms: Polling interval in milliseconds
        """
        self._running = True
        
        async def poll():
            while self._running:
                try:
                    # Dequeue due items
                    due_items = await self.dequeue_due_items()
                    
                    # Re-trigger price updates for each item
                    for item in due_items:
                        await self._retry_item(item)
                    
                    # Sleep
                    await asyncio.sleep(interval_ms / 1000.0)
                
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Delay queue poller error: {e}")
                    await asyncio.sleep(1)  # Back off on error
        
        self._poller_task = asyncio.create_task(poll())
        logger.info(f"Delay queue poller started (interval={interval_ms}ms)")
    
    async def stop_poller(self):
        """Stop background poller."""
        self._running = False
        
        if self._poller_task:
            self._poller_task.cancel()
            try:
                await self._poller_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Delay queue poller stopped")
    
    async def _retry_item(self, item: Dict[str, Any]):
        """
        Retry a held item by re-triggering price update.
        
        Args:
            item: Item payload from queue
        """
        auction_id = item["auction_id"]
        item_id = item["item_id"]
        current_price = item["current_price"]
        
        logger.debug(f"Retrying held item: {auction_id}/{item_id} @ {current_price}")
        
        # Re-publish price update event
        await self.event_bus.publish_price_update(auction_id, item_id, current_price)
    
    async def get_queue_size(self) -> int:
        """Get current queue size."""
        return await self.redis.zcard(self.queue_key)
    
    async def get_due_count(self) -> int:
        """Get count of items due for retry."""
        now_ms = time.time() * 1000
        return await self.redis.zcount(self.queue_key, 0, now_ms)
    
    async def clear_queue(self):
        """Clear entire queue (for testing/maintenance)."""
        deleted = await self.redis.delete(self.queue_key)
        logger.info(f"Cleared delay queue ({deleted} items)")
        return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get delay queue statistics."""
        return {
            "running": self._running,
            "queue_key": self.queue_key
        }
