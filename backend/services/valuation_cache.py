"""
Cache Orchestrator (Phase 11).
Redis-based caching for fused market valuations.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ValuationCache:
    """
    Cache orchestrator for market valuations.
    
    Features:
    - Redis storage with 10-minute TTL
    - Real-time refresh with backoff logic
    - Health status & fallback mechanism
    - Automatic cache invalidation
    """
    
    def __init__(self, redis_client, market_feed, valuation_fusion, event_bus):
        self.redis = redis_client
        self.market_feed = market_feed
        self.valuation_fusion = valuation_fusion
        self.event_bus = event_bus
        
        # Configuration
        self.cache_ttl = 600  # 10 minutes
        self.refresh_backoff_base = 2  # seconds
        self.refresh_backoff_max = 60  # seconds
        self.max_refresh_attempts = 3
        
        # Health tracking
        self.refresh_failures: Dict[str, int] = {}
    
    async def get_cached_valuation(
        self, item_id: str, category: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached valuation or fetch fresh if expired.
        
        Args:
            item_id: Item identifier
            category: Item category
        
        Returns:
            Fused metrics or None if unavailable
        """
        cache_key = f"valuation:cache:{item_id}"
        
        # Try to get from cache
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            try:
                metrics = json.loads(cached_data)
                logger.debug(f"Cache hit for {item_id}")
                return metrics
            except json.JSONDecodeError:
                logger.error(f"Invalid cached data for {item_id}")
        
        # Cache miss - fetch fresh data
        logger.info(f"Cache miss for {item_id} - fetching fresh data")
        return await self.refresh_valuation(item_id, category)
    
    async def refresh_valuation(
        self, item_id: str, category: str, force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Refresh valuation from market feed + fusion.
        
        Args:
            item_id: Item identifier
            category: Item category
            force: Force refresh even if recently failed
        
        Returns:
            Fresh fused metrics or None if failed
        """
        # Check backoff (unless forced)
        if not force and not await self._check_refresh_allowed(item_id):
            logger.warning(f"Refresh rate-limited for {item_id}")
            return None
        
        try:
            # Fetch external market data
            external_feeds = await self.market_feed.fetch_market_data(
                item_title=item_id,  # TODO: Map item_id to actual title
                category=category
            )
            
            # Get internal estimate (if available)
            # TODO: Query ProfitEstimate from database
            internal_estimate = None
            
            # Fuse data
            fused_metrics = await self.valuation_fusion.fuse_market_data(
                item_id=item_id,
                category=category,
                internal_estimate=internal_estimate,
                external_feeds=external_feeds
            )
            
            # Cache the result
            await self._store_in_cache(item_id, fused_metrics)
            
            # Reset failure counter
            self.refresh_failures[item_id] = 0
            
            # Emit cache update event
            await self.event_bus.publish("valuation.cache_updated", {
                "item_id": item_id,
                "metrics": fused_metrics
            })
            
            logger.info(f"Refreshed valuation for {item_id}")
            
            return fused_metrics
        
        except Exception as e:
            logger.error(f"Error refreshing valuation for {item_id}: {e}")
            
            # Track failure
            self.refresh_failures[item_id] = self.refresh_failures.get(item_id, 0) + 1
            
            # Set backoff
            await self._set_refresh_backoff(item_id)
            
            # Try fallback
            return await self._get_fallback_valuation(item_id)
    
    async def _store_in_cache(self, item_id: str, metrics: Dict[str, Any]):
        """Store metrics in Redis cache."""
        cache_key = f"valuation:cache:{item_id}"
        
        # Serialize to JSON
        data = json.dumps(metrics)
        
        # Store with TTL
        await self.redis.setex(cache_key, self.cache_ttl, data)
        
        logger.debug(f"Cached valuation for {item_id} (TTL={self.cache_ttl}s)")
    
    async def _check_refresh_allowed(self, item_id: str) -> bool:
        """Check if refresh is allowed (not in backoff)."""
        backoff_key = f"valuation:backoff:{item_id}"
        backoff_until = await self.redis.get(backoff_key)
        
        if backoff_until:
            try:
                backoff_ts = float(backoff_until)
                now_ts = datetime.utcnow().timestamp()
                
                if now_ts < backoff_ts:
                    return False
            except (ValueError, TypeError):
                pass
        
        return True
    
    async def _set_refresh_backoff(self, item_id: str):
        """Set refresh backoff based on failure count."""
        failure_count = self.refresh_failures.get(item_id, 0)
        
        # Exponential backoff: base * 2^(failures - 1)
        backoff_seconds = min(
            self.refresh_backoff_base * (2 ** (failure_count - 1)),
            self.refresh_backoff_max
        )
        
        # Calculate backoff expiry
        backoff_until = datetime.utcnow().timestamp() + backoff_seconds
        
        # Store in Redis
        backoff_key = f"valuation:backoff:{item_id}"
        await self.redis.setex(
            backoff_key,
            int(backoff_seconds) + 1,
            str(backoff_until)
        )
        
        logger.warning(
            f"Set refresh backoff for {item_id}: {backoff_seconds}s "
            f"(failures={failure_count})"
        )
    
    async def _get_fallback_valuation(
        self, item_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get fallback valuation when refresh fails.
        
        Strategy:
        1. Try stale cache (even if expired)
        2. Return default metrics
        """
        # Try stale cache
        cache_key = f"valuation:cache:{item_id}"
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            try:
                metrics = json.loads(cached_data)
                logger.warning(f"Using stale cache for {item_id}")
                return metrics
            except json.JSONDecodeError:
                pass
        
        # Return default metrics
        logger.error(f"No fallback available for {item_id}")
        return {
            "market_value": 0.0,
            "demand_score": 0.5,
            "trend_delta": 0.0,
            "confidence": 0.0,
            "sources": [],
            "data_points": 0,
            "fallback": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def invalidate_cache(self, item_id: str):
        """Invalidate cached valuation for item."""
        cache_key = f"valuation:cache:{item_id}"
        await self.redis.delete(cache_key)
        logger.info(f"Invalidated cache for {item_id}")
    
    async def get_cache_health(self) -> Dict[str, Any]:
        """Get cache health statistics."""
        # Count cached items
        pattern = "valuation:cache:*"
        cursor = 0
        cached_count = 0
        
        while True:
            cursor, keys = await self.redis.scan(
                cursor, match=pattern, count=100
            )
            cached_count += len(keys)
            
            if cursor == 0:
                break
        
        # Count items in backoff
        backoff_pattern = "valuation:backoff:*"
        cursor = 0
        backoff_count = 0
        
        while True:
            cursor, keys = await self.redis.scan(
                cursor, match=backoff_pattern, count=100
            )
            backoff_count += len(keys)
            
            if cursor == 0:
                break
        
        # Calculate failure rate
        total_items = len(self.refresh_failures)
        failed_items = sum(
            1 for count in self.refresh_failures.values()
            if count >= self.max_refresh_attempts
        )
        
        failure_rate = failed_items / total_items if total_items > 0 else 0.0
        
        return {
            "cached_items": cached_count,
            "backoff_items": backoff_count,
            "total_tracked": total_items,
            "failed_items": failed_items,
            "failure_rate": round(failure_rate, 3),
            "cache_ttl": self.cache_ttl,
            "status": "healthy" if failure_rate < 0.1 else "degraded"
        }
    
    async def cleanup_stale_entries(self):
        """Clean up stale failure tracking."""
        # Remove items with no recent activity
        items_to_remove = []
        
        for item_id in list(self.refresh_failures.keys()):
            # Check if cache exists
            cache_key = f"valuation:cache:{item_id}"
            exists = await self.redis.exists(cache_key)
            
            if not exists:
                items_to_remove.append(item_id)
        
        for item_id in items_to_remove:
            del self.refresh_failures[item_id]
        
        logger.info(f"Cleaned up {len(items_to_remove)} stale failure entries")
