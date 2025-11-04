"""
Enhanced JWT Authentication (Sprint 2)
Implements access/refresh token flow with security hardening.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Request, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import hashlib

from backend.core.config import settings
from backend.middleware.team_context import get_redis

logger = logging.getLogger(__name__)

# JWT Configuration
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
REFRESH_TOKEN_EXPIRE_HOURS = 24    # 24 hours
ALGORITHM = "HS256"

# Security bearer
security = HTTPBearer()


class TokenPayload:
    """JWT token payload structure."""
    
    def __init__(
        self,
        sub: str,
        exp: datetime,
        token_type: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ):
        self.sub = sub  # User ID
        self.exp = exp  # Expiration time
        self.token_type = token_type  # "access" or "refresh"
        self.user_agent = user_agent
        self.ip_address = ip_address


def create_access_token(
    user_id: str,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User identifier
        user_agent: User-Agent header for binding
        ip_address: Client IP for binding
        expires_delta: Custom expiration time
    
    Returns:
        Encoded JWT token
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.utcnow() + expires_delta
    
    payload = {
        "sub": user_id,
        "exp": expire,
        "token_type": "access",
        "iat": datetime.utcnow(),
    }
    
    # Add security binding (optional)
    if user_agent:
        payload["ua_hash"] = _hash_string(user_agent)
    if ip_address:
        payload["ip_hash"] = _hash_string(ip_address)
    
    encoded_jwt = jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    user_id: str,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        user_id: User identifier
        user_agent: User-Agent header for binding
        ip_address: Client IP for binding
    
    Returns:
        Encoded JWT refresh token
    """
    expires_delta = timedelta(hours=REFRESH_TOKEN_EXPIRE_HOURS)
    expire = datetime.utcnow() + expires_delta
    
    payload = {
        "sub": user_id,
        "exp": expire,
        "token_type": "refresh",
        "iat": datetime.utcnow(),
    }
    
    # Add security binding
    if user_agent:
        payload["ua_hash"] = _hash_string(user_agent)
    if ip_address:
        payload["ip_hash"] = _hash_string(ip_address)
    
    encoded_jwt = jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded token payload
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ge?ersiz veya s?resi dolmu?",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_access_token(
    token: str,
    request: Optional[Request] = None
) -> str:
    """
    Verify an access token and return user ID.
    
    Args:
        token: JWT access token
        request: FastAPI request (for security binding)
    
    Returns:
        User ID from token
    
    Raises:
        HTTPException: If token is invalid, expired, or binding fails
    """
    payload = decode_token(token)
    
    # Check token type
    if payload.get("token_type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ge?ersiz token t?r?",
        )
    
    # Verify security binding (if present in token)
    if request:
        if "ua_hash" in payload:
            user_agent = request.headers.get("User-Agent", "")
            if _hash_string(user_agent) != payload["ua_hash"]:
                logger.warning(f"User-Agent mismatch for user {payload['sub']}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token g?venlik do?rulamas? ba?ar?s?z",
                )
        
        if "ip_hash" in payload:
            client_ip = _get_client_ip(request)
            if _hash_string(client_ip) != payload["ip_hash"]:
                logger.warning(f"IP address mismatch for user {payload['sub']}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token g?venlik do?rulamas? ba?ar?s?z",
                )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ge?ersiz token yap?s?",
        )
    
    return user_id


def verify_refresh_token(token: str) -> str:
    """
    Verify a refresh token and return user ID.
    
    Args:
        token: JWT refresh token
    
    Returns:
        User ID from token
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    payload = decode_token(token)
    
    # Check token type
    if payload.get("token_type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ge?ersiz token t?r?",
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ge?ersiz token yap?s?",
        )
    
    return user_id


async def store_refresh_token(user_id: str, token: str, redis) -> None:
    """
    Store refresh token in Redis with expiration.
    
    Args:
        user_id: User identifier
        token: Refresh token
        redis: Redis client
    """
    key = f"refresh_token:{user_id}"
    ttl = REFRESH_TOKEN_EXPIRE_HOURS * 3600  # Convert to seconds
    await redis.setex(key, ttl, token)
    logger.info(f"Stored refresh token for user {user_id}")


async def verify_stored_refresh_token(user_id: str, token: str, redis) -> bool:
    """
    Verify that refresh token matches stored token in Redis.
    
    Args:
        user_id: User identifier
        token: Refresh token to verify
        redis: Redis client
    
    Returns:
        True if token matches stored token
    """
    key = f"refresh_token:{user_id}"
    stored_token = await redis.get(key)
    
    if not stored_token:
        return False
    
    return stored_token.decode() == token


async def revoke_refresh_token(user_id: str, redis) -> None:
    """
    Revoke a user's refresh token.
    
    Args:
        user_id: User identifier
        redis: Redis client
    """
    key = f"refresh_token:{user_id}"
    await redis.delete(key)
    logger.info(f"Revoked refresh token for user {user_id}")


def _hash_string(value: str) -> str:
    """
    Hash a string using SHA-256.
    
    Args:
        value: String to hash
    
    Returns:
        Hexadecimal hash digest
    """
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def _get_client_ip(request: Request) -> str:
    """
    Extract client IP from request.
    
    Handles X-Forwarded-For header for reverse proxies.
    
    Args:
        request: FastAPI request
    
    Returns:
        Client IP address
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# FastAPI dependency for protected routes
async def get_current_user_enhanced(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    FastAPI dependency to get current user from JWT with security checks.
    
    Args:
        request: FastAPI request
        credentials: HTTP Bearer credentials
    
    Returns:
        User ID
    
    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    user_id = verify_access_token(token, request)
    return user_id


# Token refresh endpoint data models
from pydantic import BaseModel


class TokenResponse(BaseModel):
    """Response model for token endpoints."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str
