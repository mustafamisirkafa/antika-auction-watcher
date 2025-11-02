"""Comprehensive tests for rate limiter middleware."""
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request, Response
from backend.middleware.rate_limiter import RateLimiter
from backend.realtime.redis_manager import RedisManager


@pytest.fixture
def mock_redis_manager():
    """Create a mock Redis manager."""
    manager = Mock(spec=RedisManager)
    manager.connect = AsyncMock()
    manager.disconnect = AsyncMock()
    manager.cache_get = AsyncMock()
    manager.cache_set = AsyncMock()
    return manager


@pytest.fixture
def rate_limiter(mock_redis_manager):
    """Create rate limiter instance."""
    app = Mock()
    limiter = RateLimiter(app, redis_manager=mock_redis_manager)
    return limiter


@pytest.mark.asyncio
async def test_rate_limiter_initialization(rate_limiter):
    """Test rate limiter initialization."""
    assert rate_limiter.default_limit == 60
    assert rate_limiter.enabled is True
    assert '/api/v1/valuations/estimate' in rate_limiter.endpoint_limits


@pytest.mark.asyncio
async def test_rate_limiter_disabled(mock_redis_manager):
    """Test rate limiter when disabled."""
    app = Mock()
    
    with patch('backend.middleware.rate_limiter.settings') as mock_settings:
        mock_settings.rate_limit_enabled = False
        limiter = RateLimiter(app, redis_manager=mock_redis_manager)
        
        # Create mock request
        request = Mock(spec=Request)
        request.url.path = '/api/v1/items'
        
        # Create mock response
        async def call_next(req):
            return Response(content='OK', status_code=200)
        
        response = await limiter.dispatch(request, call_next)
        
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limiter_health_check_bypass(rate_limiter):
    """Test that health checks bypass rate limiting."""
    request = Mock(spec=Request)
    request.url.path = '/health'
    
    async def call_next(req):
        return Response(content='OK', status_code=200)
    
    response = await rate_limiter.dispatch(request, call_next)
    
    assert response.status_code == 200
    # Should not have called Redis
    rate_limiter.redis_manager.cache_get.assert_not_called()


@pytest.mark.asyncio
async def test_get_user_identifier_with_token(rate_limiter):
    """Test user identification with JWT token."""
    request = Mock(spec=Request)
    request.headers.get.return_value = 'Bearer test_token_123'
    
    user_id = await rate_limiter._get_user_identifier(request)
    
    assert user_id == 'user:Bearer test_token_123'


@pytest.mark.asyncio
async def test_get_user_identifier_with_ip(rate_limiter):
    """Test user identification with IP address."""
    request = Mock(spec=Request)
    request.headers.get.return_value = ''
    request.client.host = '192.168.1.1'
    
    user_id = await rate_limiter._get_user_identifier(request)
    
    assert user_id == 'ip:192.168.1.1'


def test_get_rate_limit_exact_match(rate_limiter):
    """Test getting rate limit for exact endpoint match."""
    limit = rate_limiter._get_rate_limit('/api/v1/valuations/estimate')
    
    assert limit == 30


def test_get_rate_limit_default(rate_limiter):
    """Test getting default rate limit."""
    limit = rate_limiter._get_rate_limit('/api/v1/unknown/endpoint')
    
    assert limit == 60


@pytest.mark.asyncio
async def test_check_rate_limit_first_request(rate_limiter):
    """Test rate limit check for first request."""
    rate_limiter.redis_manager.cache_get.return_value = None
    
    allowed, remaining, reset_time = await rate_limiter._check_rate_limit(
        'user:test',
        '/api/v1/items',
        60
    )
    
    assert allowed is True
    assert remaining == 59
    assert reset_time > time.time()


@pytest.mark.asyncio
async def test_check_rate_limit_within_limit(rate_limiter):
    """Test rate limit check when within limit."""
    import json
    
    # Simulate 5 requests in the window
    now = time.time()
    timestamps = [now - i for i in range(5)]
    rate_limiter.redis_manager.cache_get.return_value = json.dumps({
        'timestamps': timestamps
    })
    
    allowed, remaining, reset_time = await rate_limiter._check_rate_limit(
        'user:test',
        '/api/v1/items',
        60
    )
    
    assert allowed is True
    assert remaining >= 0


@pytest.mark.asyncio
async def test_check_rate_limit_exceeded(rate_limiter):
    """Test rate limit check when limit exceeded."""
    import json
    
    # Simulate 60 requests in the window
    now = time.time()
    timestamps = [now - i * 0.5 for i in range(60)]
    rate_limiter.redis_manager.cache_get.return_value = json.dumps({
        'timestamps': timestamps
    })
    
    allowed, remaining, reset_time = await rate_limiter._check_rate_limit(
        'user:test',
        '/api/v1/items',
        60
    )
    
    assert allowed is False
    assert remaining == 0


