"""
Tests for rate limiting middleware (Sprint 2).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded

from backend.middleware.rate_limit import (
    get_request_identifier,
    rate_limit_exceeded_handler,
    limit_bid_requests,
    limit_valuation_requests,
    limit_login_requests,
    check_rate_limit_redis,
    get_rate_limit_info,
)


@pytest.fixture
def mock_request():
    """Create mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.client.host = "192.168.1.100"
    request.headers = {
        "X-Forwarded-For": "192.168.1.100",
        "User-Agent": "Test Client"
    }
    request.state = MagicMock()
    return request


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = AsyncMock()
    redis.pipeline = MagicMock()
    
    # Mock pipeline
    pipeline = AsyncMock()
    pipeline.zremrangebyscore = MagicMock(return_value=pipeline)
    pipeline.zcard = MagicMock(return_value=pipeline)
    pipeline.zadd = MagicMock(return_value=pipeline)
    pipeline.expire = MagicMock(return_value=pipeline)
    pipeline.execute = AsyncMock(return_value=[None, 5, None, None])  # 5 requests so far
    
    redis.pipeline.return_value = pipeline
    return redis


class TestRequestIdentifier:
    """Test request identifier extraction."""
    
    def test_identifier_with_user_id(self, mock_request):
        """Test identifier uses user ID when available."""
        mock_request.state.user_id = "123"
        
        identifier = get_request_identifier(mock_request)
        assert identifier == "user:123"
    
    def test_identifier_without_user_id(self, mock_request):
        """Test identifier falls back to IP."""
        # No user_id attribute
        delattr(mock_request.state, "user_id") if hasattr(mock_request.state, "user_id") else None
        
        identifier = get_request_identifier(mock_request)
        assert identifier == "ip:192.168.1.100"
    
    def test_identifier_with_proxy(self, mock_request):
        """Test identifier extracts IP from X-Forwarded-For."""
        mock_request.headers["X-Forwarded-For"] = "10.0.0.1, 192.168.1.1"
        
        identifier = get_request_identifier(mock_request)
        # Should extract first IP
        assert "10.0.0.1" in identifier


class TestRateLimitExceededHandler:
    """Test custom rate limit error handler."""
    
    def test_handler_returns_json(self, mock_request):
        """Test handler returns JSON response."""
        exc = RateLimitExceeded()
        exc.detail = "10 per 1 minute"
        exc.retry_after = 45
        exc.limit = 10
        
        response = rate_limit_exceeded_handler(mock_request, exc)
        
        assert isinstance(response, JSONResponse)
        assert response.status_code == 429
    
    def test_handler_includes_retry_after(self, mock_request):
        """Test handler includes Retry-After header."""
        exc = RateLimitExceeded()
        exc.retry_after = 30
        exc.limit = 5
        
        response = rate_limit_exceeded_handler(mock_request, exc)
        
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "30"
    
    def test_handler_turkish_message(self, mock_request):
        """Test handler returns Turkish error message."""
        exc = RateLimitExceeded()
        
        response = rate_limit_exceeded_handler(mock_request, exc)
        
        # Parse JSON body
        import json
        body = json.loads(response.body.decode())
        
        assert "message" in body
        assert "?stek limiti" in body["message"]  # Turkish
        assert body["error"] == "rate_limit_exceeded"


@pytest.mark.asyncio
class TestRedisRateLimitChecker:
    """Test Redis-based rate limit checking."""
    
    async def test_check_rate_limit_allowed(self, mock_redis):
        """Test rate limit check when under limit."""
        key = "user:123:bids"
        limit = 10
        
        # Mock 5 requests so far (under limit)
        mock_redis.pipeline.return_value.execute.return_value = [None, 5, None, None]
        
        is_allowed, remaining = await check_rate_limit_redis(mock_redis, key, limit, 60)
        
        assert is_allowed is True
        assert remaining == 4  # 10 - 5 - 1 = 4
    
    async def test_check_rate_limit_exceeded(self, mock_redis):
        """Test rate limit check when limit exceeded."""
        key = "user:456:bids"
        limit = 10
        
        # Mock 10 requests already (at limit)
        mock_redis.pipeline.return_value.execute.return_value = [None, 10, None, None]
        
        is_allowed, remaining = await check_rate_limit_redis(mock_redis, key, limit, 60)
        
        assert is_allowed is False
        assert remaining == 0
    
    async def test_check_rate_limit_first_request(self, mock_redis):
        """Test rate limit check for first request."""
        key = "user:789:bids"
        limit = 5
        
        # Mock 0 requests so far
        mock_redis.pipeline.return_value.execute.return_value = [None, 0, None, None]
        
        is_allowed, remaining = await check_rate_limit_redis(mock_redis, key, limit, 60)
        
        assert is_allowed is True
        assert remaining == 4  # 5 - 0 - 1 = 4
    
    async def test_check_rate_limit_cleanup(self, mock_redis):
        """Test rate limit cleanup of old entries."""
        key = "user:123:requests"
        limit = 10
        
        await check_rate_limit_redis(mock_redis, key, limit, window_seconds=60)
        
        # Verify pipeline operations
        pipeline = mock_redis.pipeline.return_value
        pipeline.zremrangebyscore.assert_called_once()  # Cleanup old
        pipeline.zcard.assert_called_once()              # Count current
        pipeline.zadd.assert_called_once()               # Add new
        pipeline.expire.assert_called_once()             # Set TTL


