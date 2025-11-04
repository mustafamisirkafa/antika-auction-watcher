"""
Sprint 5: Intelligent Valuation Cache Orchestrator

Features:
- Tiered TTL based on data volatility
- Lazy refresh mechanism (serve stale + async refresh)
- Cache prefetching for hot items
- Prometheus metrics integration
"""

import asyncio
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json
import logging

from redis import Redis
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# Tiered TTL configuration (in seconds)
TTL_CONFIG = {
    "hot_items": 60,           # 1 min for active auction items
    "category_stats": 3600,     # 1 hour for category aggregations
    "seller_profiles": 86400,   # 1 day for seller behavioral data
    "market_trends": 604800,    # 7 days for market trend data
}

# Lazy refresh grace period (serve stale data within this window)
LAZY_REFRESH_GRACE_PERIOD = 300  # 5 minutes

# Prometheus metrics
cache_hits = Counter('cache_hits_total', 'Total cache hits', ['cache_type'])
cache_misses = Counter('cache_misses_total', 'Total cache misses', ['cache_type'])
cache_refreshes = Counter('cache_refreshes_total', 'Total lazy refreshes', ['cache_type'])
cache_refresh_latency = Histogram(
    'cache_refresh_latency_seconds',
    'Cache refresh latency',
    ['cache_type'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)
cache_size = Gauge('cache_size_bytes', 'Approximate cache size', ['cache_type'])


class ValuationCache:
    """
    Intelligent cache orchestrator with tiered TTL and lazy refresh.
    """
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self._refresh_tasks: Dict[str, asyncio.Task] = {}
        
    def _get_cache_type(self, key: str) -> str:
        """Determine cache type from key prefix."""
        if key.startswith("val:item:"):
            return "hot_items"
        elif key.startswith("stats:category:"):
            return "category_stats"
        elif key.startswith("seller:profile:"):
            return "seller_profiles"
        elif key.startswith("market:trend:"):
            return "market_trends"
        else:
            return "hot_items"  # Default
    
    def _get_ttl(self, cache_type: str) -> int:
        """Get TTL for cache type."""
        return TTL_CONFIG.get(cache_type, 60)
    
    async def get(
        self,
        key: str,
        fetch_func: Optional[callable] = None,
        lazy_refresh: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get value from cache with optional lazy refresh.
        
        Args:
            key: Cache key
            fetch_func: Async function to fetch fresh data on miss
            lazy_refresh: Enable lazy refresh (serve stale + async update)
        
        Returns:
            Cached value or None
        """
        cache_type = self._get_cache_type(key)
        
        # Try to get from cache
        try:
            cached_data = self.redis.get(key)
            
            if cached_data:
                data = json.loads(cached_data)
                cache_hits.labels(cache_type=cache_type).inc()
                
                # Check if data is stale but within grace period
                if lazy_refresh and fetch_func:
                    cached_at = data.get("_cached_at", 0)
                    age = time.time() - cached_at
                    ttl = self._get_ttl(cache_type)
                    
                    # If data is stale but within grace period, trigger refresh
                    if age > ttl and age < (ttl + LAZY_REFRESH_GRACE_PERIOD):
                        logger.info(f"Lazy refresh triggered for key: {key} (age: {age:.1f}s)")
                        self._trigger_lazy_refresh(key, fetch_func, cache_type)
                
                return data
            
            else:
                cache_misses.labels(cache_type=cache_type).inc()
                
                # Fetch fresh data if function provided
                if fetch_func:
                    data = await self._fetch_and_cache(key, fetch_func, cache_type)
                    return data
                
                return None
                
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            cache_misses.labels(cache_type=cache_type).inc()
            return None
    
    def _trigger_lazy_refresh(
        self,
        key: str,
        fetch_func: callable,
        cache_type: str
    ) -> None:
        """
        Trigger async background refresh without blocking.
        """
        # Avoid duplicate refresh tasks
        if key in self._refresh_tasks and not self._refresh_tasks[key].done():
            return
        
        async def refresh_task():
            try:
                start = time.time()
                await self._fetch_and_cache(key, fetch_func, cache_type)
                latency = time.time() - start
                
                cache_refreshes.labels(cache_type=cache_type).inc()
                cache_refresh_latency.labels(cache_type=cache_type).observe(latency)
                
                logger.info(f"Lazy refresh completed for {key} in {latency:.2f}s")
            except Exception as e:
                logger.error(f"Lazy refresh failed for {key}: {e}")
            finally:
                # Clean up task reference
                if key in self._refresh_tasks:
                    del self._refresh_tasks[key]
        
        # Create background task
        task = asyncio.create_task(refresh_task())
        self._refresh_tasks[key] = task
    
    async def _fetch_and_cache(
        self,
        key: str,
        fetch_func: callable,
        cache_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch fresh data and store in cache.
        """
        try:
            # Fetch fresh data
            data = await fetch_func()
            
            if data is None:
                return None
            
            # Add metadata
            data["_cached_at"] = time.time()
            data["_cache_type"] = cache_type
            
            # Store with appropriate TTL
            ttl = self._get_ttl(cache_type)
            total_ttl = ttl + LAZY_REFRESH_GRACE_PERIOD  # Extended TTL for lazy refresh
            
            self.redis.setex(
                key,
                total_ttl,
                json.dumps(data)
            )
            
            logger.debug(f"Cached {key} with TTL {total_ttl}s")
            
            return data
            
        except Exception as e:
            logger.error(f"Fetch and cache error for {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl_override: Optional[int] = None
    ) -> bool:
        """
        Set value in cache with appropriate TTL.
        """
        cache_type = self._get_cache_type(key)
        
        try:
            # Add metadata
            value["_cached_at"] = time.time()
            value["_cache_type"] = cache_type
            
            # Determine TTL
            if ttl_override:
                ttl = ttl_override
            else:
                ttl = self._get_ttl(cache_type) + LAZY_REFRESH_GRACE_PERIOD
            
            # Store
            self.redis.setex(key, ttl, json.dumps(value))
            
            return True
            
        except Exception as e:
            logger.error(f"Cache set error for {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for {key}: {e}")
            return False
    
    def get_cache_age(self, key: str) -> Optional[float]:
        """
        Get age of cached data in seconds.
        Returns None if not cached.
        """
        try:
            cached_data = self.redis.get(key)
            if cached_data:
                data = json.loads(cached_data)
                cached_at = data.get("_cached_at", 0)
                return time.time() - cached_at
            return None
        except:
            return None
    
    def is_stale(self, key: str) -> bool:
        """
        Check if cache entry is stale (beyond normal TTL but within grace period).
        """
        age = self.get_cache_age(key)
        if age is None:
            return True
        
        cache_type = self._get_cache_type(key)
        ttl = self._get_ttl(cache_type)
        
        return age > ttl
    
    async def get_hot_items(self, limit: int = 20) -> List[str]:
        """
        Get list of hot item IDs from sorted set (by access count).
        """
        try:
            # Sorted set: hot_items (score = access count)
            hot_items = self.redis.zrevrange("hot_items", 0, limit - 1)
            return [item.decode() for item in hot_items]
        except Exception as e:
            logger.error(f"Error fetching hot items: {e}")
            return []
    
    def mark_hot_item(self, item_id: str) -> None:
        """
        Increment access count for item (marks as hot).
        """
        try:
            self.redis.zincrby("hot_items", 1, item_id)
            # Keep only top 100 hot items
            self.redis.zremrangebyrank("hot_items", 0, -101)
        except Exception as e:
            logger.error(f"Error marking hot item {item_id}: {e}")
    
    async def prefetch_hot_items(
        self,
        fetch_func: callable,
        limit: int = 20
    ) -> int:
        """
        Prefetch valuations for hot items.
        
        Args:
            fetch_func: Async function(item_id) to fetch valuation
            limit: Number of hot items to prefetch
        
        Returns:
            Number of items successfully prefetched
        """
        hot_items = await self.get_hot_items(limit)
        prefetched = 0
        
        tasks = []
        for item_id in hot_items:
            key = f"val:item:{item_id}"
            
            # Skip if already cached and fresh
            age = self.get_cache_age(key)
            if age is not None and age < 30:  # Skip if cached in last 30s
                continue
            
            # Create prefetch task
            async def prefetch_task(iid):
                try:
                    data = await fetch_func(iid)
                    if data:
                        await self.set(f"val:item:{iid}", data)
                        return True
                except Exception as e:
                    logger.error(f"Prefetch failed for {iid}: {e}")
                return False
            
            tasks.append(prefetch_task(item_id))
        
        # Execute prefetch tasks concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            prefetched = sum(1 for r in results if r is True)
        
        logger.info(f"Prefetched {prefetched}/{len(hot_items)} hot items")
        return prefetched
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        """
        try:
            info = self.redis.info("stats")
            keyspace = self.redis.info("keyspace")
            
            return {
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "evicted_keys": info.get("evicted_keys", 0),
                "expired_keys": info.get("expired_keys", 0),
                "total_keys": sum(
                    db_info.get("keys", 0)
                    for db_info in keyspace.values()
                    if isinstance(db_info, dict)
                ),
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}


# Global cache instance (initialized by app)
_cache_instance: Optional[ValuationCache] = None


def init_cache(redis_client: Redis) -> ValuationCache:
    """Initialize global cache instance."""
    global _cache_instance
    _cache_instance = ValuationCache(redis_client)
    return _cache_instance


def get_cache() -> ValuationCache:
    """Get global cache instance."""
    if _cache_instance is None:
        raise RuntimeError("Cache not initialized. Call init_cache() first.")
    return _cache_instance
