"""
Token Refresh Endpoint (Sprint 2)
Provides JWT token refresh functionality.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.core.auth_enhanced import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    verify_stored_refresh_token,
    store_refresh_token,
    revoke_refresh_token,
    TokenResponse,
    RefreshTokenRequest,
    _get_client_ip,
)
from backend.middleware.team_context import get_redis
from backend.core.i18n import tr_error, tr_success

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    request: Request,
    refresh_request: RefreshTokenRequest,
    redis = Depends(get_redis),
):
    """
    Refresh access token using refresh token.
    
    Flow:
    1. Validate refresh token (structure + expiration)
    2. Verify token matches stored token in Redis
    3. Generate new access token
    4. Optionally generate new refresh token (rotation)
    5. Store new refresh token
    
    Args:
        request: FastAPI request
        refresh_request: Refresh token request
        redis: Redis client
    
    Returns:
        New access and refresh tokens
    
    Raises:
        HTTPException: If refresh token is invalid or revoked
    """
    refresh_token = refresh_request.refresh_token
    
    try:
        # Verify refresh token structure and expiration
        user_id = verify_refresh_token(refresh_token)
        
        # Verify token matches stored token in Redis
        is_valid = await verify_stored_refresh_token(user_id, refresh_token, redis)
        
        if not is_valid:
            logger.warning(f"Refresh token mismatch or revoked for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=tr_error("token_revoked"),
            )
        
        # Extract security binding info
        user_agent = request.headers.get("User-Agent")
        ip_address = _get_client_ip(request)
        
        # Generate new access token
        new_access_token = create_access_token(
            user_id=user_id,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        
        # Generate new refresh token (token rotation)
        new_refresh_token = create_refresh_token(
            user_id=user_id,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        
        # Store new refresh token
        await store_refresh_token(user_id, new_refresh_token, redis)
        
        logger.info(f"Token refreshed for user {user_id}")
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=3600,  # 1 hour
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=tr_error("token_invalid"),
        )


@router.post("/revoke")
async def revoke_token(
    request: Request,
    user_id: str,  # In production, get from authenticated user
    redis = Depends(get_redis),
):
    """
    Revoke a user's refresh token.
    
    Use case: Logout, security breach, password change.
    
    Args:
        request: FastAPI request
        user_id: User ID (should come from authenticated session)
        redis: Redis client
    
    Returns:
        Success message
    """
    await revoke_refresh_token(user_id, redis)
    
    logger.info(f"Refresh token revoked for user {user_id}")
    
    return {
        "message": tr_success("token_revoked"),
        "user_id": user_id,
    }
