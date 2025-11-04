"""
Security Headers Middleware (Sprint 2)
Adds security headers to all responses.
"""
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all HTTP responses.
    
    Headers added:
    - Strict-Transport-Security (HSTS)
    - X-Frame-Options
    - X-Content-Type-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    """
    
    def __init__(self, app: ASGIApp, hsts_max_age: int = 31536000):
        """
        Initialize security headers middleware.
        
        Args:
            app: ASGI application
            hsts_max_age: HSTS max-age in seconds (default: 1 year)
        """
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response.
        
        Args:
            request: Incoming request
            call_next: Next middleware in chain
        
        Returns:
            Response with security headers
        """
        response = await call_next(request)
        
        # HSTS (HTTP Strict Transport Security)
        # Enforces HTTPS for 1 year, including subdomains
        response.headers["Strict-Transport-Security"] = f"max-age={self.hsts_max_age}; includeSubDomains; preload"
        
        # X-Frame-Options
        # Prevents clickjacking by disallowing embedding in frames
        response.headers["X-Frame-Options"] = "DENY"
        
        # X-Content-Type-Options
        # Prevents MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-XSS-Protection
        # Legacy XSS filter (modern browsers use CSP)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer-Policy
        # Controls how much referrer information is sent
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions-Policy (formerly Feature-Policy)
        # Restricts which browser features can be used
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        # Content-Security-Policy (CSP)
        # Mitigates XSS, injection attacks
        # Note: Adjust based on your frontend requirements
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://api.antika.auction wss://api.antika.auction; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        
        return response


class SecureCookieConfig:
    """
    Configuration for secure HTTP cookies.
    
    Ensures cookies are:
    - HttpOnly (not accessible via JavaScript)
    - Secure (only sent over HTTPS)
    - SameSite=Lax or Strict (CSRF protection)
    """
    
    @staticmethod
    def get_cookie_settings(secure: bool = True) -> dict:
        """
        Get secure cookie configuration.
        
        Args:
            secure: Whether to enforce HTTPS (True in production)
        
        Returns:
            Dictionary of cookie settings for FastAPI responses
        
        Example:
            response.set_cookie(
                "session_id",
                session_token,
                **SecureCookieConfig.get_cookie_settings()
            )
        """
        return {
            "httponly": True,      # Prevent JavaScript access
            "secure": secure,      # HTTPS only
            "samesite": "lax",     # CSRF protection (lax allows top-level navigation)
            "max_age": 3600,       # 1 hour expiry
        }
    
    @staticmethod
    def get_refresh_token_cookie_settings(secure: bool = True) -> dict:
        """
        Get cookie settings for refresh tokens (longer expiry).
        
        Args:
            secure: Whether to enforce HTTPS
        
        Returns:
            Cookie settings with 24-hour expiry
        """
        return {
            "httponly": True,
            "secure": secure,
            "samesite": "strict",  # Stricter for refresh tokens
            "max_age": 86400,      # 24 hours
        }


def get_cors_config(allow_origins: list[str] = None) -> dict:
    """
    Get CORS configuration for production.
    
    Args:
        allow_origins: List of allowed origins (default: localhost only)
    
    Returns:
        Dictionary of CORS settings for FastAPI CORSMiddleware
    
    Example:
        from fastapi.middleware.cors import CORSMiddleware
        app.add_middleware(CORSMiddleware, **get_cors_config())
    """
    if allow_origins is None:
        # Default: Allow localhost for development
        allow_origins = [
            "http://localhost:3000",
            "http://localhost:8000",
            "https://antika.auction",
            "https://api.antika.auction",
        ]
    
    return {
        "allow_origins": allow_origins,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        "allow_headers": [
            "Authorization",
            "Content-Type",
            "X-Team-Id",
            "X-Request-ID",
        ],
        "expose_headers": [
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ],
        "max_age": 3600,  # Cache preflight requests for 1 hour
    }


def is_production() -> bool:
    """
    Check if running in production environment.
    
    Returns:
        True if ENVIRONMENT is 'production'
    """
    import os
    env = os.getenv("ENVIRONMENT", "development").lower()
    return env == "production"


def validate_https_redirect() -> dict:
    """
    Configuration for HTTPS redirect in production.
    
    Returns:
        Dictionary with redirect settings
    
    Note:
        Fly.io handles HTTPS termination at the edge.
        Application should trust X-Forwarded-Proto header.
    """
    return {
        "enabled": is_production(),
        "trust_forwarded_proto": True,  # Trust Fly.io's X-Forwarded-Proto header
        "permanent": True,               # 301 redirect
    }


class IPWhitelist:
    """
    IP address whitelist for admin endpoints.
    
    Usage:
        whitelist = IPWhitelist(["192.168.1.0/24", "10.0.0.1"])
        if not whitelist.is_allowed(client_ip):
            raise HTTPException(403, "Access denied")
    """
    
    def __init__(self, allowed_ips: list[str]):
        """
        Initialize IP whitelist.
        
        Args:
            allowed_ips: List of IP addresses or CIDR ranges
        """
        self.allowed_ips = set(allowed_ips)
    
    def is_allowed(self, ip: str) -> bool:
        """
        Check if IP is whitelisted.
        
        Args:
            ip: Client IP address
        
        Returns:
            True if IP is allowed
        """
        # Simple exact match (extend with CIDR support if needed)
        return ip in self.allowed_ips
    
    def add(self, ip: str):
        """Add IP to whitelist."""
        self.allowed_ips.add(ip)
    
    def remove(self, ip: str):
        """Remove IP from whitelist."""
        self.allowed_ips.discard(ip)


# Security utilities

def sanitize_header(header_value: str) -> str:
    """
    Sanitize header value to prevent header injection.
    
    Args:
        header_value: Raw header value
    
    Returns:
        Sanitized header value (no newlines, limited length)
    """
    if not header_value:
        return ""
    
    # Remove newlines (prevents header injection)
    sanitized = header_value.replace("\r", "").replace("\n", "")
    
    # Limit length to prevent DoS
    max_length = 1000
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


def generate_request_id() -> str:
    """
    Generate unique request ID for tracing.
    
    Returns:
        UUID-based request ID
    """
    import uuid
    return str(uuid.uuid4())


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request.
    
    Handles:
    - Direct connection (request.client.host)
    - Reverse proxy (X-Forwarded-For, X-Real-IP)
    
    Args:
        request: FastAPI request
    
    Returns:
        Client IP address
    """
    # Check X-Forwarded-For (from reverse proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # First IP in the chain is the original client
        return forwarded_for.split(",")[0].strip()
    
    # Check X-Real-IP (alternative header)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fallback to direct connection
    if request.client:
        return request.client.host
    
    return "unknown"


def get_user_agent(request: Request) -> str:
    """
    Extract user agent from request.
    
    Args:
        request: FastAPI request
    
    Returns:
        User agent string (sanitized)
    """
    user_agent = request.headers.get("User-Agent", "")
    return sanitize_header(user_agent)
