"""Tests for metrics collector."""
import pytest
from datetime import datetime, timedelta
from backend.services.analytics.metrics_collector import MetricsCollector
from backend.db.analytics_models import SystemMetrics


@pytest.fixture
def metrics_collector(session):
    """Create metrics collector instance."""
    return MetricsCollector(session)


@pytest.mark.asyncio
async def test_record_request_time(metrics_collector, session):
    """Test recording request time."""
    await metrics_collector.record_request_time(
        endpoint='/api/v1/items',
        duration_ms=150.5,
        status_code=200
    )
    
    # Check that metric was persisted
    from sqlmodel import select
    statement = select(SystemMetrics).where(
        SystemMetrics.metric_type == 'api_response_time'
    )
    metrics = session.exec(statement).all()
    
    assert len(metrics) >= 1
    assert metrics[0].value == 150.5


@pytest.mark.asyncio
async def test_record_external_api_call(metrics_collector, session):
    """Test recording external API call."""
    await metrics_collector.record_external_api_call(
        api_name='ebay',
        success=True,
        duration_ms=350.0
    )
    
    assert metrics_collector._api_call_counts['ebay'] == 1
    
    # Check persistence
    from sqlmodel import select
    statement = select(SystemMetrics).where(
        SystemMetrics.metric_type == 'external_api'
    )
    metrics = session.exec(statement).all()
    
    assert len(metrics) >= 1


@pytest.mark.asyncio
async def test_record_database_query(metrics_collector, session):
    """Test recording database query."""
    await metrics_collector.record_database_query(
        query_type='SELECT',
        duration_ms=45.0,
        rows_affected=10
    )
    
    from sqlmodel import select
    statement = select(SystemMetrics).where(
        SystemMetrics.metric_type == 'database_query'
    )
    metrics = session.exec(statement).all()
    
    assert len(metrics) >= 1
    assert metrics[0].metadata.get('rows') == 10


@pytest.mark.asyncio
async def test_record_cache_hit(metrics_collector):
    """Test recording cache hit."""
    await metrics_collector.record_cache_hit('test_key')
    
    assert metrics_collector._cache_stats['hits'] == 1
    assert metrics_collector._cache_stats['misses'] == 0


@pytest.mark.asyncio
async def test_record_cache_miss(metrics_collector):
    """Test recording cache miss."""
    await metrics_collector.record_cache_miss('test_key')
    
    assert metrics_collector._cache_stats['misses'] == 1


@pytest.mark.asyncio
async def test_cache_stats_persistence(metrics_collector, session):
    """Test cache stats persistence after 100 operations."""
    # Record 100 cache operations to trigger persistence
    for i in range(100):
        await metrics_collector.record_cache_hit('test_key')
    
    # Should have persisted
    from sqlmodel import select
    statement = select(SystemMetrics).where(
        SystemMetrics.metric_type == 'cache_performance'
    )
    metrics = session.exec(statement).all()
    
    assert len(metrics) >= 1


@pytest.mark.asyncio
async def test_get_response_time_stats_no_data(metrics_collector):
    """Test getting response time stats with no data."""
    stats = await metrics_collector.get_response_time_stats()
    
    assert stats['status'] == 'no_data'


@pytest.mark.asyncio
async def test_get_response_time_stats_with_data(metrics_collector, session):
    """Test getting response time stats."""
    # Record some requests
    await metrics_collector.record_request_time('/api/v1/items', 100.0, 200)
    await metrics_collector.record_request_time('/api/v1/items', 150.0, 200)
    await metrics_collector.record_request_time('/api/v1/items', 200.0, 200)
    
    stats = await metrics_collector.get_response_time_stats()
    
    assert 'sample_size' in stats
    assert 'min' in stats
    assert 'max' in stats
    assert 'mean' in stats
    assert 'p50' in stats
    assert 'p95' in stats
    assert stats['min'] == 100.0
    assert stats['max'] == 200.0


