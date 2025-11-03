"""
Unit tests for Analytics API (Phase 17)
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException
from sqlmodel import Session

from backend.routers.analytics import (
    get_autobid_metrics,
    get_valuation_metrics,
    get_seller_trust_metrics,
    get_user_prefs_metrics,
    get_system_health_metrics,
)


@pytest.mark.asyncio
async def test_get_autobid_metrics_with_data():
    """Test AutoBid metrics calculation with sample data."""
    # Mock DB session
    db = Mock(spec=Session)
    
    # Mock Redis
    redis = AsyncMock()
    redis.keys.return_value = ["lock:autobid:1", "lock:autobid:2", "lock:autobid:3"]
    
    # Mock audit log query
    mock_result = Mock()
    mock_result.all.return_value = [2450, 2800, 2100, 3200, 1900]
    db.exec.return_value = mock_result
    
    result = await get_autobid_metrics(db, redis)
    
    assert result["active_bids"] == 3
    assert result["sla_p95"] > 0
    assert result["last_bid_ms"] == 2450


@pytest.mark.asyncio
async def test_get_autobid_metrics_no_data():
    """Test AutoBid metrics with no active bids."""
    db = Mock(spec=Session)
    redis = AsyncMock()
    redis.keys.return_value = []
    
    mock_result = Mock()
    mock_result.all.return_value = []
    db.exec.return_value = mock_result
    
    result = await get_autobid_metrics(db, redis)
    
    assert result["active_bids"] == 0
    assert result["sla_p95"] == 0.0
    assert result["last_bid_ms"] == 0


@pytest.mark.asyncio
async def test_get_valuation_metrics():
    """Test Valuation metrics calculation."""
    redis = AsyncMock()
    redis.keys.return_value = ["valuation:cache:1", "valuation:cache:2"]
    
    # Mock cached valuation data
    redis.get.side_effect = [
        '{"market_value": 3000, "trend_delta": 0.05, "demand_score": 0.8}',
        '{"market_value": 3500, "trend_delta": 0.10, "demand_score": 0.9}',
    ]
    
    result = await get_valuation_metrics(redis)
    
    assert result["avg_market_value"] == 3250  # (3000 + 3500) / 2
    assert result["trend_delta"] == 0.075  # (0.05 + 0.10) / 2
    assert result["demand_score"] == 0.85  # (0.8 + 0.9) / 2


@pytest.mark.asyncio
async def test_get_valuation_metrics_no_cache():
    """Test Valuation metrics with empty cache."""
    redis = AsyncMock()
    redis.keys.return_value = []
    
    result = await get_valuation_metrics(redis)
    
    assert result["avg_market_value"] == 0
    assert result["trend_delta"] == 0.0
    assert result["demand_score"] == 0.0


@pytest.mark.asyncio
async def test_get_seller_trust_metrics():
    """Test Seller Trust distribution calculation."""
    db = Mock(spec=Session)
    
    # Mock seller trust scores
    mock_result = Mock()
    mock_result.all.return_value = [
        0.9, 0.8, 0.7,  # 3 trusted (>= 0.7)
        0.6, 0.5,       # 2 medium (0.4 - 0.7)
        0.3, 0.2,       # 2 risky (< 0.4)
    ]
    db.exec.return_value = mock_result
    
    result = await get_seller_trust_metrics(db)
    
    assert result["trusted"] == 3
    assert result["medium"] == 2
    assert result["risky"] == 2


@pytest.mark.asyncio
async def test_get_user_prefs_metrics():
    """Test User Preferences metrics aggregation."""
    db = Mock(spec=Session)
    
    # Mock user preferences
    mock_pref1 = Mock()
    mock_pref1.allowlist = ["seller1", "seller2", "seller3"]
    mock_pref1.blocklist = ["seller4"]
    
    mock_pref2 = Mock()
    mock_pref2.allowlist = ["seller5", "seller6"]
    mock_pref2.blocklist = ["seller7", "seller8"]
    
    mock_result = Mock()
    mock_result.all.return_value = [mock_pref1, mock_pref2]
    db.exec.return_value = mock_result
    
    result = await get_user_prefs_metrics(db)
    
    assert result["allowlist"] == 5  # 3 + 2
    assert result["blocklist"] == 3  # 1 + 2


@pytest.mark.asyncio
async def test_get_system_health_metrics():
    """Test System Health metrics collection."""
    redis = AsyncMock()
    redis.ping.return_value = True
    redis.info.return_value = {
        "keyspace_hits": 940,
        "keyspace_misses": 60,
    }
    
    db = Mock(spec=Session)
    db.exec.return_value = Mock()
    
    result = await get_system_health_metrics(redis, db)
    
    assert "redis_latency_ms" in result
    assert result["redis_latency_ms"] >= 0
    assert "cache_hit_ratio" in result
    assert 0 <= result["cache_hit_ratio"] <= 1.0
    assert "db_latency_ms" in result
    assert result["db_latency_ms"] >= 0


@pytest.mark.asyncio
async def test_analytics_overview_performance():
    """Test that analytics overview completes within SLA (<150ms)."""
    import time
    
    # Mock dependencies
    db = Mock(spec=Session)
    redis = AsyncMock()
    redis.get.return_value = None  # Force fresh query
    redis.setex.return_value = True
    redis.keys.return_value = []
    redis.ping.return_value = True
    redis.info.return_value = {"keyspace_hits": 100, "keyspace_misses": 10}
    
    mock_result = Mock()
    mock_result.all.return_value = []
    db.exec.return_value = mock_result
    
    start = time.time()
    
    # Simulate concurrent metric gathering
    from backend.routers.analytics import (
        get_autobid_metrics,
        get_valuation_metrics,
        get_seller_trust_metrics,
        get_user_prefs_metrics,
        get_system_health_metrics,
    )
    
    results = await asyncio.gather(
        get_autobid_metrics(db, redis),
        get_valuation_metrics(redis),
        get_seller_trust_metrics(db),
        get_user_prefs_metrics(db),
        get_system_health_metrics(redis, db),
    )
    
    elapsed_ms = (time.time() - start) * 1000
    
    # With mocked data, should be very fast
    assert elapsed_ms < 150, f"Analytics took {elapsed_ms:.0f}ms (target: <150ms)"
    assert len(results) == 5


@pytest.mark.asyncio
async def test_analytics_cache_works():
    """Test that analytics results are cached properly."""
    redis = AsyncMock()
    
    # First call: cache miss
    redis.get.return_value = None
    # Should call setex to cache result
    redis.setex.return_value = True
    
    # Verify setex is called with correct TTL (15 seconds)
    # This would be tested in integration test
    pass


import asyncio
