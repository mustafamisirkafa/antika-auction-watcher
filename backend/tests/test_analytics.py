"""Tests for analytics services."""
import pytest
from backend.services.analytics.outcome_tracker import OutcomeTracker
from backend.services.analytics.learning_service import LearningService
from backend.services.analytics.metrics_collector import MetricsCollector


def test_outcome_tracker_initialization(session):
    """Test outcome tracker initialization."""
    tracker = OutcomeTracker(session)
    
    assert tracker.session is not None


def test_learning_service_initialization(session):
    """Test learning service initialization."""
    service = LearningService(session)
    
    assert service.session is not None
    assert service.min_sample_size == 10
    assert service.learning_rate == 0.1


def test_metrics_collector_initialization(session):
    """Test metrics collector initialization."""
    collector = MetricsCollector(session)
    
    assert collector.session is not None
    assert len(collector._request_timings) == 0


@pytest.mark.asyncio
async def test_outcome_tracker_category_performance(session):
    """Test category performance calculation."""
    tracker = OutcomeTracker(session)
    
    # Should return empty result for non-existent category
    performance = await tracker.get_category_performance('test_category')
    
    assert performance['category'] == 'test_category'
    assert performance['total_bids'] == 0
    assert performance['win_rate'] == 0.0


@pytest.mark.asyncio
async def test_learning_service_insufficient_data(session):
    """Test learning service with insufficient data."""
    service = LearningService(session)
    
    result = await service.train_category_model('test_category')
    
    assert result['status'] == 'insufficient_data'
    assert result['sample_size'] < service.min_sample_size


@pytest.mark.asyncio
async def test_metrics_collector_cache_operations(session):
    """Test metrics collector cache tracking."""
    collector = MetricsCollector(session)
    
    # Record cache hit
    await collector.record_cache_hit('test_key')
    
    assert collector._cache_stats['hits'] == 1
    assert collector._cache_stats['misses'] == 0
    
    # Record cache miss
    await collector.record_cache_miss('test_key')
    
    assert collector._cache_stats['misses'] == 1