@pytest.mark.asyncio
async def test_check_rate_limit_window_sliding(rate_limiter):
    """Test that old requests outside window are removed."""
    import json
    
    now = time.time()
    # Mix of old (outside window) and recent requests
    timestamps = [
        now - 120,  # 2 minutes ago (outside 60s window)
        now - 90,   # 1.5 minutes ago (outside window)
        now - 30,   # 30 seconds ago (inside window)
        now - 10    # 10 seconds ago (inside window)
    ]
    rate_limiter.redis_manager.cache_get.return_value = json.dumps({
        'timestamps': timestamps
    })
    
    allowed, remaining, reset_time = await rate_limiter._check_rate_limit(
        'user:test',
        '/api/v1/items',
        60,
        window_seconds=60
    )
    
    # Should only count the 2 recent requests
    assert allowed is True


@pytest.mark.asyncio
async def test_check_rate_limit_redis_failure(rate_limiter):
    """Test rate limit behavior when Redis fails."""
    rate_limiter.redis_manager.cache_get.side_effect = Exception('Redis error')
    
    # Should fail open (allow request)
    allowed, remaining, reset_time = await rate_limiter._check_rate_limit(
        'user:test',
        '/api/v1/items',
        60
    )
    
    assert allowed is True
    assert remaining == 60


@pytest.mark.asyncio
async def test_dispatch_adds_rate_limit_headers(rate_limiter):
    """Test that rate limit headers are added to response."""
    rate_limiter.redis_manager.cache_get.return_value = None
    
    request = Mock(spec=Request)
    request.url.path = '/api/v1/items'
    request.headers.get.return_value = ''
    request.client.host = '127.0.0.1'
    
    async def call_next(req):
        return Response(content='OK', status_code=200)
    
    response = await rate_limiter.dispatch(request, call_next)
    
    assert 'X-RateLimit-Limit' in response.headers
    assert 'X-RateLimit-Remaining' in response.headers
    assert 'X-RateLimit-Reset' in response.headers


@pytest.mark.asyncio
async def test_dispatch_returns_429_when_limited(rate_limiter):
    """Test that 429 is returned when rate limited."""
    import json
    
    # Simulate rate limit exceeded
    now = time.time()
    timestamps = [now - i * 0.5 for i in range(100)]
    rate_limiter.redis_manager.cache_get.return_value = json.dumps({
        'timestamps': timestamps
    })
    
    request = Mock(spec=Request)
    request.url.path = '/api/v1/items'
    request.headers.get.return_value = ''
    request.client.host = '127.0.0.1'
    
    async def call_next(req):
        return Response(content='OK', status_code=200)
    
    response = await rate_limiter.dispatch(request, call_next)
    
    assert response.status_code == 429
    assert 'Retry-After' in response.headers


@pytest.mark.asyncio
async def test_endpoint_specific_limits(rate_limiter):
    """Test endpoint-specific rate limits."""
    # Valuation endpoint has limit of 30
    limit = rate_limiter._get_rate_limit('/api/v1/valuations/estimate')
    assert limit == 30
    
    # Bid placement has limit of 20
    limit = rate_limiter._get_rate_limit('/api/v1/bids/place')
    assert limit == 20
    
    # Bid decision has limit of 40
    limit = rate_limiter._get_rate_limit('/api/v1/bids/decision')
    assert limit == 40


@pytest.mark.asyncio
async def test_rate_limit_per_user_isolation(rate_limiter):
    """Test that rate limits are per user."""
    rate_limiter.redis_manager.cache_get.return_value = None
    
    # User 1 makes request
    allowed1, _, _ = await rate_limiter._check_rate_limit(
        'user:user1',
        '/api/v1/items',
        60
    )
    
    # User 2 should have separate limit
    allowed2, remaining2, _ = await rate_limiter._check_rate_limit(
        'user:user2',
        '/api/v1/items',
        60
    )
    
    assert allowed1 is True
    assert allowed2 is True
    assert remaining2 == 59  # Fresh limit for user 2


@pytest.mark.asyncio
async def test_rate_limit_records_timestamp(rate_limiter):
    """Test that timestamps are recorded correctly."""
    rate_limiter.redis_manager.cache_get.return_value = None
    
    before = time.time()
    
    await rate_limiter._check_rate_limit(
        'user:test',
        '/api/v1/items',
        60
    )
    
    after = time.time()
    
    # Verify cache_set was called
    rate_limiter.redis_manager.cache_set.assert_called_once()
    
    # Get the timestamp from the call
    call_args = rate_limiter.redis_manager.cache_set.call_args
    import json
    data = json.loads(call_args[0][1])
    
    timestamp = data['timestamps'][0]
    assert before <= timestamp <= after
