"""Redis Pub/Sub manager for real-time events."""
import json
import asyncio
from typing import Optional, Callable
import redis.asyncio as aioredis
from backend.core.config import settings


class RedisManager:
    """Redis Pub/Sub manager for broadcasting events."""

    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self.is_connected = False

    async def connect(self):
        """Connect to Redis."""
        self.redis_client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        self.is_connected = True

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        self.is_connected = False

    async def publish(self, channel: str, message: dict):
        """Publish a message to a channel."""
        if not self.is_connected or not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        message_json = json.dumps(message)
        await self.redis_client.publish(channel, message_json)

    async def subscribe(self, channel: str, callback: Callable):
        """Subscribe to a channel and handle messages."""
        if not self.is_connected or not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        self.pubsub = self.redis_client.pubsub()
        await self.pubsub.subscribe(channel)
        
        # Listen for messages
        async for message in self.pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await callback(data)

    async def publish_valuation_event(
        self,
        item_id: int,
        estimated_value: float,
        target_buy_price: float,
        confidence_score: float
    ):
        """Publish valuation event."""
        await self.publish("valuations", {
            "event": "valuation_complete",
            "item_id": item_id,
            "estimated_value": estimated_value,
            "target_buy_price": target_buy_price,
            "confidence_score": confidence_score,
            "timestamp": asyncio.get_event_loop().time()
        })

    async def publish_bid_event(
        self,
        item_id: int,
        bid_amount: float,
        decision: str,
        reason: str,
        success: bool
    ):
        """Publish bid event."""
        await self.publish("bids", {
            "event": "bid_placed",
            "item_id": item_id,
            "bid_amount": bid_amount,
            "decision": decision,
            "reason": reason,
            "success": success,
            "timestamp": asyncio.get_event_loop().time()
        })

    async def publish_item_update(
        self,
        item_id: int,
        current_price: float,
        status: str
    ):
        """Publish item update event."""
        await self.publish("items", {
            "event": "item_update",
            "item_id": item_id,
            "current_price": current_price,
            "status": status,
            "timestamp": asyncio.get_event_loop().time()
        })

    async def cache_set(self, key: str, value: str, expiration: int = 3600):
        """Set a value in cache with expiration."""
        if not self.is_connected or not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        await self.redis_client.setex(key, expiration, value)

    async def cache_get(self, key: str) -> Optional[str]:
        """Get a value from cache."""
        if not self.is_connected or not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        return await self.redis_client.get(key)

    async def cache_delete(self, key: str):
        """Delete a key from cache."""
        if not self.is_connected or not self.redis_client:
            raise RuntimeError("Redis client not connected")
        
        await self.redis_client.delete(key)
