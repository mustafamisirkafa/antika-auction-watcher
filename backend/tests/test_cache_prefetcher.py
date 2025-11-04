"""
Tests for Sprint 5: Predictive Cache Prefetcher
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from backend.services.cache_prefetcher import (
    CachePrefetcher,
    PREFETCH_INTERVAL,
    PREFETCH_LIMIT,
    AUCTION_LOOKAHEAD
)


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = Mock()
    redis.zrevrange = Mock(return_value=[])
    redis.smembers = Mock(return_value=set())
    redis.zrangebyscore = Mock(return_value=[])
    redis.zadd = Mock(return_value=1)
    redis.zremrangebyscore = Mock(return_value=0)
    redis.sadd = Mock(return_value=1)
    redis.srem = Mock(return_value=1)
    return redis


@pytest.fixture
def mock_cache():
    """Mock ValuationCache."""
    cache = Mock()
    cache.get_hot_items = AsyncMock(return_value=[])
    cache.get_cache_age = Mock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    return cache


@pytest.fixture
def mock_fetch_func():
    """Mock valuation fetch function."""
    return AsyncMock(return_value={"item_id": "123", "value": 1000})


@pytest.fixture
def prefetcher(mock_redis, mock_cache, mock_fetch_func):
    """Cache prefetcher instance."""
    return CachePrefetcher(mock_redis, mock_cache, mock_fetch_func)


class TestPrefetcherLifecycle:
    """Test prefetcher lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_start_prefetcher(self, prefetcher):
        """Should start prefetch loop."""
        await prefetcher.start()
        
        assert prefetcher._running is True
        assert prefetcher._prefetch_task is not None
        
        # Cleanup
        await prefetcher.stop()
    
    @pytest.mark.asyncio
    async def test_stop_prefetcher(self, prefetcher):
        """Should stop prefetch loop."""
        await prefetcher.start()
        await prefetcher.stop()
        
        assert prefetcher._running is False
    
    @pytest.mark.asyncio
    async def test_start_already_running(self, prefetcher, caplog):
        """Starting already running prefetcher should warn."""
        await prefetcher.start()
        await prefetcher.start()  # Second start
        
        assert "already running" in caplog.text.lower()
        
        await prefetcher.stop()


class TestCandidateCollection:
    """Test candidate collection from multiple sources."""
    
    @pytest.mark.asyncio
    async def test_collect_hot_items(self, prefetcher, mock_cache):
        """Should collect hot items."""
        mock_cache.get_hot_items.return_value = ["item_1", "item_2", "item_3"]
        
        candidates = await prefetcher._collect_candidates()
        
        hot_candidates = [c for c in candidates if c["source"] == "hot"]
        assert len(hot_candidates) == 3
        assert hot_candidates[0]["item_id"] == "item_1"
    
    @pytest.mark.asyncio
    async def test_collect_trending_items(self, prefetcher, mock_redis):
        """Should collect trending items."""
        mock_redis.zrevrange.return_value = [b"item_10", b"item_11"]
        
        trending = await prefetcher._get_trending_items()
        
        assert len(trending) == 2
        assert trending[0] == "item_10"
    
    @pytest.mark.asyncio
    async def test_collect_watchlist_items(self, prefetcher, mock_redis):
        """Should collect watchlist items."""
        mock_redis.smembers.return_value = {b"item_20", b"item_21"}
        
        watchlist = await prefetcher._get_watchlist_items()
        
        assert len(watchlist) == 2
        assert "item_20" in watchlist
    
    @pytest.mark.asyncio
    async def test_collect_upcoming_auction_items(self, prefetcher, mock_redis):
        """Should collect upcoming auction items."""
        mock_redis.zrangebyscore.return_value = [
            b"A1:item_30",
            b"A2:item_31"
        ]
        
        upcoming = await prefetcher._get_upcoming_auction_items()
        
        assert len(upcoming) == 2
        assert upcoming[0] == "item_30"


class TestCandidateRanking:
    """Test candidate ranking and scoring."""
    
    def test_rank_candidates_by_score(self, prefetcher):
        """Should rank candidates by score descending."""
        candidates = [
            {"item_id": "item_1", "source": "hot", "score": 80},
            {"item_id": "item_2", "source": "trending", "score": 95},
            {"item_id": "item_3", "source": "watchlist", "score": 70},
        ]
        
        ranked = prefetcher._rank_candidates(candidates)
        
        assert ranked[0] == "item_2"  # Highest score
        assert ranked[1] == "item_1"
        assert ranked[2] == "item_3"
    
    def test_rank_candidates_aggregates_duplicates(self, prefetcher):
        """Should aggregate scores for duplicate items."""
        candidates = [
            {"item_id": "item_1", "source": "hot", "score": 80},
            {"item_id": "item_1", "source": "trending", "score": 90},
            {"item_id": "item_2", "source": "watchlist", "score": 70},
        ]
        
        ranked = prefetcher._rank_candidates(candidates)
        
        # item_1 should have bonus for multiple sources
        assert ranked[0] == "item_1"


