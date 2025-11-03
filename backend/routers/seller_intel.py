"""
Seller Intelligence API (Phase 12).
API endpoints for seller analytics and profiles.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session
from pydantic import BaseModel

from backend.db.database import get_db
from backend.services.seller_engine import SellerEngine
from backend.services.seller_profile import SellerProfileBuilder, SellerProfile
from backend.services.event_bus import EventBus
from backend.middleware.team_context import require_role, get_redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sellers", tags=["seller-intelligence"])


# Response models
class SellerProfileResponse(BaseModel):
    """Seller profile response schema."""
    seller_id: str
    source: str
    avg_discount: float
    avg_start_price: float
    avg_final_price: float
    avg_sale_speed: float
    completion_rate: float
    trust_score: float
    reliability_score: float
    trend_alignment: float
    activity_score: float
    listing_count: int
    active_listings: int
    updated_at: str


class SellerMetricsResponse(BaseModel):
    """Seller metrics response schema."""
    seller_id: str
    source: str
    avg_start_price: float
    avg_final_price: float
    discount_rate: float
    sale_speed: float
    trend_alignment: float
    reliability_score: float
    listing_count: int
    active_listings: int
    timestamp: str


class TrendSummaryResponse(BaseModel):
    """Market-wide seller trend summary."""
    source: str
    total_sellers: int
    avg_trust_score: float
    avg_discount_rate: float
    avg_sale_speed: float
    top_categories: List[str]
    timestamp: str


# Dependency injection
async def get_seller_engine(
    db: Session = Depends(get_db),
    redis = Depends(get_redis)
) -> SellerEngine:
    """Get SellerEngine instance."""
    event_bus = EventBus(redis)
    return SellerEngine(db, redis, event_bus)


async def get_profile_builder(
    db: Session = Depends(get_db),
    redis = Depends(get_redis)
) -> SellerProfileBuilder:
    """Get SellerProfileBuilder instance."""
    event_bus = EventBus(redis)
    return SellerProfileBuilder(db, redis, event_bus)


@router.get("/{seller_id}", response_model=SellerProfileResponse)
async def get_seller_profile(
    seller_id: str,
    source: str = Query(..., description="Marketplace source (ebay, etsy, etc.)"),
    builder: SellerProfileBuilder = Depends(get_profile_builder)
):
    """
    Get detailed seller profile.
    
    Returns seller behavior analytics including:
    - Pricing strategy (avg discount, start/final prices)
    - Performance (sale speed, completion rate)
    - Quality scores (trust, reliability, trend alignment)
    - Activity metrics
    """
    profile = await builder.get_profile(seller_id, source)
    
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Seller profile not found: {seller_id}"
        )
    
    # Convert to dict if SQLModel object
    if isinstance(profile, SellerProfile):
        return SellerProfileResponse(
            seller_id=profile.seller_id,
            source=profile.source,
            avg_discount=profile.avg_discount,
            avg_start_price=profile.avg_start_price,
            avg_final_price=profile.avg_final_price,
            avg_sale_speed=profile.avg_sale_speed,
            completion_rate=profile.completion_rate,
            trust_score=profile.trust_score,
            reliability_score=profile.reliability_score,
            trend_alignment=profile.trend_alignment,
            activity_score=profile.activity_score,
            listing_count=profile.listing_count,
            active_listings=profile.active_listings,
            updated_at=profile.updated_at.isoformat()
        )
    else:
        # From cache (already dict)
        return SellerProfileResponse(**profile)


@router.get("/top", response_model=List[SellerProfileResponse])
async def get_top_sellers(
    source: str = Query(..., description="Marketplace source"),
    metric: str = Query(
        "trust_score",
        description="Metric to rank by (trust_score, activity_score, etc.)"
    ),
    limit: int = Query(10, ge=1, le=100, description="Number of results"),
    builder: SellerProfileBuilder = Depends(get_profile_builder)
):
    """
    Get top sellers by metric.
    
    Supported metrics:
    - trust_score: Overall seller trustworthiness
    - activity_score: Seller activity level
    - reliability_score: Consistency and reliability
    - trend_alignment: Alignment with market trends
    - listing_count: Total listings
    """
    profiles = await builder.get_top_sellers(source, metric, limit)
    
    return [
        SellerProfileResponse(
            seller_id=p.seller_id,
            source=p.source,
            avg_discount=p.avg_discount,
            avg_start_price=p.avg_start_price,
            avg_final_price=p.avg_final_price,
            avg_sale_speed=p.avg_sale_speed,
            completion_rate=p.completion_rate,
            trust_score=p.trust_score,
            reliability_score=p.reliability_score,
            trend_alignment=p.trend_alignment,
            activity_score=p.activity_score,
            listing_count=p.listing_count,
            active_listings=p.active_listings,
            updated_at=p.updated_at.isoformat()
        )
        for p in profiles
    ]


@router.get("/trends", response_model=TrendSummaryResponse)
async def get_market_trends(
    source: str = Query(..., description="Marketplace source"),
    builder: SellerProfileBuilder = Depends(get_profile_builder),
    db: Session = Depends(get_db)
):
    """
    Get market-wide seller trend summary.
    
    Returns aggregated statistics across all sellers in the market.
    """
    from sqlmodel import select, func
    from datetime import datetime
    
    # Query aggregate statistics
    result = db.exec(
        select(
            func.count(SellerProfile.id).label("total"),
            func.avg(SellerProfile.trust_score).label("avg_trust"),
            func.avg(SellerProfile.avg_discount).label("avg_discount"),
            func.avg(SellerProfile.avg_sale_speed).label("avg_speed")
        ).where(SellerProfile.source == source)
    ).first()
    
    total_sellers = result.total if result else 0
    avg_trust = result.avg_trust if result and result.avg_trust else 0.0
    avg_discount = result.avg_discount if result and result.avg_discount else 0.0
    avg_speed = result.avg_speed if result and result.avg_speed else 0.0
    
    # TODO: Query top categories from listings
    top_categories = ["ceramics", "silver", "paintings"]
    
    return TrendSummaryResponse(
        source=source,
        total_sellers=total_sellers,
        avg_trust_score=avg_trust,
        avg_discount_rate=avg_discount,
        avg_sale_speed=avg_speed,
        top_categories=top_categories,
        timestamp=datetime.utcnow().isoformat()
    )


@router.post("/refresh", dependencies=[Depends(require_role("ADMIN"))])
async def refresh_seller_analysis(
    source: str = Query(..., description="Marketplace source"),
    seller_id: Optional[str] = Query(None, description="Specific seller (or all if omitted)"),
    engine: SellerEngine = Depends(get_seller_engine),
    builder: SellerProfileBuilder = Depends(get_profile_builder)
):
    """
    Manually trigger seller analysis refresh.
    
    **Requires ADMIN role.**
    
    Analyzes seller(s) and updates profiles.
    """
    if seller_id:
        # Analyze single seller
        metrics = await engine.analyze_seller(seller_id, source)
        profile = await builder.build_profile(metrics)
        
        return {
            "status": "success",
            "seller_id": seller_id,
            "trust_score": profile.trust_score if isinstance(profile, SellerProfile) else profile.get("trust_score"),
            "updated_at": profile.updated_at.isoformat() if isinstance(profile, SellerProfile) else profile.get("updated_at")
        }
    else:
        # Analyze all sellers in market
        metrics_list = await engine.analyze_market_sellers(source)
        
        profiles = []
        for metrics in metrics_list:
            profile = await builder.build_profile(metrics)
            profiles.append(profile)
        
        return {
            "status": "success",
            "analyzed_sellers": len(profiles),
            "source": source
        }


@router.get("/metrics/{seller_id}", response_model=SellerMetricsResponse)
async def get_seller_metrics(
    seller_id: str,
    source: str = Query(..., description="Marketplace source"),
    lookback_days: int = Query(30, ge=7, le=365, description="Historical window (days)"),
    engine: SellerEngine = Depends(get_seller_engine)
):
    """
    Get real-time seller metrics.
    
    Computes fresh metrics from historical data (not cached).
    Useful for deep-dive analysis.
    """
    metrics = await engine.analyze_seller(seller_id, source, lookback_days)
    
    return SellerMetricsResponse(**metrics)


@router.delete("/profiles/cleanup", dependencies=[Depends(require_role("ADMIN"))])
async def cleanup_stale_profiles(
    days: int = Query(30, ge=7, le=365, description="Delete profiles older than X days"),
    builder: SellerProfileBuilder = Depends(get_profile_builder)
):
    """
    Clean up stale seller profiles.
    
    **Requires ADMIN role.**
    
    Deletes profiles not updated within the specified window.
    """
    deleted_count = await builder.cleanup_stale_profiles(days)
    
    return {
        "status": "success",
        "deleted_profiles": deleted_count,
        "cutoff_days": days
    }
