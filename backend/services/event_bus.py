"""
Event Bus Service for Real-time AutoBid (Phase 10).
Redis Pub/Sub for low-latency event distribution.
"""
import asyncio
import json
import logging
from typing import Dict, Callable, Any, Optional, List
from datetime import datetime
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class EventBus:
    """
    Redis-based event bus for real-time auction events.
    
    Channels:
    - auction.price_update:{auction_id}
    - advisor.ready:{auction_id}:{item_id}
    - bid.request
    - bid.result
    """
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        self.subscribers: Dict[str, List[Callable]] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
    
    async def connect(self):
        """Connect to Redis."""
        if self.redis_client is None:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            self.pubsub = self.redis_client.pubsub()
            logger.info(f"EventBus connected to Redis: {self.redis_url}")
    
    async def disconnect(self):
        """Disconnect from Redis."""
        self._running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        if self.pubsub:
            await self.pubsub.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("EventBus disconnected")
    
    async def publish(self, channel: str, payload: Dict[str, Any]):
        """
        Publish event to channel.
        
        Args:
            channel: Channel name
            payload: Event data (will be JSON serialized)
        """
        if not self.redis_client:
            await self.connect()
        
        # Add timestamp if not present
        if "ts" not in payload:
            payload["ts"] = datetime.utcnow().isoformat()
        
        message = json.dumps(payload)
        await self.redis_client.publish(channel, message)
        logger.debug(f"Published to {channel}: {message}")
    
    async def subscribe(self, pattern: str, handler: Callable[[str, Dict[str, Any]], Any]):
        """
        Subscribe to channel pattern.
        
        Args:
            pattern: Channel pattern (supports wildcards, e.g., "auction.price_update:*")
            handler: Async callback function(channel, payload)
        """
        if not self.redis_client:
            await self.connect()
        
        if pattern not in self.subscribers:
            self.subscribers[pattern] = []
            await self.pubsub.psubscribe(pattern)
            logger.info(f"Subscribed to pattern: {pattern}")
        
        self.subscribers[pattern].append(handler)
    
    async def start_listening(self):
        """Start listening for messages (run in background)."""
        if not self.pubsub:
            await self.connect()
        
        self._running = True
        
        async def listen():
            try:
                async for message in self.pubsub.listen():
                    if not self._running:
                        break
                    
                    if message["type"] == "pmessage":
                        pattern = message["pattern"]
                        channel = message["channel"]
                        data = message["data"]
                        
                        try:
                            payload = json.loads(data)
                            
                            # Call all handlers for this pattern
                            if pattern in self.subscribers:
                                for handler in self.subscribers[pattern]:
                                    try:
                                        if asyncio.iscoroutinefunction(handler):
                                            await handler(channel, payload)
                                        else:
                                            handler(channel, payload)
                                    except Exception as e:
                                        logger.error(f"Handler error for {channel}: {e}")
                        
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON from {channel}: {data}")
            
            except asyncio.CancelledError:
                logger.info("EventBus listener cancelled")
            except Exception as e:
                logger.error(f"EventBus listener error: {e}")
        
        task = asyncio.create_task(listen())
        self._tasks.append(task)
        logger.info("EventBus started listening")
    
    async def publish_price_update(self, auction_id: str, item_id: str, price: float):
        """Convenience method: publish price update."""
        await self.publish(
            f"auction.price_update:{auction_id}",
            {
                "auction_id": auction_id,
                "item_id": item_id,
                "price": price,
                "event_type": "price_update"
            }
        )
    
    async def publish_advisor_ready(self, auction_id: str, item_id: str, estimate: Dict):
        """Convenience method: publish profit advisor ready."""
        await self.publish(
            f"advisor.ready:{auction_id}:{item_id}",
            {
                "auction_id": auction_id,
                "item_id": item_id,
                "estimate": estimate,
                "event_type": "advisor_ready"
            }
        )
    
    async def publish_bid_request(self, request: Dict[str, Any]):
        """Convenience method: publish bid request."""
        await self.publish("bid.request", request)
    
    async def publish_bid_result(self, result: Dict[str, Any]):
        """Convenience method: publish bid result."""
        await self.publish("bid.result", result)
    
    async def publish_autobid_decision(self, decision: Dict[str, Any]):
        """Convenience method: publish autobid decision."""
        await self.publish("autobid.decision", decision)


# Global instance
_event_bus: Optional[EventBus] = None


def get_event_bus(redis_url: Optional[str] = None) -> EventBus:
    """Get or create global EventBus instance."""
    global _event_bus
    
    if _event_bus is None:
        if redis_url is None:
            from backend.core.config import settings
            redis_url = settings.REDIS_URL
        
        _event_bus = EventBus(redis_url)
    
    return _event_bus


async def init_event_bus(redis_url: str):
    """Initialize event bus on startup."""
    bus = get_event_bus(redis_url)
    await bus.connect()
    await bus.start_listening()
    return bus


async def shutdown_event_bus():
    """Shutdown event bus on app shutdown."""
    global _event_bus
    if _event_bus:
        await _event_bus.disconnect()
        _event_bus = None
