"""
Tests for Sprint 5: Intelligent Valuation Cache
"""

import pytest
import asyncio
import time
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from backend.services.valuation_cache import (
    ValuationCache,
    TTL_CONFIG,
    LAZY_REFRESH_GRACE_PERIOD
)


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = Mock()
    redis.get = Mock(return_value=None)
    redis.setex = Mock(return_value=True)
    redis.delete = Mock(return_value=True)
    redis.zrevrange = Mock(return_value=[])
    redis.zincrby = Mock(return_value=1)
    redis.zremrangebyrank = Mock(return_value=0)
    redis.info = Mock(return_value={})
    return redis


@pytest.fixture
def cache(mock_redis):
    """Valuation cache instance."""
    return ValuationCache(mock_redis)


class TestTieredTTL:
    """Test tiered TTL configuration."""
    
    def test_hot_items_ttl(self, cache):
        """Hot items should have 60s TTL."""
        ttl = cache._get_ttl("hot_items")
        assert ttl == 60
    
    def test_category_stats_ttl(self, cache):
        """Category stats should have 1 hour TTL."""
        ttl = cache._get_ttl("category_stats")
        assert ttl == 3600
    
    def test_seller_profiles_ttl(self, cache):
        """Seller profiles should have 1 day TTL."""
        ttl = cache._get_ttl("seller_profiles")
        assert ttl == 86400
    
    def test_market_trends_ttl(self, cache):
        """Market trends should have 7 days TTL."""
        ttl = cache._get_ttl("market_trends")
        assert ttl == 604800
    
    def test_cache_type_detection(self, cache):
        """Cache type should be detected from key prefix."""
        assert cache._get_cache_type("val:item:123") == "hot_items"
        assert cache._get_cache_type("stats:category:coins") == "category_stats"
        assert cache._get_cache_type("seller:profile:S123") == "seller_profiles"
        assert cache._get_cache_type("market:trend:ceramics") == "market_trends"
        assert cache._get_cache_type("unknown:key") == "hot_items"  # Default


class TestCacheOperations:
    """Test basic cache operations."""
    
    @pytest.mark.asyncio
    async def test_cache_miss(self, cache, mock_redis):
        """Cache miss should return None and increment metrics."""
        mock_redis.get.return_value = None
        
        result = await cache.get("val:item:123")
        
        assert result is None
        mock_redis.get.assert_called_once_with("val:item:123")
    
    @pytest.mark.asyncio
    async def test_cache_hit(self, cache, mock_redis):
        """Cache hit should return cached data."""
        cached_data = {
            "item_id": "123",
            "value": 1000,
            "_cached_at": time.time(),
            "_cache_type": "hot_items"
        }
        mock_redis.get.return_value = json.dumps(cached_data)
        
        result = await cache.get("val:item:123")
        
        assert result is not None
        assert result["item_id"] == "123"
        assert result["value"] == 1000
    
    @pytest.mark.asyncio
    async def test_cache_set(self, cache, mock_redis):
        """Set should store data with correct TTL."""
        data = {"item_id": "123", "value": 1000}
        
        success = await cache.set("val:item:123", data)
        
        assert success is True
        assert mock_redis.setex.called
        
        # Check TTL includes grace period
        call_args = mock_redis.setex.call_args
        key, ttl, value = call_args[0]
        assert ttl == 60 + LAZY_REFRESH_GRACE_PERIOD  # hot_items + grace
    
    def test_cache_delete(self, cache, mock_redis):
        """Delete should remove key from cache."""
        success = cache.delete("val:item:123")
        
        assert success is True
        mock_redis.delete.assert_called_once_with("val:item:123")


class TestLazyRefresh:
    """Test lazy refresh mechanism."""
    
    @pytest.mark.asyncio
    async def test_lazy_refresh_triggered_for_stale_data(self, cache, mock_redis):
        """Lazy refresh should trigger for stale but valid data."""
        # Data cached 90 seconds ago (stale but within grace period)
        cached_data = {
            "item_id": "123",
            "value": 1000,
            "_cached_at": time.time() - 90,
            "_cache_type": "hot_items"
        }
        mock_redis.get.return_value = json.dumps(cached_data)
        
        fetch_func = AsyncMock(return_value={"item_id": "123", "value": 1100})
        
        # Get with lazy refresh
        result = await cache.get("val:item:123", fetch_func=fetch_func, lazy_refresh=True)
        
        # Should return stale data immediately
        assert result["value"] == 1000
        
        # Allow async refresh to complete
        await asyncio.sleep(0.1)
        
        # Fetch function should have been called in background
        assert fetch_func.called
    
    @pytest.mark.asyncio
    async def test_no_lazy_refresh_for_fresh_data(self, cache, mock_redis):
        """Lazy refresh should NOT trigger for fresh data."""
        # Data cached 30 seconds ago (fresh)
        cached_data = {
            "item_id": "123",
            "value": 1000,
            "_cached_at": time.time() - 30,
            "_cache_type": "hot_items"
        }
        mock_redis.get.return_value = json.dumps(cached_data)
        
        fetch_func = AsyncMock(return_value={"item_id": "123", "value": 1100})
        
        result = await cache.get("val:item:123", fetch_func=fetch_func, lazy_refresh=True)
        
        assert result["value"] == 1000
        
        # Wait a bit
        await asyncio.sleep(0.1)
        
        # Fetch function should NOT have been called
        assert not fetch_func.called
    
    @pytest.mark.asyncio
    async def test_fetch_on_miss_with_function(self, cache, mock_redis):
        """Cache miss with fetch function should fetch and cache."""
        mock_redis.get.return_value = None
        fetch_func = AsyncMock(return_value={"item_id": "123", "value": 1000})
        
        result = await cache.get("val:item:123", fetch_func=fetch_func)
        
        assert result["item_id"] == "123"
        assert result["value"] == 1000
        fetch_func.assert_called_once()
        assert mock_redis.setex.called


