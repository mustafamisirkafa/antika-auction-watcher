"""Rate limiting middleware using Redis sliding window."""
import time
from typing import Optional, Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from backend.realtime.redis_manager import RedisManager
from backend.core.config import settings


class RateLimiter(BaseHTTPMiddleware):
    """
    Rate limiting middleware with sliding window algorithm.
    
    Features:
    - Per-user rate limiting
    - Per-endpoint rate limiting
    - Configurable time windows
    - Redis-based distributed limiting
    """

    def __init__(self, app, redis_manager: Optional[RedisManager] = None):
        super().__init__(app)
        self.redis_manager = redis_manager or RedisManager()
        self.enabled = settings.rate_limit_enabled
        
        # Default rate limits (requests per minute)
        self.default_limit = 60
        
        # Endpoint-specific limits
        self.endpoint_limits = {
            '/api/v1/valuations/estimate': 30,
            '/api/v1/bids/place': 20,
            '/api/v1/bids/decision': 40,
            '/api/v1/items': 100
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        if not self.enabled:
            return await call_next(request)
        
        # Skip rate limiting for health checks and admin endpoints
        if request.url.path in ['/health', '/']:
            return await call_next(request)
        
        # Get user identifier (IP or user ID if authenticated)
        user_id = await self._get_user_identifier(request)
        
        # Get rate limit for this endpoint
        limit = self._get_rate_limit(request.url.path)
        
        # Check rate limit
        allowed, remaining, reset_time = await self._check_rate_limit(
            user_id,
            request.url.path,
            limit
        )
        
        # Add rate limit headers to response
        response = None
        if allowed:
            response = await call_next(request)
        else:
            response = Response(
                content='Rate limit exceeded. Please try again later.',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # Add headers
        response.headers['X-RateLimit-Limit'] = str(limit)
        response.headers['X-RateLimit-Remaining'] = str(remaining)
        response.headers['X-RateLimit-Reset'] = str(reset_time)
        
        if not allowed:
            retry_after = int(reset_time - time.time())
            response.headers['Retry-After'] = str(max(retry_after, 1))
        
        return response

    async def _get_user_identifier(self, request: Request) -> str:
        """Get unique identifier for the user."""
        # Try to get user ID from JWT token
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            # In production, decode JWT and get user ID
            # For now, use the token itself as identifier
            return f"user:{auth_header}"
        
        # Fall back to IP address
        client_ip = request.client.host if request.client else 'unknown'
        return f"ip:{client_ip}"

    def _get_rate_limit(self, path: str) -> int:
        """Get rate limit for endpoint."""
        # Check for exact match
        if path in self.endpoint_limits:
            return self.endpoint_limits[path]
        
        # Check for prefix match
        for endpoint_path, limit in self.endpoint_limits.items():
            if path.startswith(endpoint_path):
                return limit
        
        return self.default_limit

    async def _check_rate_limit(
        self,
        user_id: str,
        endpoint: str,
        limit: int,
        window_seconds: int = 60
    ) -> tuple[bool, int, int]:
        """
        Check rate limit using sliding window algorithm.
        
        Args:
            user_id: User identifier
            endpoint: API endpoint
            limit: Maximum requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            Tuple of (allowed, remaining, reset_time)
        """
        try:
            await self.redis_manager.connect()
            
            # Create key for this user and endpoint
            key = f"rate_limit:{user_id}:{endpoint}"
            
            # Get current timestamp
            now = time.time()
            window_start = now - window_seconds
            
            # Use Redis sorted set for sliding window
            # Each request is scored by its timestamp
            
            # Remove old entries outside the window
            # (In production, use actual Redis commands)
            # For now, simulate the logic
            
            # Get current count
            cached_data = await self.redis_manager.cache_get(key)
            
            if cached_data is None:
                # First request
                current_count = 0
            else:
                import json
                data = json.loads(cached_data)
                # Filter requests within window
                requests_in_window = [
                    ts for ts in data.get('timestamps', [])
                    if ts > window_start
                ]
                current_count = len(requests_in_window)
            
            # Check if limit exceeded
            allowed = current_count < limit
            remaining = max(0, limit - current_count - 1)
            
            if allowed:
                # Record this request
                if cached_data is None:
                    new_data = {'timestamps': [now]}
                else:
                    data = json.loads(cached_data)
                    timestamps = [ts for ts in data.get('timestamps', []) if ts > window_start]
                    timestamps.append(now)
                    new_data = {'timestamps': timestamps}
                
                import json
                await self.redis_manager.cache_set(
                    key,
                    json.dumps(new_data),
                    window_seconds
                )
            
            # Calculate reset time
            reset_time = int(now + window_seconds)
            
            await self.redis_manager.disconnect()
            
            return allowed, remaining, reset_time
            
        except Exception as e:
            # If Redis fails, allow the request (fail open)
            return True, limit, int(time.time() + 60)
