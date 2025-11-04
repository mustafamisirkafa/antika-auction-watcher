"""
Rate Limiting Middleware (Sprint 2)
Implements per-user and per-IP rate limiting using slowapi.
"""
import logging
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)


def get_user_or_ip_key(request: Request) -> str:
    """
    Rate limit key function that uses user ID if authenticated, otherwise IP.
    
    Args:
        request: FastAPI request
    
    Returns:
        Rate limit key (user ID or IP address)
    """
    # Try to get user ID from JWT token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            from backend.core.auth_enhanced import decode_token
            payload = decode_token(token)
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass  # Fall back to IP
    
    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


def get_user_key(request: Request) -> str:
    """
    Rate limit key function for user-specific limits.
    
    Args:
        request: FastAPI request
    
    Returns:
        User ID or "anonymous"
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            from backend.core.auth_enhanced import decode_token
            payload = decode_token(token)
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass
    
    return f"ip:{get_remote_address(request)}"


# Initialize limiter
limiter = Limiter(
    key_func=get_user_or_ip_key,
    default_limits=["100/minute"],  # Global fallback
    headers_enabled=True,  # Include rate limit info in headers
    storage_uri="memory://",  # Use in-memory storage (can switch to Redis)
)


def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom handler for rate limit exceeded errors.
    
    Returns structured JSON response in Turkish.
    
    Args:
        request: FastAPI request
        exc: RateLimitExceeded exception
    
    Returns:
        JSON error response
    """
    logger.warning(
        f"Rate limit exceeded: {request.url.path} "
        f"from {get_remote_address(request)}"
    )
    
    return Response(
        content={
            "error": "rate_limit_exceeded",
            "message": "?stek limiti a??ld?. L?tfen daha sonra tekrar deneyin.",
            "detail": f"Limit: {exc.detail}",
            "retry_after": getattr(exc, "retry_after", None),
        },
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        headers={
            "Retry-After": str(getattr(exc, "retry_after", 60)),
            "X-RateLimit-Limit": str(exc.limit),
            "X-RateLimit-Remaining": "0",
        },
    )


# Rate limit decorators for different endpoints
class RateLimits:
    """
    Predefined rate limits for different endpoint types.
    """
    
    # Authentication endpoints
    LOGIN = "5/minute"           # 5 login attempts per minute
    REGISTER = "3/hour"          # 3 registrations per hour
    REFRESH = "10/minute"        # 10 token refreshes per minute
    
    # Bidding endpoints
    BID = "10/minute"            # 10 bids per minute
    BID_RULE = "20/minute"       # 20 bid rule changes per minute
    
    # Valuation endpoints
    VALUATION = "30/minute"      # 30 valuation requests per minute
    PROFIT = "20/minute"         # 20 profit advisor requests per minute
    
    # Analytics endpoints
    ANALYTICS = "60/minute"      # 60 analytics requests per minute
    
    # Admin endpoints
    ADMIN = "100/minute"         # 100 admin requests per minute
    
    # User preferences
    PREFS = "30/minute"          # 30 preference updates per minute
    
    # WebSocket connections
    WS_CONNECT = "10/minute"     # 10 WebSocket connections per minute
    
    # Global default
    DEFAULT = "100/minute"       # 100 requests per minute


# Middleware to add rate limit headers
async def rate_limit_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to add rate limit information to all responses.
    
    Args:
        request: FastAPI request
        call_next: Next middleware/handler
    
    Returns:
        Response with rate limit headers
    """
    # Process request
    response = await call_next(request)
    
    # Add rate limit headers (if available from limiter state)
    # These are added automatically by slowapi when limit is checked
    
    return response


def get_rate_limiter_state(key: str) -> dict:
    """
    Get current rate limiter state for a key.
    
    Args:
        key: Rate limit key (e.g., "user:123" or "ip:192.168.1.1")
    
    Returns:
        Dict with current usage and limits
    """
    # This is a simplified version - actual implementation
    # would query the limiter's storage backend
    return {
        "key": key,
        "remaining": "N/A",
        "limit": "N/A",
        "reset": "N/A",
    }
