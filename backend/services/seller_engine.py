"""
Seller Analytics Engine (Phase 12).
Analyzes marketplace data on a per-seller basis.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from statistics import mean, stdev

logger = logging.getLogger(__name__)


class SellerEngine:
    """
    Seller analytics engine.
    
    Responsibilities:
    - Consume Phase 11 normalized_feed and historical listings
    - Aggregate data by seller_id
    - Compute behavioral metrics
    - Emit seller_metrics to event bus
    """
    
    def __init__(self, db, redis_client, event_bus):
        self.db = db
        self.redis = redis_client
        self.event_bus = event_bus
    
    async def analyze_seller(
        self, seller_id: str, source: str, lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze seller behavior and generate metrics.
        
        Args:
            seller_id: Seller identifier
            source: Marketplace source (ebay, etsy, etc.)
            lookback_days: Days of history to analyze
        
        Returns:
            Seller metrics dict
        """
        # Get seller's listings from cache/database
        listings = await self._get_seller_listings(seller_id, source, lookback_days)
        
        if not listings:
            logger.warning(f"No listings found for seller {seller_id} ({source})")
            return self._default_metrics(seller_id, source)
        
        # Calculate metrics
        metrics = {
            "seller_id": seller_id,
            "source": source,
            "listing_count": len(listings),
            "avg_start_price": self._calculate_avg_start_price(listings),
            "avg_final_price": self._calculate_avg_final_price(listings),
            "discount_rate": self._calculate_discount_rate(listings),
            "sale_speed": self._calculate_sale_speed(listings),
            "trend_alignment": self._calculate_trend_alignment(listings),
            "reliability_score": self._calculate_reliability_score(listings),
            "price_variance": self._calculate_price_variance(listings),
            "activity_score": self._calculate_activity_score(listings, lookback_days),
            "analyzed_at": datetime.utcnow().isoformat()
        }
        
        # Emit to event bus
        await self.event_bus.publish("seller.metrics", metrics)
        
        logger.info(
            f"Analyzed seller {seller_id} ({source}): "
            f"{len(listings)} listings, "
            f"discount={metrics['discount_rate']:.2%}, "
            f"trust={metrics['reliability_score']:.2f}"
        )
        
        return metrics
    
    async def analyze_all_sellers(
        self, source: Optional[str] = None, lookback_days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Analyze all sellers from market feed.
        
        Args:
            source: Filter by source (optional)
            lookback_days: Days of history
        
        Returns:
            List of seller metrics
        """
        # Get unique sellers from recent market feeds
        sellers = await self._get_active_sellers(source, lookback_days)
        
        results = []
        for seller_id, seller_source in sellers:
            try:
                metrics = await self.analyze_seller(
                    seller_id, seller_source, lookback_days
                )
                results.append(metrics)
            except Exception as e:
                logger.error(f"Error analyzing seller {seller_id}: {e}")
        
        logger.info(f"Analyzed {len(results)} sellers")
        return results
    
    async def _get_seller_listings(
        self, seller_id: str, source: str, lookback_days: int
    ) -> List[Dict[str, Any]]:
        """
        Get seller's listings from cache or database.
        
        Note: In production, this would query a listings table.
        For now, we'll use mock data.
        """
        # TODO: Query actual listings from database
        # For now, return mock listings
        
        # Generate deterministic mock data based on seller_id
        import random
        seed = hash(f"{seller_id}:{source}") % (2**32)
        rng = random.Random(seed)
        
        listing_count = rng.randint(5, 30)
        listings = []
        
        for i in range(listing_count):
            base_price = rng.uniform(500, 3000)
            discount = rng.uniform(0.05, 0.3)
            
            listings.append({
                "listing_id": f"{seller_id}-{i}",
                "seller_id": seller_id,
                "source": source,
                "start_price": base_price,
                "final_price": base_price * (1 - discount),
                "listed_at": datetime.utcnow() - timedelta(days=rng.randint(1, lookback_days)),
                "sold_at": datetime.utcnow() - timedelta(days=rng.randint(0, lookback_days - 1)),
                "category": rng.choice(["ceramics", "silver", "paintings", "furniture"])
            })
        
        return listings
    
    async def _get_active_sellers(
        self, source: Optional[str], lookback_days: int
    ) -> List[tuple]:
        """
        Get list of active sellers.
        
        Returns:
            List of (seller_id, source) tuples
        """
        # TODO: Query from market_feed cache or database
        # For now, return mock sellers
        
        mock_sellers = [
            ("seller_ebay_123", "ebay"),
            ("seller_ebay_456", "ebay"),
            ("seller_etsy_789", "etsy"),
            ("seller_sahibinden_111", "sahibinden"),
        ]
        
        if source:
            mock_sellers = [(sid, src) for sid, src in mock_sellers if src == source]
        
        return mock_sellers
    
    def _calculate_avg_start_price(self, listings: List[Dict[str, Any]]) -> float:
        """Calculate average starting price."""
        if not listings:
            return 0.0
        
        prices = [l["start_price"] for l in listings]
        return round(mean(prices), 2)
    
    def _calculate_avg_final_price(self, listings: List[Dict[str, Any]]) -> float:
        """Calculate average final/sold price."""
        if not listings:
            return 0.0
        
        prices = [l["final_price"] for l in listings]
        return round(mean(prices), 2)
    
    def _calculate_discount_rate(self, listings: List[Dict[str, Any]]) -> float:
        """
        Calculate average discount rate.
        
        discount_rate = (start_price - final_price) / start_price
        """
        if not listings:
            return 0.0
        
        discounts = []
        for listing in listings:
            start = listing["start_price"]
            final = listing["final_price"]
            
            if start > 0:
                discount = (start - final) / start
                discounts.append(discount)
        
        if not discounts:
            return 0.0
        
        return round(mean(discounts), 4)
    
    def _calculate_sale_speed(self, listings: List[Dict[str, Any]]) -> float:
        """
        Calculate average time to sale (in days).
        
        sale_speed = avg(sold_at - listed_at)
        """
        if not listings:
            return 0.0
        
        speeds = []
        for listing in listings:
            listed = listing.get("listed_at")
            sold = listing.get("sold_at")
            
            if listed and sold:
                delta = (sold - listed).total_seconds() / 86400  # Convert to days
                speeds.append(delta)
        
        if not speeds:
            return 0.0
        
        return round(mean(speeds), 2)
    
    def _calculate_trend_alignment(self, listings: List[Dict[str, Any]]) -> float:
        """
        Calculate how well seller's prices align with market trends.
        
        Higher = seller prices follow market trends closely
        Lower = seller has different pricing strategy
        """
        if len(listings) < 3:
            return 0.5  # Neutral if not enough data
        
        # TODO: Compare seller prices to market_value from ValuationFusion
        # For now, use simplified heuristic
        
        # Calculate price trend
        sorted_listings = sorted(listings, key=lambda x: x["listed_at"])
        prices = [l["final_price"] for l in sorted_listings]
        
        # Calculate correlation (simplified)
        if len(prices) > 1:
            # Positive trend = increasing prices
            deltas = [prices[i+1] - prices[i] for i in range(len(prices) - 1)]
            positive_deltas = sum(1 for d in deltas if d > 0)
            trend_alignment = positive_deltas / len(deltas)
        else:
            trend_alignment = 0.5
        
        return round(trend_alignment, 3)
    
    def _calculate_reliability_score(self, listings: List[Dict[str, Any]]) -> float:
        """
        Calculate seller reliability score (0-1).
        
        Factors:
        - Listing count (more = higher reliability)
        - Price consistency (lower variance = higher reliability)
        - Activity recency
        """
        if not listings:
            return 0.0
        
        # Listing count factor
        count_score = min(1.0, len(listings) / 20)  # Cap at 20 listings
        
        # Price consistency factor
        prices = [l["final_price"] for l in listings]
        if len(prices) > 1:
            avg_price = mean(prices)
            std = stdev(prices)
            cv = std / avg_price if avg_price > 0 else 1.0  # Coefficient of variation
            consistency_score = max(0.0, 1.0 - cv)
        else:
            consistency_score = 0.5
        
        # Activity recency factor
        now = datetime.utcnow()
        recent_count = sum(
            1 for l in listings
            if (now - l["listed_at"]).days <= 7
        )
        recency_score = min(1.0, recent_count / 5)
        
        # Weighted combination
        reliability = (
            count_score * 0.4 +
            consistency_score * 0.35 +
            recency_score * 0.25
        )
        
        return round(reliability, 3)
    
    def _calculate_price_variance(self, listings: List[Dict[str, Any]]) -> float:
        """Calculate price variance (coefficient of variation)."""
        if len(listings) < 2:
            return 0.0
        
        prices = [l["final_price"] for l in listings]
        avg_price = mean(prices)
        std = stdev(prices)
        
        if avg_price == 0:
            return 0.0
        
        cv = std / avg_price
        return round(cv, 4)
    
    def _calculate_activity_score(
        self, listings: List[Dict[str, Any]], lookback_days: int
    ) -> float:
        """
        Calculate seller activity score (0-1).
        
        Based on listing frequency and consistency.
        """
        if not listings:
            return 0.0
        
        # Frequency factor
        listings_per_week = len(listings) / (lookback_days / 7)
        frequency_score = min(1.0, listings_per_week / 5)  # Cap at 5/week
        
        # Consistency factor (check if listings are evenly distributed)
        if len(listings) > 1:
            # Group by week
            weeks = defaultdict(int)
            for listing in listings:
                week_num = (datetime.utcnow() - listing["listed_at"]).days // 7
                weeks[week_num] += 1
            
            # Calculate variance in weekly listings
            weekly_counts = list(weeks.values())
            if len(weekly_counts) > 1:
                avg_weekly = mean(weekly_counts)
                std_weekly = stdev(weekly_counts)
                consistency = max(0.0, 1.0 - (std_weekly / avg_weekly if avg_weekly > 0 else 1.0))
            else:
                consistency = 0.5
        else:
            consistency = 0.5
        
        activity_score = (
            frequency_score * 0.6 +
            consistency * 0.4
        )
        
        return round(activity_score, 3)
    
    def _default_metrics(self, seller_id: str, source: str) -> Dict[str, Any]:
        """Return default metrics when no data available."""
        return {
            "seller_id": seller_id,
            "source": source,
            "listing_count": 0,
            "avg_start_price": 0.0,
            "avg_final_price": 0.0,
            "discount_rate": 0.0,
            "sale_speed": 0.0,
            "trend_alignment": 0.5,
            "reliability_score": 0.0,
            "price_variance": 0.0,
            "activity_score": 0.0,
            "analyzed_at": datetime.utcnow().isoformat()
        }
