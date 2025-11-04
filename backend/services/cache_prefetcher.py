"""
Sprint 5: Predictive Cache Prefetch Engine

Features:
- Predicts which items will require valuation soon
- Preloads valuations into Redis ahead of bidding
- Async scheduler (runs every 30s)
- Multiple prediction strategies
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
import logging

from redis import Redis

logger = logging.getLogger(__name__)

# Prefetch configuration
PREFETCH_INTERVAL = 30  # seconds
PREFETCH_LIMIT = 20     # max items to prefetch per run
AUCTION_LOOKAHEAD = 300 # Look ahead 5 minutes for upcoming auctions


class CachePrefetcher:
    """
    Predictive cache prefetcher for valuation data.
    """
    
    def __init__(
        self,
        redis_client: Redis,
        valuation_cache: Any,  # ValuationCache instance
        valuation_fetch_func: callable
    ):
        self.redis = redis_client
        self.cache = valuation_cache
        self.fetch_func = valuation_fetch_func
        self._running = False
        self._prefetch_task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Start the prefetch scheduler."""
        if self._running:
            logger.warning("Prefetcher already running")
            return
        
        self._running = True
        self._prefetch_task = asyncio.create_task(self._prefetch_loop())
        logger.info("Cache prefetcher started")
    
    async def stop(self) -> None:
        """Stop the prefetch scheduler."""
        self._running = False
        
        if self._prefetch_task:
            self._prefetch_task.cancel()
            try:
                await self._prefetch_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Cache prefetcher stopped")
    
    async def _prefetch_loop(self) -> None:
        """Main prefetch loop (runs every PREFETCH_INTERVAL seconds)."""
        while self._running:
            try:
                await self.prefetch_round()
            except Exception as e:
                logger.error(f"Prefetch round error: {e}", exc_info=True)
            
            # Wait for next round
            await asyncio.sleep(PREFETCH_INTERVAL)
    
    async def prefetch_round(self) -> int:
        """
        Execute one prefetch round.
        
        Returns:
            Number of items successfully prefetched
        """
        start_time = time.time()
        
        # Step 1: Collect candidate items from multiple sources
        candidates = await self._collect_candidates()
        
        if not candidates:
            logger.debug("No candidates for prefetch")
            return 0
        
        # Step 2: Score and rank candidates
        ranked_candidates = self._rank_candidates(candidates)
        
        # Step 3: Select top N
        to_prefetch = ranked_candidates[:PREFETCH_LIMIT]
        
        # Step 4: Prefetch valuations
        prefetched = await self._prefetch_items(to_prefetch)
        
        elapsed = time.time() - start_time
        logger.info(
            f"Prefetch round complete: {prefetched}/{len(to_prefetch)} items "
            f"in {elapsed:.2f}s"
        )
        
        return prefetched
    
    async def _collect_candidates(self) -> List[Dict[str, Any]]:
        """
        Collect candidate items from multiple sources.
        
        Returns:
            List of dicts with item_id, source, score
        """
        candidates = []
        
        # Source 1: Hot items (from access patterns)
        hot_items = await self._get_hot_items()
        candidates.extend([
            {"item_id": item_id, "source": "hot", "score": 100 - i}
            for i, item_id in enumerate(hot_items)
        ])
        
        # Source 2: Trending items (from market data)
        trending_items = await self._get_trending_items()
        candidates.extend([
            {"item_id": item_id, "source": "trending", "score": 80 - i}
            for i, item_id in enumerate(trending_items)
        ])
        
        # Source 3: User watchlist items
        watchlist_items = await self._get_watchlist_items()
        candidates.extend([
            {"item_id": item_id, "source": "watchlist", "score": 90}
            for item_id in watchlist_items
        ])
        
        # Source 4: Upcoming auction items
        upcoming_items = await self._get_upcoming_auction_items()
        candidates.extend([
            {"item_id": item_id, "source": "upcoming", "score": 95}
            for item_id in upcoming_items
        ])
        
        logger.debug(f"Collected {len(candidates)} candidates from all sources")
        return candidates
    
    def _rank_candidates(self, candidates: List[Dict[str, Any]]) -> List[str]:
        """
        Rank candidates by priority score.
        
        Returns:
            List of item_ids sorted by priority (highest first)
        """
        # Group by item_id and aggregate scores
        item_scores: Dict[str, float] = {}
        
        for candidate in candidates:
            item_id = candidate["item_id"]
            score = candidate["score"]
            
            if item_id in item_scores:
                item_scores[item_id] += score * 0.5  # Bonus for multiple sources
            else:
                item_scores[item_id] = score
        
        # Sort by score descending
        ranked = sorted(
            item_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [item_id for item_id, score in ranked]
    
    async def _prefetch_items(self, item_ids: List[str]) -> int:
        """
        Prefetch valuations for items.
        
        Returns:
            Number successfully prefetched
        """
        tasks = []
        
        for item_id in item_ids:
            key = f"val:item:{item_id}"
            
            # Skip if already cached and fresh
            age = self.cache.get_cache_age(key)
            if age is not None and age < 60:  # Fresh within last minute
                continue
            
            # Create prefetch task
            async def prefetch_task(iid):
                try:
                    data = await self.fetch_func(iid)
                    if data:
                        await self.cache.set(f"val:item:{iid}", data)
                        logger.debug(f"Prefetched valuation for {iid}")
                        return True
                except Exception as e:
                    logger.error(f"Prefetch error for {iid}: {e}")
                return False
            
            tasks.append(prefetch_task(item_id))
        
        # Execute concurrently
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return sum(1 for r in results if r is True)
        
        return 0
    
    # ======== Candidate Source Implementations ========
    
    async def _get_hot_items(self) -> List[str]:
        """Get hot items from cache access patterns."""
        try:
            return await self.cache.get_hot_items(limit=10)
        except Exception as e:
            logger.error(f"Error getting hot items: {e}")
            return []
    
    async def _get_trending_items(self) -> List[str]:
        """Get trending items from market data."""
        try:
            # Redis sorted set: market:trending (score = trend score)
            trending = self.redis.zrevrange("market:trending", 0, 9)
            return [item.decode() for item in trending]
        except Exception as e:
            logger.error(f"Error getting trending items: {e}")
            return []
    
    async def _get_watchlist_items(self) -> List[str]:
        """Get items from user watchlists."""
        try:
            # Redis set: watchlist:active (items in active watchlists)
            watchlist = self.redis.smembers("watchlist:active")
            return [item.decode() for item in watchlist][:15]
        except Exception as e:
            logger.error(f"Error getting watchlist items: {e}")
            return []
    
    async def _get_upcoming_auction_items(self) -> List[str]:
        """Get items from auctions starting soon."""
        try:
            # Redis sorted set: auctions:upcoming (score = start_time)
            now = time.time()
            lookahead = now + AUCTION_LOOKAHEAD
            
            # Get auctions starting in next 5 minutes
            upcoming = self.redis.zrangebyscore(
                "auctions:upcoming",
                now,
                lookahead
            )
            
            # Extract item_ids (format: "auction_id:item_id")
            items = []
            for entry in upcoming:
                parts = entry.decode().split(":")
                if len(parts) == 2:
                    items.append(parts[1])
            
            return items[:10]
            
        except Exception as e:
            logger.error(f"Error getting upcoming auction items: {e}")
            return []
    
    # ======== Helper Methods for Integration ========
    
    @staticmethod
    def add_to_watchlist(redis_client: Redis, item_id: str) -> None:
        """Add item to active watchlist."""
        try:
            redis_client.sadd("watchlist:active", item_id)
        except Exception as e:
            logger.error(f"Error adding to watchlist: {e}")
    
    @staticmethod
    def remove_from_watchlist(redis_client: Redis, item_id: str) -> None:
        """Remove item from active watchlist."""
        try:
            redis_client.srem("watchlist:active", item_id)
        except Exception as e:
            logger.error(f"Error removing from watchlist: {e}")
    
    @staticmethod
    def schedule_auction(
        redis_client: Redis,
        auction_id: str,
        item_id: str,
        start_time: float
    ) -> None:
        """Schedule upcoming auction for prefetch."""
        try:
            entry = f"{auction_id}:{item_id}"
            redis_client.zadd("auctions:upcoming", {entry: start_time})
            
            # Clean up past auctions
            redis_client.zremrangebyscore(
                "auctions:upcoming",
                0,
                time.time() - 3600  # Remove auctions older than 1 hour
            )
        except Exception as e:
            logger.error(f"Error scheduling auction: {e}")
    
    @staticmethod
    def update_trending(
        redis_client: Redis,
        item_id: str,
        trend_score: float
    ) -> None:
        """Update trending score for item."""
        try:
            redis_client.zadd("market:trending", {item_id: trend_score})
            
            # Keep only top 100 trending items
            redis_client.zremrangebyrank("market:trending", 0, -101)
        except Exception as e:
            logger.error(f"Error updating trending: {e}")


# Global prefetcher instance
_prefetcher_instance: Optional[CachePrefetcher] = None


async def init_prefetcher(
    redis_client: Redis,
    valuation_cache: Any,
    valuation_fetch_func: callable,
    auto_start: bool = True
) -> CachePrefetcher:
    """Initialize and optionally start the global prefetcher."""
    global _prefetcher_instance
    
    _prefetcher_instance = CachePrefetcher(
        redis_client,
        valuation_cache,
        valuation_fetch_func
    )
    
    if auto_start:
        await _prefetcher_instance.start()
    
    return _prefetcher_instance


def get_prefetcher() -> CachePrefetcher:
    """Get global prefetcher instance."""
    if _prefetcher_instance is None:
        raise RuntimeError("Prefetcher not initialized. Call init_prefetcher() first.")
    return _prefetcher_instance
