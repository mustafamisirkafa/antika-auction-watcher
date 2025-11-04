"""
Rate Limiting Middleware (Sprint 2)

Implements per-user and per-IP rate limiting using slowapi.

Limits:
- /api/bid: 10 requests/minute per user
- /api/valuation: 30 requests/minute per user
- /api/login: 5 requests/minute per IP
- Global fallback: 100 requests/minute per IP

Rate limit headers:
- X-RateLimit-Limit: Maximum requests allowed
- X-RateLimit-Remaining: Remaining requests
- X-RateLimit-Reset: Time when limit resets (Unix timestamp)
"""

import logging
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.core.security import get_client_ip

logger = logging.getLogger(__name__)


def get_request_identifier(request: Request) -> str:
    """
    Get identifier for rate limiting (user ID or IP).
    
    Priority:
    1. User ID from JWT (if authenticated)
    2. Client IP address
    
    Args:
        request: FastAPI request
    
    Returns:
        Identifier string for rate limiting
    """
    # Try to get user ID from request state (set by auth middleware)
    if hasattr(request.state, "user_id"):
        return f"user:{request.state.user_id}"
    
    # Fallback to IP address
    client_ip = get_client_ip(request)
    return f"ip:{client_ip}"


# Initialize rate limiter
limiter = Limiter(
    key_func=get_request_identifier,
    default_limits=["100/minute"],  # Global fallback
    storage_uri="redis://redis:6379/0",
    strategy="fixed-window",
    headers_enabled=True,
)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.
    
    Returns JSON response instead of plain text.
    
    Args:
        request: FastAPI request
        exc: RateLimitExceeded exception
    
    Returns:
        JSON error response with Turkish message
    """
    from fastapi.responses import JSONResponse
    
    # Extract reset time from exception
    retry_after = getattr(exc, "retry_after", None)
    
    response_data = {
        "error": "rate_limit_exceeded",
        "message": "?stek limiti a??ld?. L?tfen daha sonra tekrar deneyin.",
        "detail": str(exc.detail) if hasattr(exc, "detail") else "?ok fazla istek g?nderildi",
    }
    
    if retry_after:
        response_data["retry_after"] = retry_after
    
    logger.warning(f"Rate limit exceeded for {get_request_identifier(request)}: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=response_data,
        headers={
            "Retry-After": str(retry_after) if retry_after else "60",
            "X-RateLimit-Limit": str(getattr(exc, "limit", "unknown")),
            "X-RateLimit-Remaining": "0",
        }
    )


# Route-specific rate limit decorators

def limit_bid_requests():
    """
    Rate limit for bid endpoints: 10 requests/minute per user.
    
    Usage:
        @router.post("/bid")
        @limit_bid_requests()
        async def create_bid(...):
            ...
    """
    return limiter.limit("10/minute")


def limit_valuation_requests():
    """
    Rate limit for valuation endpoints: 30 requests/minute per user.
    
    Usage:
        @router.get("/valuation")
        @limit_valuation_requests()
        async def get_valuation(...):
            ...
    """
    return limiter.limit("30/minute")


def limit_login_requests():
    """
    Rate limit for authentication endpoints: 5 requests/minute per IP.
    
    Prevents brute-force attacks.
    
    Usage:
        @router.post("/login")
        @limit_login_requests()
        async def login(...):
            ...
    """
    return limiter.limit("5/minute", key_func=lambda request: f"ip:{get_client_ip(request)}")


def limit_analytics_requests():
    """
    Rate limit for analytics endpoints: 60 requests/minute per user.
    
    Usage:
        @router.get("/analytics/overview")
        @limit_analytics_requests()
        async def get_analytics(...):
            ...
    """
    return limiter.limit("60/minute")


def limit_api_calls(calls_per_minute: int):
    """
    Generic rate limiter with custom limit.
    
    Args:
        calls_per_minute: Maximum calls per minute
    
    Returns:
        Rate limiter decorator
    
    Usage:
        @router.get("/custom")
        @limit_api_calls(15)
        async def custom_endpoint(...):
            ...
    """
    return limiter.limit(f"{calls_per_minute}/minute")


# IP-based rate limits (for public/unauthenticated endpoints)

def get_ip_identifier(request: Request) -> str:
    """Get IP-only identifier (ignore auth)."""
    return f"ip:{get_client_ip(request)}"


def limit_by_ip(calls_per_minute: int):
    """
    Rate limit by IP only (for public endpoints).
    
    Args:
        calls_per_minute: Maximum calls per minute per IP
    
    Returns:
        Rate limiter decorator
    """
    return limiter.limit(
        f"{calls_per_minute}/minute",
        key_func=get_ip_identifier
    )


# Redis-based rate limit checker (for manual checks)

async def check_rate_limit_redis(
    redis,
    key: str,
    limit: int,
    window_seconds: int = 60
) -> tuple[bool, int]:
    """
    Check rate limit using Redis directly.
    
    Useful for custom rate limiting logic outside of route decorators.
    
    Args:
        redis: Redis client
        key: Rate limit key (e.g., "user:123:bids")
        limit: Maximum requests allowed
        window_seconds: Time window in seconds
    
    Returns:
        Tuple of (is_allowed, remaining_requests)
    
    Example:
        is_allowed, remaining = await check_rate_limit_redis(
            redis, f"user:{user_id}:autobid_starts", limit=10, window_seconds=60
        )
        if not is_allowed:
            raise HTTPException(429, "Too many autobid starts")
    """
    import time
    
    current_time = int(time.time())
    window_start = current_time - window_seconds
    
    # Redis sorted set: members are timestamps, score is timestamp
    pipe = redis.pipeline()
    
    # Remove old entries outside window
    pipe.zremrangebyscore(key, 0, window_start)
    
    # Count current entries
    pipe.zcard(key)
    
    # Add current request
    pipe.zadd(key, {str(current_time): current_time})
    
    # Set expiration
    pipe.expire(key, window_seconds)
    
    results = await pipe.execute()
    current_count = results[1]  # Result from ZCARD
    
    is_allowed = current_count < limit
    remaining = max(0, limit - current_count - 1)
    
    return is_allowed, remaining


# Rate limit info endpoint

def get_rate_limit_info(request: Request) -> dict:
    """
    Get current rate limit status for request.
    
    Args:
        request: FastAPI request
    
    Returns:
        Dictionary with rate limit info
    
    Example:
        {
            "identifier": "user:123",
            "limits": {
                "global": "100/minute",
                "bids": "10/minute",
                "valuations": "30/minute"
            },
            "remaining": {
                "global": 87,
                "bids": 5
            }
        }
    """
    identifier = get_request_identifier(request)
    
    return {
        "identifier": identifier,
        "limits": {
            "global": "100/minute",
            "bids": "10/minute",
            "valuations": "30/minute",
            "analytics": "60/minute",
            "login": "5/minute (IP-based)",
        },
        "headers": {
            "X-RateLimit-Limit": "Maximum requests allowed",
            "X-RateLimit-Remaining": "Requests remaining in current window",
            "X-RateLimit-Reset": "Unix timestamp when limit resets",
        }
    }
