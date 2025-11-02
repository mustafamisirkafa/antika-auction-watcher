"""
Market data fetcher for profit analysis.
Mock implementation with realistic pseudo-random data.
"""
import random
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import hashlib


class MarketFetcher:
    """
    Fetches market data from various sources.
    Uses deterministic pseudo-random generation for consistent testing.
    """
    
    def __init__(self):
        """Initialize market fetcher."""
        self.sources = ["ebay", "etsy", "sahibinden", "letgo"]
        
        # Category price ranges (for realistic data)
        self.category_ranges = {
            "ceramics": (200, 2000),
            "silver": (500, 5000),
            "paintings": (1000, 10000),
            "furniture": (800, 8000),
            "coins": (50, 500),
            "jewelry": (300, 3000),
            "books": (20, 200),
            "textiles": (100, 1000),
            "default": (100, 1000)
        }
    
    def _get_seed(self, title: str, category: str, source: str) -> int:
        """Generate deterministic seed from input."""
        text = f"{title}_{category}_{source}".lower()
        return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
    
    async def fetch_market_data(
        self,
        title: str,
        category: str,
        source: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Fetch market data for a specific source.
        
        Args:
            title: Item title
            category: Item category
            source: Market source (ebay, etsy, etc.)
            
        Returns:
            Dictionary with market metrics
        """
        # Use specific source or random
        source = source or random.choice(self.sources)
        
        # Get deterministic seed
        seed = self._get_seed(title, category, source)
        random.seed(seed)
        
        # Get category price range
        price_min, price_max = self.category_ranges.get(
            category.lower(),
            self.category_ranges["default"]
        )
        
        # Generate realistic market data
        avg_price = random.uniform(price_min, price_max)
        sample_size = random.randint(5, 50)
        
        # Liquidity based on sample size
        liquidity_base = min(sample_size / 50, 1.0)
        liquidity_score = random.uniform(
            max(0.5, liquidity_base - 0.1),
            min(0.95, liquidity_base + 0.1)
        )
        
        # Volatility (lower is better)
        volatility_stability = random.uniform(0.6, 0.9)
        
        # Source-specific adjustments
        source_multipliers = {
            "ebay": 1.0,      # Baseline
            "etsy": 1.15,     # Premium for handmade/vintage
            "sahibinden": 0.85,  # Local market discount
            "letgo": 0.75     # Secondary market discount
        }
        
        avg_price *= source_multipliers.get(source, 1.0)
        
        # Simulate API delay
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        return {
            "source": source,
            "market_avg": round(avg_price, 2),
            "sample_size": sample_size,
            "liquidity_score": round(liquidity_score, 3),
            "volatility_stability": round(volatility_stability, 3),
            "last_checked": datetime.utcnow().isoformat()
        }
    
    async def fetch_all_sources(
        self,
        title: str,
        category: str
    ) -> List[Dict[str, any]]:
        """
        Fetch market data from all sources concurrently.
        
        Args:
            title: Item title
            category: Item category
            
        Returns:
            List of market data from all sources
        """
        tasks = [
            self.fetch_market_data(title, category, source)
            for source in self.sources
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions
        return [r for r in results if isinstance(r, dict)]
    
    def aggregate_market_data(
        self,
        market_data_list: List[Dict[str, any]]
    ) -> Dict[str, float]:
        """
        Aggregate market data from multiple sources.
        
        Args:
            market_data_list: List of market data dictionaries
            
        Returns:
            Aggregated metrics
        """
        if not market_data_list:
            return {
                "avg_market_price": 0.0,
                "avg_liquidity": 0.0,
                "avg_volatility_stability": 0.0,
                "total_samples": 0,
                "source_count": 0
            }
        
        # Calculate weighted average (weighted by sample size)
        total_weighted_price = sum(
            d["market_avg"] * d["sample_size"]
            for d in market_data_list
        )
        total_samples = sum(d["sample_size"] for d in market_data_list)
        
        avg_market_price = (
            total_weighted_price / total_samples
            if total_samples > 0
            else sum(d["market_avg"] for d in market_data_list) / len(market_data_list)
        )
        
        # Simple averages for other metrics
        avg_liquidity = sum(d["liquidity_score"] for d in market_data_list) / len(market_data_list)
        avg_volatility = sum(d["volatility_stability"] for d in market_data_list) / len(market_data_list)
        
        return {
            "avg_market_price": round(avg_market_price, 2),
            "avg_liquidity": round(avg_liquidity, 3),
            "avg_volatility_stability": round(avg_volatility, 3),
            "total_samples": total_samples,
            "source_count": len(market_data_list)
        }
    
    async def search_similar_items(
        self,
        title: str,
        category: str,
        limit: int = 10
    ) -> List[Dict[str, any]]:
        """
        Search for similar items in the market (mock).
        
        Args:
            title: Item title
            category: Item category
            limit: Maximum number of results
            
        Returns:
            List of similar items
        """
        # Mock similar items
        seed = self._get_seed(title, category, "search")
        random.seed(seed)
        
        price_min, price_max = self.category_ranges.get(
            category.lower(),
            self.category_ranges["default"]
        )
        
        similar_items = []
        for i in range(min(limit, random.randint(5, 15))):
            similar_items.append({
                "title": f"{title} (Similar #{i+1})",
                "price": round(random.uniform(price_min, price_max), 2),
                "source": random.choice(self.sources),
                "sold_date": datetime.utcnow().isoformat()
            })
        
        return similar_items


# Global instance
market_fetcher = MarketFetcher()
