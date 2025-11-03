"""
Valuation Feed API Router (Phase 11).
Endpoints for dynamic market valuation.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session
from pydantic import BaseModel

from backend.db.database import get_session as get_db
from backend.routers.auth import get_current_user
from backend.middleware.team_context import get_team_context, TeamContext
from backend.db.models import User

router = APIRouter(prefix="/api/v1/valuation", tags=["valuation-feed"])


# === Pydantic Schemas ===

class MarketValueResponse(BaseModel):
    """Market valuation response."""
    item_id: str
    market_value: float
    demand_score: float
    trend_delta: float
    confidence: float
    sources: List[str]
    data_points: int
    timestamp: str
    fallback: bool = False


class RefreshRequest(BaseModel):
    """Valuation refresh request."""
    item_id: str
    category: str
    force: bool = False


class SourceInfo(BaseModel):
    """External feed source information."""
    name: str
    enabled: bool
    trust_score: float


# === Endpoints ===

@router.get("/live", response_model=MarketValueResponse)
async def get_live_valuation(
    item_id: str = Query(..., description="Item identifier"),
    category: str = Query(..., description="Item category"),
    team_context: TeamContext = Depends(get_team_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get live market valuation for item.
    
    Returns cached value if available, otherwise fetches fresh data.
    """
    # TODO: Integrate with ValuationCache
    # from backend.services.valuation_cache import valuation_cache
    # metrics = await valuation_cache.get_cached_valuation(item_id, category)
    
    # Mock response for now
    mock_metrics = {
        "item_id": item_id,
        "market_value": 1050.0,
        "demand_score": 0.75,
        "trend_delta": 0.05,
        "confidence": 0.82,
        "sources": ["ebay", "etsy", "internal"],
        "data_points": 5,
        "timestamp": "2025-11-02T12:00:00Z",
        "fallback": False
    }
    
    return mock_metrics


@router.post("/refresh", status_code=status.HTTP_200_OK)
async def refresh_valuation(
    request: RefreshRequest,
    team_context: TeamContext = Depends(get_team_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually trigger valuation refresh.
    
    Requires ANALYST+ role.
    """
    from backend.models.team_models import MemberRole
    
    # Check role
    if team_context.role not in [MemberRole.OWNER, MemberRole.ADMIN, MemberRole.ANALYST]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ANALYST, ADMIN, or OWNER can trigger valuation refresh"
        )
    
    # TODO: Integrate with ValuationCache
    # from backend.services.valuation_cache import valuation_cache
    # metrics = await valuation_cache.refresh_valuation(
    #     request.item_id, request.category, force=request.force
    # )
    
    return {
        "status": "refreshed",
        "item_id": request.item_id,
        "category": request.category,
        "forced": request.force,
        "message": "Valuation refresh triggered successfully"
    }


@router.get("/sources", response_model=List[SourceInfo])
async def list_feed_sources(
    team_context: TeamContext = Depends(get_team_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List available external feed sources.
    
    Returns source information including trust scores.
    """
    # TODO: Integrate with MarketFeed
    # from backend.services.market_feed import market_feed
    # stats = market_feed.get_stats()
    
    # Mock response
    sources = [
        {
            "name": "ebay",
            "enabled": True,
            "trust_score": 0.9
        },
        {
            "name": "etsy",
            "enabled": True,
            "trust_score": 0.85
        },
        {
            "name": "instagram",
            "enabled": True,
            "trust_score": 0.7
        },
        {
            "name": "sahibinden",
            "enabled": True,
            "trust_score": 0.8
        }
    ]
    
    return sources


@router.get("/health")
async def get_cache_health(
    team_context: TeamContext = Depends(get_team_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get valuation cache health status.
    
    Requires ADMIN+ role.
    """
    from backend.models.team_models import MemberRole
    
    # Check role
    if team_context.role not in [MemberRole.OWNER, MemberRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMIN or OWNER can view cache health"
        )
    
    # TODO: Integrate with ValuationCache
    # from backend.services.valuation_cache import valuation_cache
    # health = await valuation_cache.get_cache_health()
    
    # Mock response
    health = {
        "cached_items": 42,
        "backoff_items": 3,
        "total_tracked": 45,
        "failed_items": 1,
        "failure_rate": 0.022,
        "cache_ttl": 600,
        "status": "healthy"
    }
    
    return health