@pytest.mark.asyncio
async def test_get_response_time_stats_specific_endpoint(
    metrics_collector,
    session
):
    """Test getting stats for specific endpoint."""
    await metrics_collector.record_request_time('/api/v1/items', 100.0, 200)
    await metrics_collector.record_request_time('/api/v1/bids', 200.0, 200)
    
    stats = await metrics_collector.get_response_time_stats(endpoint='/api/v1/items')
    
    assert stats['endpoint'] == '/api/v1/items'
    assert stats['sample_size'] >= 1


@pytest.mark.asyncio
async def test_get_external_api_usage(metrics_collector, session):
    """Test getting external API usage."""
    # Record API calls
    await metrics_collector.record_external_api_call('ebay', True, 300.0)
    await metrics_collector.record_external_api_call('ebay', True, 350.0)
    await metrics_collector.record_external_api_call('ebay', False, 100.0)
    await metrics_collector.record_external_api_call('etsy', True, 250.0)
    
    usage = await metrics_collector.get_external_api_usage(hours=24)
    
    assert 'api_usage' in usage
    assert 'ebay' in usage['api_usage']
    assert usage['api_usage']['ebay']['total_calls'] == 3
    assert usage['api_usage']['ebay']['successful_calls'] == 2
    assert usage['api_usage']['ebay']['failed_calls'] == 1


@pytest.mark.asyncio
async def test_get_slow_queries(metrics_collector, session):
    """Test getting slow queries."""
    # Record some queries
    await metrics_collector.record_database_query('SELECT', 50.0, 10)
    await metrics_collector.record_database_query('INSERT', 150.0, 1)
    await metrics_collector.record_database_query('UPDATE', 200.0, 5)
    
    slow_queries = await metrics_collector.get_slow_queries(threshold_ms=100)
    
    assert len(slow_queries) >= 2  # INSERT and UPDATE


@pytest.mark.asyncio
async def test_get_cache_performance_no_data(metrics_collector):
    """Test cache performance with no persisted data."""
    # Use in-memory stats
    await metrics_collector.record_cache_hit('key1')
    await metrics_collector.record_cache_hit('key2')
    await metrics_collector.record_cache_miss('key3')
    
    performance = await metrics_collector.get_cache_performance()
    
    assert performance['current_hit_rate'] == pytest.approx(2/3, rel=0.01)
    assert performance['hits'] == 2
    assert performance['misses'] == 1


@pytest.mark.asyncio
async def test_get_dashboard_metrics(metrics_collector):
    """Test comprehensive dashboard metrics."""
    dashboard = await metrics_collector.get_dashboard_metrics()
    
    assert 'response_times' in dashboard
    assert 'external_api_usage' in dashboard
    assert 'cache_performance' in dashboard
    assert 'slow_queries_count' in dashboard
    assert 'timestamp' in dashboard


@pytest.mark.asyncio
async def test_cleanup_old_metrics(metrics_collector, session):
    """Test cleaning up old metrics."""
    # Create old metrics
    old_metric = SystemMetrics(
        metric_type='test',
        metric_name='old_metric',
        value=100.0,
        unit='ms',
        recorded_at=datetime.utcnow() - timedelta(days=40)
    )
    session.add(old_metric)
    
    # Create recent metric
    recent_metric = SystemMetrics(
        metric_type='test',
        metric_name='recent_metric',
        value=100.0,
        unit='ms'
    )
    session.add(recent_metric)
    session.commit()
    
    # Cleanup metrics older than 30 days
    deleted_count = await metrics_collector.cleanup_old_metrics(days=30)
    
    assert deleted_count >= 1


@pytest.mark.asyncio
async def test_percentile_calculations(metrics_collector, session):
    """Test percentile calculations in response time stats."""
    # Record many requests to test percentiles
    for i in range(100):
        await metrics_collector.record_request_time(
            '/api/v1/test',
            float(i),
            200
        )
    
    stats = await metrics_collector.get_response_time_stats()
    
    assert stats['p50'] == pytest.approx(50, rel=0.1)
    assert stats['p95'] == pytest.approx(95, rel=0.1)
    assert stats['p99'] == pytest.approx(99, rel=0.1)
