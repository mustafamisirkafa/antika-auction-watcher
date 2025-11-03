"""
User Preferences Models (Phase 14).
Manages seller allowlists and blocklists for AutoBid control.
"""
from typing import List, Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, JSON, Column
from sqlalchemy.dialects.postgresql import ARRAY, TEXT


class UserPreference(SQLModel, table=True):
    """
    User preferences for seller control.
    
    Manages per-user allowlist and blocklist for sellers.
    Integrated with AutoBid Engine for bid filtering.
    """
    __tablename__ = "user_preferences"
    
    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True, unique=True)
    team_id: int = Field(foreign_key="teams.id", index=True)
    
    # Seller lists (stored as JSON arrays)
    allowlist: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=[])
    )
    blocklist: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, default=[])
    )
    
    # Metadata
    notes: Optional[str] = Field(default=None, max_length=1000)
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        arbitrary_types_allowed = True


class SellerItem(SQLModel):
    """Seller item for API requests/responses."""
    seller_id: str = Field(max_length=200, description="Seller identifier")
    source: str = Field(max_length=50, description="Marketplace source (ebay, etsy, etc.)")
    reason: Optional[str] = Field(default=None, max_length=500, description="Reason for preference")


class UserPreferencesResponse(SQLModel):
    """Response model for GET /api/user/prefs."""
    user_id: int
    team_id: int
    allowlist: List[SellerItem]
    blocklist: List[SellerItem]
    updated_at: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "team_id": 1,
                "allowlist": [
                    {
                        "seller_id": "trusted-seller-001",
                        "source": "ebay",
                        "reason": "Highly reliable, consistent quality"
                    }
                ],
                "blocklist": [
                    {
                        "seller_id": "suspect-seller-042",
                        "source": "etsy",
                        "reason": "Low trust score, multiple failed transactions"
                    }
                ],
                "updated_at": "2025-11-03T12:00:00Z"
            }
        }


class UpdatePreferenceRequest(SQLModel):
    """Request model for POST /api/user/prefs/update."""
    action: str = Field(
        description="Action to perform",
        pattern="^(add_allow|remove_allow|add_block|remove_block)$"
    )
    seller_id: str = Field(max_length=200, description="Seller identifier")
    source: str = Field(max_length=50, description="Marketplace source")
    reason: Optional[str] = Field(default=None, max_length=500, description="Reason for preference")
    
    class Config:
        json_schema_extra = {
            "example": {
                "action": "add_block",
                "seller_id": "suspect-seller-042",
                "source": "etsy",
                "reason": "Low trust score, multiple failed transactions"
            }
        }


class UpdatePreferenceResponse(SQLModel):
    """Response model for POST /api/user/prefs/update."""
    success: bool
    message: str
    affected_list: str  # "allowlist" or "blocklist"
    seller_id: str
    new_total: int
    updated_at: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Seller added to blocklist",
                "affected_list": "blocklist",
                "seller_id": "suspect-seller-042",
                "new_total": 3,
                "updated_at": "2025-11-03T12:00:00Z"
            }
        }