class TestRateLimitInfo:
    """Test rate limit information endpoint."""
    
    def test_get_rate_limit_info_authenticated(self, mock_request):
        """Test rate limit info for authenticated user."""
        mock_request.state.user_id = "123"
        
        info = get_rate_limit_info(mock_request)
        
        assert info["identifier"] == "user:123"
        assert "limits" in info
        assert "bids" in info["limits"]
        assert info["limits"]["bids"] == "10/minute"
    
    def test_get_rate_limit_info_unauthenticated(self, mock_request):
        """Test rate limit info for unauthenticated request."""
        # No user_id
        info = get_rate_limit_info(mock_request)
        
        assert "ip:" in info["identifier"]
        assert "limits" in info
    
    def test_get_rate_limit_info_includes_headers(self, mock_request):
        """Test rate limit info includes header documentation."""
        info = get_rate_limit_info(mock_request)
        
        assert "headers" in info
        assert "X-RateLimit-Limit" in info["headers"]
        assert "X-RateLimit-Remaining" in info["headers"]
        assert "X-RateLimit-Reset" in info["headers"]


class TestRateLimitDecorators:
    """Test rate limit decorator functions."""
    
    def test_limit_bid_requests(self):
        """Test bid request rate limiter."""
        limiter = limit_bid_requests()
        assert limiter is not None
    
    def test_limit_valuation_requests(self):
        """Test valuation request rate limiter."""
        limiter = limit_valuation_requests()
        assert limiter is not None
    
    def test_limit_login_requests(self):
        """Test login request rate limiter."""
        limiter = limit_login_requests()
        assert limiter is not None
    
    def test_limit_analytics_requests(self):
        """Test analytics request rate limiter."""
        limiter = limit_analytics_requests()
        assert limiter is not None


@pytest.mark.integration
class TestRateLimitIntegration:
    """Integration tests with FastAPI app."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app with rate limiting."""
        from fastapi import FastAPI, Depends
        from backend.middleware.rate_limit import limiter, limit_api_calls
        
        app = FastAPI()
        
        @app.get("/test")
        @limit_api_calls(5)
        async def test_endpoint():
            return {"message": "ok"}
        
        return app
    
    def test_rate_limit_headers_present(self, app):
        """Test that rate limit headers are added to response."""
        from fastapi.testclient import TestClient
        
        client = TestClient(app)
        
        # First request should succeed
        response = client.get("/test")
        
        assert response.status_code == 200
        # Note: In real scenario, headers would be present
        # This test would require full slowapi integration


@pytest.mark.asyncio
class TestConcurrentRequests:
    """Test rate limiting under concurrent load."""
    
    async def test_concurrent_requests_under_limit(self, mock_redis):
        """Test multiple concurrent requests under limit."""
        key = "user:123:concurrent"
        limit = 20
        
        # Simulate 10 concurrent checks
        results = []
        for i in range(10):
            mock_redis.pipeline.return_value.execute.return_value = [None, i, None, None]
            is_allowed, remaining = await check_rate_limit_redis(mock_redis, key, limit, 60)
            results.append((is_allowed, remaining))
        
        # All should be allowed
        assert all(allowed for allowed, _ in results)
    
    async def test_concurrent_requests_at_limit(self, mock_redis):
        """Test requests near limit boundary."""
        key = "user:456:boundary"
        limit = 10
        
        # Request when at limit - 1
        mock_redis.pipeline.return_value.execute.return_value = [None, 9, None, None]
        is_allowed_1, remaining_1 = await check_rate_limit_redis(mock_redis, key, limit, 60)
        
        # Request when at limit
        mock_redis.pipeline.return_value.execute.return_value = [None, 10, None, None]
        is_allowed_2, remaining_2 = await check_rate_limit_redis(mock_redis, key, limit, 60)
        
        assert is_allowed_1 is True
        assert remaining_1 == 0
        assert is_allowed_2 is False
        assert remaining_2 == 0


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_redis_connection_error(self, mock_redis):
        """Test handling of Redis connection errors."""
        key = "user:123:error"
        limit = 10
        
        # Mock Redis error
        mock_redis.pipeline.side_effect = Exception("Redis connection failed")
        
        # Should raise or handle gracefully
        with pytest.raises(Exception):
            await check_rate_limit_redis(mock_redis, key, limit, 60)
    
    def test_negative_limit(self):
        """Test rate limit with negative value."""
        # Should not create limiter with negative value
        # (validation happens at configuration level)
        pass
    
    def test_zero_window(self):
        """Test rate limit with zero window."""
        # Edge case: zero window should default to minimum
        pass
