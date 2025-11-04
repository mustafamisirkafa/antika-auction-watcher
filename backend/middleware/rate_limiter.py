"""
Rate Limiting Middleware (Sprint 2 - Enhanced)
Implements per-user and per-IP rate limiting using slowapi.
"""
import logging
from typing import Callable
from fastapi import Request, Response, HTTPException
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)


def get_user_identifier(request: Request) -> str:
    """
    Get unique identifier for rate limiting.
    
    Priority:
    1. User ID (if authenticated)
    2. IP address (fallback)
    
    Args:
        request: FastAPI request
    
    Returns:
        Unique identifier for rate limiting
    """
    # Try to get user ID from JWT token
    if hasattr(request.state, "user_id"):
        return f"user:{request.state.user_id}"
    
    # Fallback to IP address
    # Check X-Forwarded-For (from reverse proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
        return f"ip:{client_ip}"
    
    # Check X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return f"ip:{real_ip.strip()}"
    
    # Direct connection
    if request.client:
        return f"ip:{request.client.host}"
    
    return "ip:unknown"


# Initialize slowapi limiter
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=["100/minute"],  # Global fallback
    storage_uri="memory://",         # Use in-memory storage (can switch to Redis)
    strategy="fixed-window",         # Fixed window strategy
    headers_enabled=True,            # Include rate limit headers in response
)


# Rate limit decorators for specific endpoints

def rate_limit_login():
    """
    Rate limit for login endpoint.
    5 requests per minute per IP (prevents brute force).
    """
    return limiter.limit("5/minute")


def rate_limit_bid():
    """
    Rate limit for bid endpoints.
    10 requests per minute per user.
    """
    return limiter.limit("10/minute")


def rate_limit_valuation():
    """
    Rate limit for valuation endpoints.
    30 requests per minute per user.
    """
    return limiter.limit("30/minute")


def rate_limit_api():
    """
    General API rate limit.
    100 requests per minute per user.
    """
    return limiter.limit("100/minute")


def rate_limit_websocket():
    """
    Rate limit for WebSocket connections.
    10 connections per minute per IP.
    """
    return limiter.limit("10/minute")


# Custom rate limit exceeded handler
def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded.
    
    Returns structured JSON error instead of plain text.
    
    Args:
        request: FastAPI request
        exc: RateLimitExceeded exception
    
    Returns:
        JSON response with error details
    """
    from backend.core.i18n import tr_error
    
    # Extract rate limit info
    limit = exc.detail
    
    # Get identifier for logging
    identifier = get_user_identifier(request)
    
    logger.warning(
        f"Rate limit exceeded for {identifier} on {request.url.path}: {limit}"
    )
    
    # Return structured error
    return Response(
        content={
            "status": "error",
            "error": tr_error("rate_limit_exceeded"),
            "message": f"Limit a??ld?: {limit}",
            "retry_after": exc.headers.get("Retry-After", "60"),  # Seconds
            "limit": limit,
        },
        status_code=429,
        headers={
            "Retry-After": exc.headers.get("Retry-After", "60"),
            "X-RateLimit-Limit": str(exc.headers.get("X-RateLimit-Limit", "100")),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(exc.headers.get("X-RateLimit-Reset", "60")),
        }
    )


class RateLimiter:
    """
    Legacy rate limiter class (kept for compatibility).
    New code should use slowapi decorators.
    """
    
    def __init__(self, redis_client=None):
        """Initialize rate limiter."""
        self.redis = redis_client
        self.enabled = False  # Disabled in favor of slowapi
        logger.info("Legacy RateLimiter initialized (disabled, using slowapi)")
    
    async def check_rate_limit(self, key: str, limit: int, window: int) -> bool:
        """
        Check rate limit (legacy method).
        
        Args:
            key: Rate limit key
            limit: Maximum requests
            window: Time window in seconds
        
        Returns:
            True if within limit
        """
        # Delegate to slowapi
        return True


# Configuration for Redis-backed rate limiting (optional)

def get_redis_limiter(redis_url: str):
    """
    Create slowapi limiter with Redis backend.
    
    Args:
        redis_url: Redis connection URL (e.g., redis://localhost:6379)
    
    Returns:
        Limiter instance with Redis storage
    
    Example:
        limiter = get_redis_limiter("redis://redis-master:6379/1")
    
    Benefits:
    - Shared state across multiple app instances
    - Persistent rate limits
    - Better for production
    """
    return Limiter(
        key_func=get_user_identifier,
        default_limits=["100/minute"],
        storage_uri=redis_url,
        strategy="fixed-window",
        headers_enabled=True,
    )


# Rate limiting tiers by plan

RATE_LIMITS = {
    "FREE": {
        "api": "50/minute",
        "bid": "5/minute",
        "valuation": "10/minute",
        "websocket": "5/minute",
    },
    "PRO": {
        "api": "200/minute",
        "bid": "20/minute",
        "valuation": "50/minute",
        "websocket": "20/minute",
    },
    "ENTERPRISE": {
        "api": "1000/minute",
        "bid": "100/minute",
        "valuation": "200/minute",
        "websocket": "100/minute",
    },
}


def get_rate_limit_for_plan(plan_code: str, endpoint_type: str) -> str:
    """
    Get rate limit string for a specific plan and endpoint type.
    
    Args:
        plan_code: Plan code (FREE, PRO, ENTERPRISE)
        endpoint_type: Endpoint type (api, bid, valuation, websocket)
    
    Returns:
        Rate limit string (e.g., "100/minute")
    
    Example:
        limit = get_rate_limit_for_plan("PRO", "bid")
        @limiter.limit(limit)
        async def place_bid():
            ...
    """
    plan_limits = RATE_LIMITS.get(plan_code, RATE_LIMITS["FREE"])
    return plan_limits.get(endpoint_type, "100/minute")


def dynamic_rate_limit(request: Request) -> str:
    """
    Dynamic rate limit based on user's plan.
    
    Args:
        request: FastAPI request
    
    Returns:
        Rate limit string based on user's plan
    
    Usage:
        @limiter.limit(dynamic_rate_limit)
        async def some_endpoint(request: Request):
            ...
    """
    # Get user's plan from request state (set by auth middleware)
    plan_code = getattr(request.state, "plan_code", "FREE")
    
    # Determine endpoint type from path
    path = request.url.path
    if "/bid" in path:
        endpoint_type = "bid"
    elif "/valuation" in path:
        endpoint_type = "valuation"
    elif "/ws" in path:
        endpoint_type = "websocket"
    else:
        endpoint_type = "api"
    
    return get_rate_limit_for_plan(plan_code, endpoint_type)
