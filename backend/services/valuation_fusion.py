"""
DataFusion Core (Phase 11).
Merges internal bid cache + external market feed.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from statistics import mean, median

logger = logging.getLogger(__name__)


class ValuationFusion:
    """
    Data fusion engine for market valuation.
    
    Merges:
    - Internal bid cache (Phase 9 ProfitEstimate)
    - External market feed (Phase 11 normalized_feed)
    
    Produces:
    - market_value: Fused price estimate
    - demand_score: 0-1 score indicating market demand
    - trend_delta: % change over time
    """
    
    def __init__(self, db, redis_client):
        self.db = db
        self.redis = redis_client
    
    async def fuse_market_data(
        self,
        item_id: str,
        category: str,
        internal_estimate: Optional[Dict[str, Any]] = None,
        external_feeds: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Fuse internal and external market data.
        
        Args:
            item_id: Item identifier
            category: Item category
            internal_estimate: Phase 9 ProfitEstimate data
            external_feeds: List of normalized market feeds
        
        Returns:
            Fused metrics: {
                market_value: float,
                demand_score: float,
                trend_delta: float,
                confidence: float,
                sources: list
            }
        """
        # Collect all price points with weights
        price_points = []
        
        # Add internal estimate (if available)
        if internal_estimate:
            price_points.append({
                "price": internal_estimate.get("estimated_value", 0),
                "weight": self._calculate_internal_weight(internal_estimate),
                "source": "internal",
                "timestamp": internal_estimate.get("created_at", datetime.utcnow())
            })
        
        # Add external feeds
        if external_feeds:
            for feed in external_feeds:
                price_points.append({
                    "price": feed.get("price", 0),
                    "weight": self._calculate_external_weight(feed, category),
                    "source": feed.get("source", "unknown"),
                    "timestamp": self._parse_timestamp(feed.get("timestamp"))
                })
        
        if not price_points:
            logger.warning(f"No price points for item {item_id}")
            return self._fallback_metrics()
        
        # Calculate weighted market value
        market_value = self._weighted_average(price_points)
        
        # Calculate demand score
        demand_score = self._calculate_demand_score(price_points, external_feeds or [])
        
        # Calculate trend delta
        trend_delta = await self._calculate_trend_delta(item_id, market_value)
        
        # Calculate confidence
        confidence = self._calculate_fusion_confidence(price_points, internal_estimate)
        
        # Track sources
        sources = list(set(p["source"] for p in price_points))
        
        fused_metrics = {
            "market_value": round(market_value, 2),
            "demand_score": round(demand_score, 3),
            "trend_delta": round(trend_delta, 4),
            "confidence": round(confidence, 3),
            "sources": sources,
            "data_points": len(price_points),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(
            f"Fused valuation for {item_id}: market_value={market_value:.2f}, "
            f"demand={demand_score:.2f}, trend={trend_delta:+.2%}, "
            f"sources={sources}"
        )
        
        return fused_metrics
    
    def _calculate_internal_weight(self, estimate: Dict[str, Any]) -> float:
        """
        Calculate weight for internal estimate.
        
        Factors:
        - Confidence score
        - Recency
        - Sample size
        """
        base_weight = 1.5  # Internal data is trusted more
        
        # Confidence factor
        confidence = estimate.get("confidence", 0.5)
        confidence_factor = confidence
        
        # Recency factor (decay over time)
        created_at = estimate.get("created_at", datetime.utcnow())
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        
        age_hours = (datetime.utcnow() - created_at.replace(tzinfo=None)).total_seconds() / 3600
        recency_factor = max(0.5, 1.0 - (age_hours / 48))  # Decay over 48h
        
        return base_weight * confidence_factor * recency_factor
    
    def _calculate_external_weight(
        self, feed: Dict[str, Any], category: str
    ) -> float:
        """
        Calculate weight for external feed.
        
        Factors:
        - Trust score
        - Condition score
        - Category match
        - Recency
        """
        base_weight = 1.0
        
        # Trust score (source reliability ? seller rating)
        trust_score = feed.get("trust_score", 0.5)
        
        # Condition score
        condition_score = feed.get("condition_score", 0.75)
        
        # Category match (exact match gets boost)
        feed_category = feed.get("category", "").lower()
        category_match = 1.2 if feed_category == category.lower() else 1.0
        
        # Recency factor
        timestamp = self._parse_timestamp(feed.get("timestamp"))
        age_hours = (datetime.utcnow() - timestamp).total_seconds() / 3600
        recency_factor = max(0.3, 1.0 - (age_hours / 24))  # Decay over 24h
        
        return base_weight * trust_score * condition_score * category_match * recency_factor
    
    def _weighted_average(self, price_points: List[Dict[str, Any]]) -> float:
        """Calculate weighted average price."""
        if not price_points:
            return 0.0
        
        total_weighted = sum(p["price"] * p["weight"] for p in price_points)
        total_weight = sum(p["weight"] for p in price_points)
        
        if total_weight == 0:
            return 0.0
        
        return total_weighted / total_weight
    
    def _calculate_demand_score(
        self, price_points: List[Dict[str, Any]], external_feeds: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate demand score (0-1).
        
        Factors:
        - Number of listings (more = higher demand)
        - Price variance (lower = higher demand)
        - Recency (newer = higher demand)
        """
        if not price_points:
            return 0.5
        
        # Listing count factor (normalized)
        listing_count = len(external_feeds)
        count_score = min(1.0, listing_count / 10)  # Cap at 10 listings
        
        # Price variance factor (inverse)
        if len(price_points) > 1:
            prices = [p["price"] for p in price_points]
            avg_price = mean(prices)
            variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
            std_dev = variance ** 0.5
            cv = std_dev / avg_price if avg_price > 0 else 1.0  # Coefficient of variation
            variance_score = max(0.0, 1.0 - cv)
        else:
            variance_score = 0.5
        
        # Recency factor
        now = datetime.utcnow()
        recent_count = sum(
            1 for p in price_points
            if (now - p["timestamp"]).total_seconds() < 3600  # Last hour
        )
        recency_score = min(1.0, recent_count / 5)
        
        # Weighted combination
        demand_score = (
            count_score * 0.4 +
            variance_score * 0.3 +
            recency_score * 0.3
        )
        
        return demand_score
    
    async def _calculate_trend_delta(self, item_id: str, current_value: float) -> float:
        """
        Calculate trend delta (% change from previous value).
        
        Args:
            item_id: Item identifier
            current_value: Current market value
        
        Returns:
            Trend delta as decimal (e.g., 0.05 = 5% increase)
        """
        # Get previous value from Redis
        key = f"trend:{item_id}"
        previous_data = await self.redis.get(key)
        
        if previous_data:
            try:
                previous_value = float(previous_data)
                if previous_value > 0:
                    delta = (current_value - previous_value) / previous_value
                else:
                    delta = 0.0
            except (ValueError, TypeError):
                delta = 0.0
        else:
            delta = 0.0
        
        # Store current value for next calculation
        await self.redis.setex(key, 86400, str(current_value))  # 24h TTL
        
        return delta
    
    def _calculate_fusion_confidence(
        self, price_points: List[Dict[str, Any]], internal_estimate: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calculate confidence in fused valuation.
        
        Factors:
        - Number of data sources
        - Internal estimate confidence (if available)
        - Weight distribution
        """
        # Base confidence from data point count
        count_confidence = min(1.0, len(price_points) / 5)
        
        # Internal confidence (if available)
        internal_confidence = internal_estimate.get("confidence", 0.5) if internal_estimate else 0.5
        
        # Weight distribution (more even = higher confidence)
        if len(price_points) > 1:
            weights = [p["weight"] for p in price_points]
            total_weight = sum(weights)
            weight_variance = sum((w / total_weight - 1 / len(weights)) ** 2 for w in weights)
            distribution_confidence = max(0.5, 1.0 - weight_variance)
        else:
            distribution_confidence = 0.5
        
        # Combined confidence
        confidence = (
            count_confidence * 0.3 +
            internal_confidence * 0.4 +
            distribution_confidence * 0.3
        )
        
        return confidence
    
    def _parse_timestamp(self, ts: Any) -> datetime:
        """Parse timestamp to datetime."""
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except:
                pass
        return datetime.utcnow()
    
    def _fallback_metrics(self) -> Dict[str, Any]:
        """Return fallback metrics when no data available."""
        return {
            "market_value": 0.0,
            "demand_score": 0.5,
            "trend_delta": 0.0,
            "confidence": 0.0,
            "sources": [],
            "data_points": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