class TestCacheMetadata:
    """Test cache metadata and age tracking."""
    
    @pytest.mark.asyncio
    async def test_cache_age_calculation(self, cache, mock_redis):
        """get_cache_age should return correct age in seconds."""
        cached_at = time.time() - 120  # 2 minutes ago
        cached_data = {
            "item_id": "123",
            "_cached_at": cached_at,
            "_cache_type": "hot_items"
        }
        mock_redis.get.return_value = json.dumps(cached_data)
        
        age = cache.get_cache_age("val:item:123")
        
        assert age is not None
        assert 119 < age < 121  # Allow small timing variance
    
    @pytest.mark.asyncio
    async def test_is_stale_detection(self, cache, mock_redis):
        """is_stale should correctly identify stale entries."""
        # Stale data (90 seconds > 60 second TTL)
        cached_data = {
            "_cached_at": time.time() - 90,
            "_cache_type": "hot_items"
        }
        mock_redis.get.return_value = json.dumps(cached_data)
        
        is_stale = cache.is_stale("val:item:123")
        
        assert is_stale is True
    
    @pytest.mark.asyncio
    async def test_is_not_stale_detection(self, cache, mock_redis):
        """is_stale should return False for fresh data."""
        # Fresh data (30 seconds < 60 second TTL)
        cached_data = {
            "_cached_at": time.time() - 30,
            "_cache_type": "hot_items"
        }
        mock_redis.get.return_value = json.dumps(cached_data)
        
        is_stale = cache.is_stale("val:item:123")
        
        assert is_stale is False


class TestHotItemsTracking:
    """Test hot items tracking functionality."""
    
    @pytest.mark.asyncio
    async def test_get_hot_items(self, cache, mock_redis):
        """get_hot_items should return top accessed items."""
        mock_redis.zrevrange.return_value = [
            b"item_123",
            b"item_456",
            b"item_789"
        ]
        
        hot_items = await cache.get_hot_items(limit=20)
        
        assert len(hot_items) == 3
        assert hot_items[0] == "item_123"
        mock_redis.zrevrange.assert_called_once_with("hot_items", 0, 19)
    
    def test_mark_hot_item(self, cache, mock_redis):
        """mark_hot_item should increment access count."""
        cache.mark_hot_item("item_123")
        
        mock_redis.zincrby.assert_called_once_with("hot_items", 1, "item_123")
        mock_redis.zremrangebyrank.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_prefetch_hot_items(self, cache, mock_redis):
        """prefetch_hot_items should prefetch valuations for hot items."""
        mock_redis.zrevrange.return_value = [b"item_123", b"item_456"]
        mock_redis.get.return_value = None  # Not cached
        
        fetch_func = AsyncMock(side_effect=[
            {"item_id": "123", "value": 1000},
            {"item_id": "456", "value": 2000}
        ])
        
        prefetched = await cache.prefetch_hot_items(fetch_func, limit=2)
        
        assert prefetched == 2
        assert fetch_func.call_count == 2


class TestCacheStats:
    """Test cache statistics."""
    
    def test_get_stats(self, cache, mock_redis):
        """get_stats should return Redis statistics."""
        mock_redis.info.side_effect = [
            {  # stats
                "keyspace_hits": 1000,
                "keyspace_misses": 200,
                "evicted_keys": 10,
                "expired_keys": 50
            },
            {  # keyspace
                "db0": {"keys": 150, "expires": 100}
            }
        ]
        
        stats = cache.get_stats()
        
        assert stats["keyspace_hits"] == 1000
        assert stats["keyspace_misses"] == 200
        assert stats["evicted_keys"] == 10
        assert stats["expired_keys"] == 50
        assert stats["total_keys"] == 150


class TestErrorHandling:
    """Test error handling."""
    
    @pytest.mark.asyncio
    async def test_get_handles_redis_error(self, cache, mock_redis):
        """get should handle Redis errors gracefully."""
        mock_redis.get.side_effect = Exception("Redis error")
        
        result = await cache.get("val:item:123")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_set_handles_redis_error(self, cache, mock_redis):
        """set should handle Redis errors gracefully."""
        mock_redis.setex.side_effect = Exception("Redis error")
        
        success = await cache.set("val:item:123", {"value": 1000})
        
        assert success is False
    
    def test_delete_handles_redis_error(self, cache, mock_redis):
        """delete should handle Redis errors gracefully."""
        mock_redis.delete.side_effect = Exception("Redis error")
        
        success = cache.delete("val:item:123")
        
        assert success is False


# Run with: pytest backend/tests/test_valuation_cache.py -v --cov=backend/services/valuation_cache
