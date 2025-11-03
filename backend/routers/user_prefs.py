"""
User Preferences API (Phase 14).
Endpoints for managing seller allowlists and blocklists.
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from backend.db.database import get_db
from backend.core.auth import get_current_user
from backend.models.user_prefs import (
    UserPreferencesResponse,
    UpdatePreferenceRequest,
    UpdatePreferenceResponse,
    SellerItem
)
from backend.services.user_prefs_svc import UserPreferencesService
from backend.services.event_bus import EventBus
from backend.middleware.team_context import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user/prefs", tags=["User Preferences"])


# Dependency injection
async def get_user_prefs_service(
    db: Session = Depends(get_db),
    redis = Depends(get_redis)
) -> UserPreferencesService:
    """Get UserPreferencesService instance."""
    event_bus = EventBus(redis)
    return UserPreferencesService(db, redis, event_bus)


@router.get("", response_model=UserPreferencesResponse)
async def get_user_preferences(
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: UserPreferencesService = Depends(get_user_prefs_service)
):
    """
    Get current user's seller preferences.
    
    Returns allowlist and blocklist for the authenticated user.
    
    **Flow:**
    1. Try Redis cache first (10-minute TTL)
    2. If not found, query Postgres
    3. Create default preferences if none exist
    
    **Response:**
    - `allowlist`: Sellers the user wants to bid on (if set, only these allowed)
    - `blocklist`: Sellers the user wants to avoid (always blocked)
    
    **Logic:**
    - If blocklisted ? bid blocked
    - If allowlist empty ? all sellers allowed (except blocklisted)
    - If allowlist set ? only allowlisted sellers allowed
    """
    user_id = current_user.get("id")
    team_id = current_user.get("team_id")
    
    if not user_id or not team_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID or Team ID not found in token"
        )
    
    try:
        prefs = await service.get_user_preferences(user_id, team_id)
        
        if not prefs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User preferences not found"
            )
        
        # Parse preferences
        if isinstance(prefs, dict):
            allowlist = prefs.get("allowlist", [])
            blocklist = prefs.get("blocklist", [])
            updated_at = prefs.get("updated_at")
        else:
            allowlist = prefs.allowlist
            blocklist = prefs.blocklist
            updated_at = prefs.updated_at.isoformat()
        
        # Parse seller lists
        allowlist_items = service.parse_seller_list(allowlist)
        blocklist_items = service.parse_seller_list(blocklist)
        
        return UserPreferencesResponse(
            user_id=user_id,
            team_id=team_id,
            allowlist=allowlist_items,
            blocklist=blocklist_items,
            updated_at=updated_at
        )
    
    except Exception as e:
        logger.error(f"Error fetching user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch preferences: {str(e)}"
        )


@router.post("/update", response_model=UpdatePreferenceResponse)
async def update_user_preference(
    request: UpdatePreferenceRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: UserPreferencesService = Depends(get_user_prefs_service)
):
    """
    Update user's seller preferences.
    
    **Actions:**
    - `add_allow`: Add seller to allowlist (removes from blocklist if present)
    - `remove_allow`: Remove seller from allowlist
    - `add_block`: Add seller to blocklist (removes from allowlist if present)
    - `remove_block`: Remove seller from blocklist
    
    **Flow:**
    1. Validate action
    2. Update database
    3. Clear Redis cache
    4. Emit `user_prefs.updated` event to event bus
    5. Return updated state
    
    **Integration:**
    - AutoBid Engine reads from Redis cache `user_prefs:{user_id}`
    - Bid decisions check seller against preferences
    """
    user_id = current_user.get("id")
    team_id = current_user.get("team_id")
    
    if not user_id or not team_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID or Team ID not found in token"
        )
    
    # Validate action
    valid_actions = ["add_allow", "remove_allow", "add_block", "remove_block"]
    if request.action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid action. Must be one of: {', '.join(valid_actions)}"
        )
    
    try:
        result = await service.update_user_preference(
            user_id=user_id,
            team_id=team_id,
            action=request.action,
            seller_id=request.seller_id,
            source=request.source,
            reason=request.reason
        )
        
        return UpdatePreferenceResponse(**result)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating user preferences: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update preferences: {str(e)}"
        )


@router.get("/check/{seller_id}")
async def check_seller_allowed(
    seller_id: str,
    source: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    service: UserPreferencesService = Depends(get_user_prefs_service)
):
    """
    Check if a seller is allowed for bidding.
    
    **Logic:**
    - If in blocklist ? denied
    - If allowlist is empty ? allowed (default allow)
    - If in allowlist ? allowed
    - Otherwise ? denied
    
    **Use Case:**
    - AutoBid Engine calls this before placing bids
    - Frontend can show allowed/blocked status
    """
    user_id = current_user.get("id")
    team_id = current_user.get("team_id")
    
    if not user_id or not team_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID or Team ID not found in token"
        )
    
    try:
        result = await service.check_seller_allowed(
            user_id=user_id,
            team_id=team_id,
            seller_id=seller_id,
            source=source
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error checking seller: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check seller: {str(e)}"
        )
