"""Tests for performance middleware."""
import pytest
import time
import asyncio
from unittest.mock import Mock, AsyncMock
from backend.middleware.performance import (
    PerformanceMiddleware,
    DatabasePerformanceMonitor
)


@pytest.fixture
def perf_middleware():
    """Create performance middleware instance."""
    app = Mock()
    return PerformanceMiddleware(app)


@pytest.fixture
def db_monitor():
    """Create database performance monitor."""
    return DatabasePerformanceMonitor()


@pytest.mark.asyncio
async def test_performance_middleware_adds_header(perf_middleware):
    """Test that performance middleware adds timing header."""
    request = Mock()
    request.method = 'GET'
    request.url.path = '/api/v1/items'
    
    async def call_next(req):
        # Simulate some processing time
        await asyncio.sleep(0.01)
        response = Mock()
        response.headers = {}
        return response
    
    response = await perf_middleware.dispatch(request, call_next)
    
    assert 'X-Response-Time' in response.headers
    assert 'ms' in response.headers['X-Response-Time']


@pytest.mark.asyncio
async def test_performance_middleware_timing_accuracy(perf_middleware):
    """Test timing accuracy."""
    import asyncio
    
    request = Mock()
    request.method = 'GET'
    request.url.path = '/api/v1/test'
    
    async def call_next(req):
        await asyncio.sleep(0.05)  # 50ms delay
        response = Mock()
        response.headers = {}
        return response
    
    start = time.time()
    response = await perf_middleware.dispatch(request, call_next)
    end = time.time()
    
    # Extract timing from header
    timing_str = response.headers['X-Response-Time']
    timing_ms = float(timing_str.replace('ms', ''))
    
    # Should be approximately 50ms
    assert 40 <= timing_ms <= 100  # Allow some variance


def test_db_monitor_record_query(db_monitor):
    """Test recording database query."""
    db_monitor.record_query('SELECT', 45.0, 10)
    
    assert len(db_monitor.queries) == 1
    assert db_monitor.queries[0]['type'] == 'SELECT'
    assert db_monitor.queries[0]['duration_ms'] == 45.0
    assert db_monitor.queries[0]['rows'] == 10


def test_db_monitor_slow_query_detection(db_monitor):
    """Test slow query detection."""
    # Record fast query
    db_monitor.record_query('SELECT', 50.0, 5)
    
    # Record slow query
    db_monitor.record_query('SELECT', 150.0, 100)
    
    slow_queries = db_monitor.get_slow_queries()
    
    assert len(slow_queries) == 1
    assert slow_queries[0]['duration_ms'] == 150.0


def test_db_monitor_custom_threshold(db_monitor):
    """Test slow queries with custom threshold."""
    db_monitor.record_query('SELECT', 75.0, 10)
    db_monitor.record_query('INSERT', 125.0, 1)
    
    # With threshold of 80ms
    slow_queries = db_monitor.get_slow_queries(threshold_ms=80)
    
    assert len(slow_queries) == 1
    assert slow_queries[0]['type'] == 'INSERT'


def test_db_monitor_query_buffer_limit(db_monitor):
    """Test that query buffer is limited."""
    # Record 1500 queries
    for i in range(1500):
        db_monitor.record_query('SELECT', 50.0, 1)
    
    # Should keep only last 1000
    assert len(db_monitor.queries) == 1000


def test_db_monitor_get_query_stats(db_monitor):
    """Test getting query statistics."""
    # Record various queries
    db_monitor.record_query('SELECT', 50.0, 10)
    db_monitor.record_query('INSERT', 100.0, 1)
    db_monitor.record_query('UPDATE', 75.0, 5)
    db_monitor.record_query('SELECT', 200.0, 50)
    
    stats = db_monitor.get_query_stats()
    
    assert stats['total_queries'] == 4
    assert stats['min_duration_ms'] == 50.0
    assert stats['max_duration_ms'] == 200.0
    assert stats['avg_duration_ms'] == pytest.approx(106.25)
    assert 'p50_duration_ms' in stats
    assert 'p95_duration_ms' in stats


def test_db_monitor_get_query_stats_empty(db_monitor):
    """Test getting stats with no queries."""
    stats = db_monitor.get_query_stats()
    
    assert stats['total'] == 0


def test_db_monitor_percentile_calculation(db_monitor):
    """Test percentile calculations."""
    # Record 100 queries with known distribution
    for i in range(100):
        db_monitor.record_query('SELECT', float(i), 1)
    
    stats = db_monitor.get_query_stats()
    
    assert stats['p50_duration_ms'] == pytest.approx(50, rel=0.1)
    assert stats['p95_duration_ms'] == pytest.approx(95, rel=0.1)


def test_db_monitor_slow_queries_count(db_monitor):
    """Test slow queries count in stats."""
    # Record queries with some slow ones
    db_monitor.record_query('SELECT', 50.0, 10)
    db_monitor.record_query('SELECT', 150.0, 10)
    db_monitor.record_query('INSERT', 200.0, 1)
    
    stats = db_monitor.get_query_stats()
    
    # 2 queries over 100ms threshold
    assert stats['slow_queries'] == 2
