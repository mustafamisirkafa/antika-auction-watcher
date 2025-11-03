"""
User Preferences Service (Phase 14).
CRUD operations for seller allowlist/blocklist management.
"""
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlmodel import Session, select

from backend.models.user_prefs import UserPreference, SellerItem

logger = logging.getLogger(__name__)


class UserPreferencesService:
    """
    User preferences service.
    
    Features:
    - CRUD operations for user preferences
    - Redis caching with 10-minute TTL
    - Event bus integration
    """
    
    def __init__(self, db: Session, redis_client, event_bus):
        self.db = db
        self.redis = redis_client
        self.event_bus = event_bus
        self.cache_ttl = 600  # 10 minutes
    
    async def get_user_preferences(
        self, user_id: int, team_id: int
    ) -> Optional[UserPreference]:
        """
        Get user preferences (from cache or database).
        
        Args:
            user_id: User ID
            team_id: Team ID (for verification)
        
        Returns:
            UserPreference or None
        """
        # Try cache first
        cache_key = f"user_prefs:{user_id}"
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            try:
                data = json.loads(cached_data)
                logger.debug(f"Cache hit for user preferences {user_id}")
                return data
            except json.JSONDecodeError:
                logger.error(f"Invalid cached preferences for user {user_id}")
        
        # Cache miss - query database
        prefs = self.db.exec(
            select(UserPreference)
            .where(UserPreference.user_id == user_id)
            .where(UserPreference.team_id == team_id)
        ).first()
        
        if prefs:
            # Cache for future
            await self._cache_preferences(prefs)
        else:
            # Create default preferences
            prefs = UserPreference(
                user_id=user_id,
                team_id=team_id,
                allowlist=[],
                blocklist=[]
            )
            self.db.add(prefs)
            self.db.commit()
            self.db.refresh(prefs)
            
            # Cache the new preferences
            await self._cache_preferences(prefs)
            
            logger.info(f"Created default preferences for user {user_id}")
        
        return prefs
    
    async def update_user_preference(
        self,
        user_id: int,
        team_id: int,
        action: str,
        seller_id: str,
        source: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update user preferences (add/remove from allowlist/blocklist).
        
        Args:
            user_id: User ID
            team_id: Team ID
            action: "add_allow", "remove_allow", "add_block", "remove_block"
            seller_id: Seller identifier
            source: Marketplace source
            reason: Optional reason for preference
        
        Returns:
            Update result dict
        """
        # Get current preferences
        prefs = await self.get_user_preferences(user_id, team_id)
        
        if not prefs:
            raise ValueError(f"Preferences not found for user {user_id}")
        
        # Convert to dict if from cache
        if isinstance(prefs, dict):
            # Re-fetch from database for modification
            prefs = self.db.exec(
                select(UserPreference)
                .where(UserPreference.user_id == user_id)
                .where(UserPreference.team_id == team_id)
            ).first()
        
        # Create seller item key
        seller_key = f"{seller_id}:{source}"
        
        # Perform action
        affected_list = ""
        message = ""
        
        if action == "add_allow":
            if seller_key not in prefs.allowlist:
                prefs.allowlist.append(seller_key)
                # Remove from blocklist if present
                if seller_key in prefs.blocklist:
                    prefs.blocklist.remove(seller_key)
                message = "Seller added to allowlist"
            else:
                message = "Seller already in allowlist"
            affected_list = "allowlist"
        
        elif action == "remove_allow":
            if seller_key in prefs.allowlist:
                prefs.allowlist.remove(seller_key)
                message = "Seller removed from allowlist"
            else:
                message = "Seller not in allowlist"
            affected_list = "allowlist"
        
        elif action == "add_block":
            if seller_key not in prefs.blocklist:
                prefs.blocklist.append(seller_key)
                # Remove from allowlist if present
                if seller_key in prefs.allowlist:
                    prefs.allowlist.remove(seller_key)
                message = "Seller added to blocklist"
            else:
                message = "Seller already in blocklist"
            affected_list = "blocklist"
        
        elif action == "remove_block":
            if seller_key in prefs.blocklist:
                prefs.blocklist.remove(seller_key)
                message = "Seller removed from blocklist"
            else:
                message = "Seller not in blocklist"
            affected_list = "blocklist"
        
        else:
            raise ValueError(f"Invalid action: {action}")
        
        # Update timestamp
        prefs.updated_at = datetime.utcnow()
        
        # Save to database
        self.db.add(prefs)
        self.db.commit()
        self.db.refresh(prefs)
        
        # Clear cache
        await self._clear_cache(user_id)
        
        # Cache updated preferences
        await self._cache_preferences(prefs)
        
        # Emit event
        await self.event_bus.publish("user_prefs.updated", {
            "user_id": user_id,
            "team_id": team_id,
            "action": action,
            "seller_id": seller_id,
            "source": source,
            "affected_list": affected_list,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        logger.info(
            f"User {user_id} preferences updated: {action} {seller_id} ({source})"
        )
        
        # Return result
        new_total = (
            len(prefs.allowlist) if affected_list == "allowlist"
            else len(prefs.blocklist)
        )
        
        return {
            "success": True,
            "message": message,
            "affected_list": affected_list,
            "seller_id": seller_id,
            "new_total": new_total,
            "updated_at": prefs.updated_at.isoformat()
        }
    
    async def check_seller_allowed(
        self, user_id: int, team_id: int, seller_id: str, source: str
    ) -> Dict[str, Any]:
        """
        Check if a seller is allowed for bidding.
        
        Logic:
        - If in blocklist ? denied
        - If allowlist is empty ? allowed (default allow)
        - If in allowlist ? allowed
        - Otherwise ? denied
        
        Args:
            user_id: User ID
            team_id: Team ID
            seller_id: Seller identifier
            source: Marketplace source
        
        Returns:
            {"allowed": bool, "reason": str}
        """
        prefs = await self.get_user_preferences(user_id, team_id)
        
        if not prefs:
            return {"allowed": True, "reason": "No preferences set"}
        
        # Extract lists
        if isinstance(prefs, dict):
            allowlist = prefs.get("allowlist", [])
            blocklist = prefs.get("blocklist", [])
        else:
            allowlist = prefs.allowlist
            blocklist = prefs.blocklist
        
        seller_key = f"{seller_id}:{source}"
        
        # Check blocklist first
        if seller_key in blocklist:
            return {"allowed": False, "reason": "Seller is blocklisted"}
        
        # If allowlist is empty, allow by default
        if not allowlist:
            return {"allowed": True, "reason": "No allowlist restrictions"}
        
        # If allowlist exists, check membership
        if seller_key in allowlist:
            return {"allowed": True, "reason": "Seller is allowlisted"}
        
        return {"allowed": False, "reason": "Seller not in allowlist"}
    
    async def _cache_preferences(self, prefs: UserPreference):
        """Cache preferences in Redis."""
        cache_key = f"user_prefs:{prefs.user_id}"
        
        prefs_dict = {
            "user_id": prefs.user_id,
            "team_id": prefs.team_id,
            "allowlist": prefs.allowlist,
            "blocklist": prefs.blocklist,
            "updated_at": prefs.updated_at.isoformat()
        }
        
        await self.redis.setex(cache_key, self.cache_ttl, json.dumps(prefs_dict))
        
        logger.debug(f"Cached preferences for user {prefs.user_id}")
    
    async def _clear_cache(self, user_id: int):
        """Clear cached preferences."""
        cache_key = f"user_prefs:{user_id}"
        await self.redis.delete(cache_key)
        
        logger.debug(f"Cleared cache for user {user_id}")
    
    def parse_seller_list(
        self, seller_keys: List[str]
    ) -> List[SellerItem]:
        """
        Parse seller list from storage format to API format.
        
        Args:
            seller_keys: List of "seller_id:source" strings
        
        Returns:
            List of SellerItem objects
        """
        items = []
        
        for key in seller_keys:
            try:
                seller_id, source = key.split(":", 1)
                items.append(SellerItem(
                    seller_id=seller_id,
                    source=source,
                    reason=None  # Reason not stored in Phase 14.0
                ))
            except ValueError:
                logger.warning(f"Invalid seller key format: {key}")
        
        return items
