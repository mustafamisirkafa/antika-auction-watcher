"""
Security Headers Middleware (Sprint 2)
Adds security headers to all responses for protection against common attacks.
"""
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    Headers added:
    - Strict-Transport-Security (HSTS)
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    """
    
    def __init__(self, app, hsts_max_age: int = 31536000):
        """
        Initialize security headers middleware.
        
        Args:
            app: FastAPI application
            hsts_max_age: HSTS max-age in seconds (default: 1 year)
        """
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
        
        Returns:
            Response with security headers
        """
        # Process request
        response = await call_next(request)
        
        # Add security headers
        self._add_security_headers(response, request)
        
        return response
    
    def _add_security_headers(self, response: Response, request: Request) -> None:
        """
        Add security headers to response.
        
        Args:
            response: FastAPI response
            request: FastAPI request
        """
        # HSTS - Force HTTPS for all future requests
        # Only add if connection is HTTPS
        if self._is_secure(request):
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains; preload"
            )
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS Protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (disable unnecessary features)
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        
        # Content Security Policy (CSP)
        # Restrictive policy - adjust as needed for your frontend
        if not self._is_health_endpoint(request):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' wss: ws:; "
                "frame-ancestors 'none';"
            )
    
    def _is_secure(self, request: Request) -> bool:
        """
        Check if request is over HTTPS.
        
        Args:
            request: FastAPI request
        
        Returns:
            True if HTTPS or behind reverse proxy with X-Forwarded-Proto
        """
        # Check if request is HTTPS
        if request.url.scheme == "https":
            return True
        
        # Check X-Forwarded-Proto header (for reverse proxies like Fly.io)
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
        return forwarded_proto.lower() == "https"
    
    def _is_health_endpoint(self, request: Request) -> bool:
        """
        Check if request is to a health check endpoint.
        
        Args:
            request: FastAPI request
        
        Returns:
            True if health endpoint
        """
        health_paths = ["/health", "/ready", "/metrics", "/status"]
        return any(request.url.path.startswith(path) for path in health_paths)


# Cookie security settings
class SecureCookieConfig:
    """
    Configuration for secure cookie settings.
    
    Settings:
    - Secure: Only send over HTTPS
    - HttpOnly: Not accessible via JavaScript
    - SameSite: Strict CSRF protection
    """
    
    @staticmethod
    def get_cookie_params(is_https: bool = True) -> dict:
        """
        Get secure cookie parameters.
        
        Args:
            is_https: Whether connection is HTTPS
        
        Returns:
            Dict with cookie parameters
        """
        return {
            "httponly": True,        # Prevent XSS access
            "secure": is_https,      # HTTPS only
            "samesite": "strict",    # CSRF protection
            "max_age": 3600,         # 1 hour
            "domain": None,          # Set to your domain in production
            "path": "/",
        }


# CORS configuration helper
class SecureCORSConfig:
    """
    Secure CORS configuration.
    """
    
    # Production allowed origins (whitelist)
    ALLOWED_ORIGINS = [
        "https://antika-auction-watcher.fly.dev",
        "https://www.antika-auction-watcher.com",
    ]
    
    # Development allowed origins
    DEV_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    
    @classmethod
    def get_allowed_origins(cls, is_production: bool = False) -> list:
        """
        Get allowed CORS origins based on environment.
        
        Args:
            is_production: Whether running in production
        
        Returns:
            List of allowed origins
        """
        if is_production:
            return cls.ALLOWED_ORIGINS
        return cls.ALLOWED_ORIGINS + cls.DEV_ORIGINS
    
    @staticmethod
    def get_cors_config(is_production: bool = False) -> dict:
        """
        Get CORS middleware configuration.
        
        Args:
            is_production: Whether running in production
        
        Returns:
            Dict with CORS settings
        """
        return {
            "allow_origins": SecureCORSConfig.get_allowed_origins(is_production),
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": [
                "Authorization",
                "Content-Type",
                "X-Team-Id",
                "X-Request-ID",
            ],
            "expose_headers": [
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset",
            ],
            "max_age": 600,  # 10 minutes
        }
