"""
Seller Profile Builder (Phase 12).
Converts seller metrics into structured profiles.
"""
import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlmodel import Session, Field, SQLModel, select

logger = logging.getLogger(__name__)


class SellerProfile(SQLModel, table=True):
    """
    Seller profile model.
    
    Stores seller behavior analytics.
    """
    __tablename__ = "seller_profiles"
    
    id: int = Field(default=None, primary_key=True)
    seller_id: str = Field(index=True, max_length=200)
    source: str = Field(index=True, max_length=50)
    
    # Pricing metrics
    avg_discount: float = Field(default=0.0, ge=0, le=1)
    avg_start_price: float = Field(default=0.0, ge=0)
    avg_final_price: float = Field(default=0.0, ge=0)
    
    # Performance metrics
    avg_sale_speed: float = Field(default=0.0, ge=0)  # Days
    completion_rate: float = Field(default=0.0, ge=0, le=1)
    
    # Quality metrics
    trust_score: float = Field(default=0.5, ge=0, le=1, index=True)
    reliability_score: float = Field(default=0.5, ge=0, le=1)
    trend_alignment: float = Field(default=0.5, ge=0, le=1)
    
    # Activity metrics
    activity_score: float = Field(default=0.5, ge=0, le=1)
    listing_count: int = Field(default=0, ge=0)
    active_listings: int = Field(default=0, ge=0)
    
    # Metadata
    updated_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SellerProfileBuilder:
    """
    Builds and maintains seller profiles.
    
    Features:
    - Convert seller_metrics to profile
    - Store in Redis (24h TTL) + Postgres
    - Maintain 7-day rolling window
    - Update profiles daily
    """
    
    def __init__(self, db: Session, redis_client, event_bus):
        self.db = db
        self.redis = redis_client
        self.event_bus = event_bus
        self.cache_ttl = 86400  # 24 hours
        self.rolling_window_days = 7
    
    async def build_profile(
        self, seller_metrics: Dict[str, Any], save: bool = True
    ) -> SellerProfile:
        """
        Build seller profile from metrics.
        
        Args:
            seller_metrics: Metrics from SellerEngine
            save: Whether to save to database
        
        Returns:
            SellerProfile object
        """
        seller_id = seller_metrics.get("seller_id")
        source = seller_metrics.get("source")
        
        # Check for existing profile
        existing = self.db.exec(
            select(SellerProfile)
            .where(SellerProfile.seller_id == seller_id)
            .where(SellerProfile.source == source)
        ).first()
        
        if existing:
            # Update existing profile
            profile = self._update_profile(existing, seller_metrics)
        else:
            # Create new profile
            profile = self._create_profile(seller_metrics)
        
        if save:
            self.db.add(profile)
            self.db.commit()
            self.db.refresh(profile)
            
            # Also cache in Redis
            await self._cache_profile(profile)
            
            # Emit event
            await self.event_bus.publish("seller.profile_updated", {
                "seller_id": seller_id,
                "source": source,
                "trust_score": profile.trust_score,
                "activity_score": profile.activity_score
            })
        
        logger.info(f"Built profile for {seller_id} (trust={profile.trust_score:.2f})")
        
        return profile
    
    def _create_profile(self, metrics: Dict[str, Any]) -> SellerProfile:
        """Create new seller profile from metrics."""
        # Calculate activity score
        listing_count = metrics.get("listing_count", 0)
        activity_score = min(1.0, listing_count / 50)
        
        # Calculate trust score
        trust_score = self._calculate_trust_score(metrics)
        
        return SellerProfile(
            seller_id=metrics.get("seller_id"),
            source=metrics.get("source"),
            avg_discount=metrics.get("discount_rate", 0.0),
            avg_start_price=metrics.get("avg_start_price", 0.0),
            avg_final_price=metrics.get("avg_final_price", 0.0),
            avg_sale_speed=metrics.get("sale_speed", 0.0),
            completion_rate=self._calculate_completion_rate(metrics),
            trust_score=trust_score,
            reliability_score=metrics.get("reliability_score", 0.5),
            trend_alignment=metrics.get("trend_alignment", 0.5),
            activity_score=activity_score,
            listing_count=metrics.get("listing_count", 0),
            active_listings=metrics.get("active_listings", 0)
        )
    
    def _update_profile(
        self, profile: SellerProfile, metrics: Dict[str, Any]
    ) -> SellerProfile:
        """Update existing profile with new metrics (rolling average)."""
        # Use exponential moving average (alpha=0.3 for new data)
        alpha = 0.3
        
        profile.avg_discount = (
            alpha * metrics.get("discount_rate", 0.0) +
            (1 - alpha) * profile.avg_discount
        )
        
        profile.avg_start_price = (
            alpha * metrics.get("avg_start_price", 0.0) +
            (1 - alpha) * profile.avg_start_price
        )
        
        profile.avg_final_price = (
            alpha * metrics.get("avg_final_price", 0.0) +
            (1 - alpha) * profile.avg_final_price
        )
        
        profile.avg_sale_speed = (
            alpha * metrics.get("sale_speed", 0.0) +
            (1 - alpha) * profile.avg_sale_speed
        )
        
        profile.reliability_score = (
            alpha * metrics.get("reliability_score", 0.5) +
            (1 - alpha) * profile.reliability_score
        )
        
        profile.trend_alignment = (
            alpha * metrics.get("trend_alignment", 0.5) +
            (1 - alpha) * profile.trend_alignment
        )
        
        # Update counts (direct replacement)
        profile.listing_count = metrics.get("listing_count", profile.listing_count)
        profile.active_listings = metrics.get("active_listings", profile.active_listings)
        
        # Recalculate trust score
        profile.trust_score = self._calculate_trust_score(metrics, profile)
        
        # Update activity score
        profile.activity_score = min(1.0, profile.listing_count / 50)
        
        profile.updated_at = datetime.utcnow()
        
        return profile
    
    def _calculate_trust_score(
        self, metrics: Dict[str, Any], profile: Optional[SellerProfile] = None
    ) -> float:
        """
        Calculate seller trust score (0-1).
        
        Factors:
        - Reliability score
        - Trend alignment
        - Completion rate
        - Activity score
        """
        reliability = metrics.get("reliability_score", 0.5)
        trend_alignment = metrics.get("trend_alignment", 0.5)
        
        # Completion rate
        listing_count = metrics.get("listing_count", 0)
        active_count = metrics.get("active_listings", 0)
        sold_count = listing_count - active_count
        completion_rate = sold_count / listing_count if listing_count > 0 else 0.5
        
        # Activity score
        activity_score = min(1.0, listing_count / 50)
        
        # Weighted combination
        trust = (
            reliability * 0.35 +
            trend_alignment * 0.25 +
            completion_rate * 0.25 +
            activity_score * 0.15
        )
        
        return max(0.0, min(trust, 1.0))
    
    def _calculate_completion_rate(self, metrics: Dict[str, Any]) -> float:
        """Calculate listing completion rate."""
        listing_count = metrics.get("listing_count", 0)
        active_count = metrics.get("active_listings", 0)
        sold_count = listing_count - active_count
        
        return sold_count / listing_count if listing_count > 0 else 0.0
    
    async def _cache_profile(self, profile: SellerProfile):
        """Cache profile in Redis."""
        cache_key = f"seller:profile:{profile.seller_id}:{profile.source}"
        
        profile_dict = {
            "seller_id": profile.seller_id,
            "source": profile.source,
            "avg_discount": profile.avg_discount,
            "avg_sale_speed": profile.avg_sale_speed,
            "trust_score": profile.trust_score,
            "reliability_score": profile.reliability_score,
            "activity_score": profile.activity_score,
            "listing_count": profile.listing_count,
            "updated_at": profile.updated_at.isoformat()
        }
        
        await self.redis.setex(cache_key, self.cache_ttl, json.dumps(profile_dict))
        
        logger.debug(f"Cached profile for {profile.seller_id}")
    
    async def get_profile(
        self, seller_id: str, source: str
    ) -> Optional[SellerProfile]:
        """
        Get seller profile (from cache or database).
        
        Args:
            seller_id: Seller identifier
            source: Marketplace source
        
        Returns:
            SellerProfile or None
        """
        # Try cache first
        cache_key = f"seller:profile:{seller_id}:{source}"
        cached_data = await self.redis.get(cache_key)
        
        if cached_data:
            try:
                data = json.loads(cached_data)
                logger.debug(f"Cache hit for seller {seller_id}")
                # Return as dict (lightweight)
                return data
            except json.JSONDecodeError:
                logger.error(f"Invalid cached profile for {seller_id}")
        
        # Cache miss - query database
        profile = self.db.exec(
            select(SellerProfile)
            .where(SellerProfile.seller_id == seller_id)
            .where(SellerProfile.source == source)
        ).first()
        
        if profile:
            # Cache for future
            await self._cache_profile(profile)
        
        return profile
    
    async def get_top_sellers(
        self, source: str, metric: str = "trust_score", limit: int = 10
    ) -> List[SellerProfile]:
        """
        Get top sellers by metric.
        
        Args:
            source: Marketplace source
            metric: Metric to sort by (trust_score, activity_score, etc.)
            limit: Number of results
        
        Returns:
            List of top seller profiles
        """
        # Validate metric
        valid_metrics = [
            "trust_score", "activity_score", "reliability_score",
            "trend_alignment", "avg_discount", "listing_count"
        ]
        
        if metric not in valid_metrics:
            metric = "trust_score"
        
        # Query database
        query = select(SellerProfile).where(SellerProfile.source == source)
        
        # Order by metric (descending)
        if metric == "trust_score":
            query = query.order_by(SellerProfile.trust_score.desc())
        elif metric == "activity_score":
            query = query.order_by(SellerProfile.activity_score.desc())
        elif metric == "reliability_score":
            query = query.order_by(SellerProfile.reliability_score.desc())
        elif metric == "listing_count":
            query = query.order_by(SellerProfile.listing_count.desc())
        
        query = query.limit(limit)
        
        profiles = self.db.exec(query).all()
        
        return profiles
    
    async def cleanup_stale_profiles(self, days: int = 30):
        """Clean up profiles not updated in X days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        stale_profiles = self.db.exec(
            select(SellerProfile)
            .where(SellerProfile.updated_at < cutoff)
        ).all()
        
        for profile in stale_profiles:
            self.db.delete(profile)
        
        self.db.commit()
        
        logger.info(f"Cleaned up {len(stale_profiles)} stale seller profiles")
        
        return len(stale_profiles)