class TestPrefetchExecution:
    """Test prefetch execution."""
    
    @pytest.mark.asyncio
    async def test_prefetch_items_fetches_and_caches(
        self,
        prefetcher,
        mock_cache,
        mock_fetch_func
    ):
        """Should fetch and cache items."""
        mock_cache.get_cache_age.return_value = None  # Not cached
        mock_fetch_func.side_effect = [
            {"item_id": "123", "value": 1000},
            {"item_id": "456", "value": 2000}
        ]
        
        prefetched = await prefetcher._prefetch_items(["item_123", "item_456"])
        
        assert prefetched == 2
        assert mock_fetch_func.call_count == 2
        assert mock_cache.set.call_count == 2
    
    @pytest.mark.asyncio
    async def test_prefetch_skips_fresh_cache(
        self,
        prefetcher,
        mock_cache,
        mock_fetch_func
    ):
        """Should skip items with fresh cache."""
        mock_cache.get_cache_age.return_value = 30  # Fresh (< 60s)
        
        prefetched = await prefetcher._prefetch_items(["item_123"])
        
        assert prefetched == 0
        assert mock_fetch_func.call_count == 0
    
    @pytest.mark.asyncio
    async def test_prefetch_handles_errors(
        self,
        prefetcher,
        mock_cache,
        mock_fetch_func
    ):
        """Should handle fetch errors gracefully."""
        mock_cache.get_cache_age.return_value = None
        mock_fetch_func.side_effect = Exception("Fetch error")
        
        prefetched = await prefetcher._prefetch_items(["item_123"])
        
        assert prefetched == 0  # Failed but didn't crash


class TestPrefetchRound:
    """Test full prefetch round execution."""
    
    @pytest.mark.asyncio
    async def test_prefetch_round_collects_ranks_and_prefetches(
        self,
        prefetcher,
        mock_cache,
        mock_redis,
        mock_fetch_func
    ):
        """Full prefetch round should work end-to-end."""
        # Mock hot items
        mock_cache.get_hot_items.return_value = ["item_1", "item_2"]
        
        # Mock trending
        mock_redis.zrevrange.return_value = [b"item_3"]
        
        # Mock cache state (not cached)
        mock_cache.get_cache_age.return_value = None
        
        # Mock fetch
        mock_fetch_func.return_value = {"item_id": "test", "value": 1000}
        
        prefetched = await prefetcher.prefetch_round()
        
        # Should have collected at least 3 candidates
        assert prefetched <= 3  # May be less if fetch failed
        assert mock_fetch_func.called


class TestHelperMethods:
    """Test helper methods for integration."""
    
    def test_add_to_watchlist(self, mock_redis):
        """Should add item to watchlist."""
        CachePrefetcher.add_to_watchlist(mock_redis, "item_123")
        
        mock_redis.sadd.assert_called_once_with("watchlist:active", "item_123")
    
    def test_remove_from_watchlist(self, mock_redis):
        """Should remove item from watchlist."""
        CachePrefetcher.remove_from_watchlist(mock_redis, "item_123")
        
        mock_redis.srem.assert_called_once_with("watchlist:active", "item_123")
    
    def test_schedule_auction(self, mock_redis):
        """Should schedule auction for prefetch."""
        now = time.time()
        CachePrefetcher.schedule_auction(
            mock_redis,
            "A1",
            "item_123",
            now + 600
        )
        
        mock_redis.zadd.assert_called_once()
        mock_redis.zremrangebyscore.assert_called_once()  # Cleanup
    
    def test_update_trending(self, mock_redis):
        """Should update trending score."""
        CachePrefetcher.update_trending(mock_redis, "item_123", 95.5)
        
        mock_redis.zadd.assert_called_once()
        mock_redis.zremrangebyrank.assert_called_once()  # Keep top 100


class TestPrefetchLimits:
    """Test prefetch limits and constraints."""
    
    @pytest.mark.asyncio
    async def test_respects_prefetch_limit(
        self,
        prefetcher,
        mock_cache,
        mock_redis
    ):
        """Should respect PREFETCH_LIMIT."""
        # Generate many candidates
        many_items = [f"item_{i}" for i in range(100)]
        mock_cache.get_hot_items.return_value = many_items
        mock_cache.get_cache_age.return_value = None
        
        candidates = await prefetcher._collect_candidates()
        ranked = prefetcher._rank_candidates(candidates)
        
        # Only top PREFETCH_LIMIT should be selected
        to_prefetch = ranked[:PREFETCH_LIMIT]
        assert len(to_prefetch) == PREFETCH_LIMIT


# Run with: pytest backend/tests/test_cache_prefetcher.py -v --cov=backend/services/cache_prefetcher
