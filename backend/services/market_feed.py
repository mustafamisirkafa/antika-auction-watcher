"""
MarketFeed Manager (Phase 11).
Handles external market data from eBay, Etsy, Instagram, etc.
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import aiohttp
from decimal import Decimal

logger = logging.getLogger(__name__)


class MarketFeed:
    """
    External market feed manager.
    
    Responsibilities:
    - Connect to external marketplace APIs
    - Normalize price data (currency, condition, location)
    - Emit normalized_feed to event bus
    """
    
    def __init__(self, event_bus, config):
        self.event_bus = event_bus
        self.config = config
        self.sources = {
            "ebay": self._fetch_ebay,
            "etsy": self._fetch_etsy,
            "instagram": self._fetch_instagram,
            "sahibinden": self._fetch_sahibinden
        }
        self._http_session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._http_session
    
    async def close(self):
        """Close HTTP session."""
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
    
    async def fetch_market_data(
        self, item_title: str, category: str, sources: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch market data from external sources.
        
        Args:
            item_title: Item title/description
            category: Item category
            sources: List of sources to query (defaults to all)
        
        Returns:
            List of normalized feed objects
        """
        if sources is None:
            sources = list(self.sources.keys())
        
        # Fetch from all sources concurrently
        tasks = []
        for source in sources:
            if source in self.sources:
                tasks.append(self.sources[source](item_title, category))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out errors and normalize
        normalized_feeds = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching from {sources[i]}: {result}")
                continue
            
            if result:
                normalized_feeds.extend(result)
        
        # Emit to event bus
        for feed in normalized_feeds:
            await self.event_bus.publish("market.feed", feed)
        
        logger.info(
            f"Fetched {len(normalized_feeds)} market data points "
            f"for '{item_title}' from {len(sources)} sources"
        )
        
        return normalized_feeds
    
    async def _fetch_ebay(
        self, item_title: str, category: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch data from eBay.
        
        Note: In production, use actual eBay Finding API.
        This is a mock implementation.
        """
        # TODO: Implement actual eBay API integration
        # For now, return mock data
        
        mock_listings = [
            {
                "title": f"{item_title} (used)",
                "price": 850.0,
                "currency": "TRY",
                "condition": "used",
                "location": "istanbul",
                "seller_rating": 4.5,
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "title": f"{item_title} (new)",
                "price": 1200.0,
                "currency": "TRY",
                "condition": "new",
                "location": "ankara",
                "seller_rating": 4.8,
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        
        return [
            self._normalize_listing(listing, "ebay", category)
            for listing in mock_listings
        ]
    
    async def _fetch_etsy(
        self, item_title: str, category: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch data from Etsy.
        
        Note: In production, use actual Etsy API.
        This is a mock implementation.
        """
        # TODO: Implement actual Etsy API integration
        
        mock_listings = [
            {
                "title": f"Vintage {item_title}",
                "price": 1100.0,
                "currency": "TRY",
                "condition": "vintage",
                "location": "izmir",
                "seller_rating": 4.9,
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        
        return [
            self._normalize_listing(listing, "etsy", category)
            for listing in mock_listings
        ]
    
    async def _fetch_instagram(
        self, item_title: str, category: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch data from Instagram (via hashtags/shops).
        
        Note: In production, use Instagram Graph API.
        This is a mock implementation.
        """
        # TODO: Implement Instagram API integration
        
        mock_listings = [
            {
                "title": f"#{item_title.replace(' ', '')}",
                "price": 950.0,
                "currency": "TRY",
                "condition": "new",
                "location": "online",
                "seller_rating": 4.3,
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        
        return [
            self._normalize_listing(listing, "instagram", category)
            for listing in mock_listings
        ]
    
    async def _fetch_sahibinden(
        self, item_title: str, category: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch data from Sahibinden (Turkish marketplace).
        
        Note: In production, scrape or use unofficial API.
        This is a mock implementation.
        """
        # TODO: Implement Sahibinden integration
        
        mock_listings = [
            {
                "title": f"{item_title} - Temiz",
                "price": 780.0,
                "currency": "TRY",
                "condition": "used",
                "location": "bursa",
                "seller_rating": 4.2,
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        
        return [
            self._normalize_listing(listing, "sahibinden", category)
            for listing in mock_listings
        ]
    
    def _normalize_listing(
        self, listing: Dict[str, Any], source: str, category: str
    ) -> Dict[str, Any]:
        """
        Normalize listing data to common format.
        
        Args:
            listing: Raw listing data
            source: Source marketplace
            category: Item category
        
        Returns:
            Normalized feed object
        """
        # Normalize price to TRY
        price = float(listing.get("price", 0))
        currency = listing.get("currency", "TRY")
        
        if currency != "TRY":
            # TODO: Apply currency conversion
            price = self._convert_currency(price, currency, "TRY")
        
        # Normalize condition
        condition = listing.get("condition", "unknown").lower()
        condition_map = {
            "new": 1.0,
            "like new": 0.95,
            "excellent": 0.9,
            "good": 0.85,
            "used": 0.8,
            "vintage": 0.75,
            "fair": 0.7,
            "poor": 0.6,
            "unknown": 0.75
        }
        condition_score = condition_map.get(condition, 0.75)
        
        # Calculate trust score based on source
        source_trust = {
            "ebay": 0.9,
            "etsy": 0.85,
            "instagram": 0.7,
            "sahibinden": 0.8
        }.get(source, 0.5)
        
        # Apply seller rating to trust
        seller_rating = listing.get("seller_rating", 4.0)
        trust_score = source_trust * (seller_rating / 5.0)
        
        return {
            "source": source,
            "category": category,
            "title": listing.get("title", ""),
            "price": round(price, 2),
            "currency": "TRY",
            "condition": condition,
            "condition_score": condition_score,
            "location": listing.get("location", "unknown"),
            "trust_score": trust_score,
            "timestamp": listing.get("timestamp", datetime.utcnow().isoformat()),
            "raw_data": listing
        }
    
    def _convert_currency(
        self, amount: float, from_currency: str, to_currency: str
    ) -> float:
        """
        Convert currency.
        
        Note: In production, use live exchange rates.
        This uses mock rates.
        """
        # Mock exchange rates (to TRY)
        rates = {
            "USD": 32.5,
            "EUR": 35.0,
            "GBP": 40.0,
            "TRY": 1.0
        }
        
        if from_currency == to_currency:
            return amount
        
        # Convert to TRY
        from_rate = rates.get(from_currency, 1.0)
        to_rate = rates.get(to_currency, 1.0)
        
        return amount * from_rate / to_rate
    
    def get_stats(self) -> Dict[str, Any]:
        """Get market feed statistics."""
        return {
            "enabled_sources": list(self.sources.keys()),
            "source_count": len(self.sources)
        }
