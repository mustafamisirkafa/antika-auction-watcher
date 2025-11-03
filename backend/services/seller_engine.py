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
    - Aggregate market feed data by seller
    - Compute seller-specific metrics
    - Analyze pricing strategies and behavior
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
        Analyze a single seller's behavior.
        
        Args:
            seller_id: Seller identifier
            source: Marketplace source (ebay, etsy, etc.)
            lookback_days: Historical window (days)
        
        Returns:
            Seller metrics dict
        """
        # Get seller's historical listings
        listings = await self._get_seller_listings(seller_id, source, lookback_days)
        
        if not listings:
            logger.warning(f"No listings found for seller {seller_id}")
            return self._empty_metrics(seller_id, source)
        
        # Calculate metrics
        metrics = {
            "seller_id": seller_id,
            "source": source,
            "avg_start_price": self._calculate_avg_start_price(listings),
            "avg_final_price": self._calculate_avg_final_price(listings),
            "discount_rate": self._calculate_discount_rate(listings),
            "sale_speed": self._calculate_sale_speed(listings),
            "trend_alignment": self._calculate_trend_alignment(listings),
            "reliability_score": self._calculate_reliability_score(listings),
            "listing_count": len(listings),
            "active_listings": sum(1 for l in listings if l.get("status") == "active"),
            "avg_condition_score": mean(l.get("condition_score", 0.75) for l in listings),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Emit to event bus
        await self.event_bus.publish("seller.metrics", metrics)
        
        logger.info(
            f"Analyzed seller {seller_id}: {len(listings)} listings, "
            f"discount={metrics['discount_rate']:.1%}, "
            f"reliability={metrics['reliability_score']:.2f}"
        )
        
        return metrics
    
    async def analyze_sellers_batch(
        self, seller_ids: List[str], source: str, lookback_days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple sellers in batch.
        
        Args:
            seller_ids: List of seller identifiers
            source: Marketplace source
            lookback_days: Historical window (days)
        
        Returns:
            List of seller metrics
        """
        import asyncio
        
        tasks = [
            self.analyze_seller(seller_id, source, lookback_days)
            for seller_id in seller_ids
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out errors
        metrics_list = [
            r for r in results
            if not isinstance(r, Exception)
        ]
        
        logger.info(f"Batch analyzed {len(metrics_list)} sellers")
        
        return metrics_list
    
    async def _get_seller_listings(
        self, seller_id: str, source: str, lookback_days: int
    ) -> List[Dict[str, Any]]:
        """
        Get seller's historical listings.
        
        Note: In production, query from database or external API.
        This is a mock implementation.
        """
        # TODO: Query actual seller listing history
        # For now, generate mock data
        
        import random
        random.seed(hash(seller_id))  # Deterministic
        
        listing_count = random.randint(5, 50)
        listings = []
        
        for i in range(listing_count):
            base_price = random.uniform(500, 2000)
            discount = random.uniform(0, 0.3)
            
            listing = {
                "listing_id": f"{seller_id}-{i}",
                "seller_id": seller_id,
                "source": source,
                "start_price": base_price,
                "final_price": base_price * (1 - discount),
                "condition_score": random.uniform(0.7, 1.0),
                "listed_date": datetime.utcnow() - timedelta(days=random.randint(0, lookback_days)),
                "sold_date": datetime.utcnow() - timedelta(days=random.randint(0, lookback_days)),
                "status": random.choice(["sold", "sold", "active", "expired"]),
                "category": random.choice(["ceramics", "silver", "paintings", "furniture"])
            }
            
            # Calculate days to sale
            if listing["status"] == "sold":
                listing["days_to_sale"] = (listing["sold_date"] - listing["listed_date"]).days
            
            listings.append(listing)
        
        return listings
    
    def _calculate_avg_start_price(self, listings: List[Dict[str, Any]]) -> float:
        """Calculate average starting price."""
        prices = [l.get("start_price", 0) for l in listings if l.get("start_price")]
        return mean(prices) if prices else 0.0
    
    def _calculate_avg_final_price(self, listings: List[Dict[str, Any]]) -> float:
        """Calculate average final/sold price."""
        sold_listings = [l for l in listings if l.get("status") == "sold"]
        prices = [l.get("final_price", 0) for l in sold_listings if l.get("final_price")]
        return mean(prices) if prices else 0.0
    
    def _calculate_discount_rate(self, listings: List[Dict[str, Any]]) -> float:
        """
        Calculate average discount rate (%).
        
        discount_rate = (start_price - final_price) / start_price
        """
        discounts = []
        
        for listing in listings:
            if listing.get("status") == "sold":
                start = listing.get("start_price", 0)
                final = listing.get("final_price", 0)
                
                if start > 0:
                    discount = (start - final) / start
                    discounts.append(discount)
        
        return mean(discounts) if discounts else 0.0
    
    def _calculate_sale_speed(self, listings: List[Dict[str, Any]]) -> float:
        """
        Calculate average days to sale.
        
        Lower = faster sales = higher demand for seller's items
        """
        sold_listings = [
            l for l in listings
            if l.get("status") == "sold" and l.get("days_to_sale") is not None
        ]
        
        if not sold_listings:
            return 0.0
        
        speeds = [l["days_to_sale"] for l in sold_listings]
        return mean(speeds)
    
    def _calculate_trend_alignment(self, listings: List[Dict[str, Any]]) -> float:
        """
        Calculate how well seller aligns with market trends.
        
        Compares seller's pricing to market average over time.
        
        Returns:
            Alignment score (0-1, 1 = perfect alignment)
        """
        # TODO: Compare with market trends from Phase 11
        # For now, use simplified calculation
        
        sold_listings = [l for l in listings if l.get("status") == "sold"]
        
        if len(sold_listings) < 3:
            return 0.5  # Not enough data
        
        # Check price consistency
        prices = [l.get("final_price", 0) for l in sold_listings]
        
        if mean(prices) == 0:
            return 0.5
        
        # Calculate coefficient of variation
        cv = stdev(prices) / mean(prices) if mean(prices) > 0 else 1.0
        
        # Lower variance = better trend alignment
        alignment = max(0.0, 1.0 - cv)
        
        return alignment
    
    def _calculate_reliability_score(self, listings: List[Dict[str, Any]]) -> float:
        """
        Calculate seller reliability score (0-1).
        
        Factors:
        - Listing volume (more = better)
        - Sale completion rate
        - Price consistency
        - Condition accuracy (future)
        """
        total_listings = len(listings)
        sold_listings = [l for l in listings if l.get("status") == "sold"]
        sold_count = len(sold_listings)
        
        # Volume factor (normalized)
        volume_score = min(1.0, total_listings / 50)
        
        # Completion rate
        completion_rate = sold_count / total_listings if total_listings > 0 else 0.0
        
        # Price consistency
        if sold_count >= 3:
            prices = [l.get("final_price", 0) for l in sold_listings]
            cv = stdev(prices) / mean(prices) if mean(prices) > 0 else 1.0
            consistency_score = max(0.0, 1.0 - cv)
        else:
            consistency_score = 0.5
        
        # Weighted combination
        reliability = (
            volume_score * 0.3 +
            completion_rate * 0.4 +
            consistency_score * 0.3
        )
        
        return reliability
    
    def _empty_metrics(self, seller_id: str, source: str) -> Dict[str, Any]:
        """Return empty metrics when no data available."""
        return {
            "seller_id": seller_id,
            "source": source,
            "avg_start_price": 0.0,
            "avg_final_price": 0.0,
            "discount_rate": 0.0,
            "sale_speed": 0.0,
            "trend_alignment": 0.5,
            "reliability_score": 0.0,
            "listing_count": 0,
            "active_listings": 0,
            "avg_condition_score": 0.0,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def analyze_market_sellers(
        self, source: str, category: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Analyze all sellers in a market/category.
        
        Args:
            source: Marketplace source
            category: Optional category filter
            limit: Max sellers to analyze
        
        Returns:
            List of seller metrics
        """
        # Get unique seller IDs from recent market feed
        # TODO: Query from database or market feed cache
        
        # Mock: Generate sample seller IDs
        seller_ids = [f"{source}-seller-{i:03d}" for i in range(min(limit, 20))]
        
        # Analyze in batch
        metrics_list = await self.analyze_sellers_batch(seller_ids, source)
        
        logger.info(f"Analyzed {len(metrics_list)} sellers from {source}")
        
        return metrics_list
