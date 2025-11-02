"""Etsy API v3 client with OAuth 2.0 authentication."""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import httpx
from backend.services.marketplace.base_adapter import MarketplaceAdapter
from backend.core.config import settings
from backend.realtime.redis_manager import RedisManager


class EtsyClient(MarketplaceAdapter):
    """
    Etsy API v3 client with OAuth 2.0.
    
    Rate limits: 10,000 calls/day, 10 calls/second per app
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None
    ):
        super().__init__()
        self.api_key = api_key or getattr(settings, 'etsy_api_key', None)
        self.secret_key = secret_key or getattr(settings, 'etsy_secret_key', None)
        
        # API endpoint
        self.api_url = "https://openapi.etsy.com/v3/application"
        
        # Rate limiting
        self.max_calls_per_second = 10
        self.max_calls_per_day = 10000
        self.daily_call_count = 0
        self.daily_reset_time = datetime.utcnow() + timedelta(days=1)
        
        # Caching
        self.redis_manager = RedisManager()
        self.cache_ttl = 7200  # 2 hours
        
        # OAuth token
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

    def get_source_name(self) -> str:
        """Get source name."""
        return "etsy"

    async def authenticate(self) -> bool:
        """
        Authenticate with Etsy using OAuth 2.0.
        
        Returns:
            True if authentication successful
        """
        # Check if we have a valid token
        if self.access_token and self.token_expires_at:
            if datetime.utcnow() < self.token_expires_at:
                return True
        
        if not all([self.api_key, self.secret_key]):
            return False
        
        # Mock OAuth for development
        # In production: implement full OAuth 2.0 flow
        self.access_token = "mock_etsy_token"
        self.token_expires_at = datetime.utcnow() + timedelta(hours=1)
        
        return True

    async def search_comparables(
        self,
        item_title: str,
        category: str,
        max_results: int = 20,
        **kwargs
    ) -> List[Dict]:
        """
        Search for comparable items using Etsy Listings API.
        
        Args:
            item_title: Item title to search for
            category: Item category
            max_results: Maximum number of results
            **kwargs: Additional parameters
            
        Returns:
            List of comparable items
        """
        # Check cache
        cache_key = self.generate_cache_key(item_title, category, **kwargs)
        
        try:
            cached_data = await self.redis_manager.cache_get(cache_key)
            if cached_data:
                import json
                return json.loads(cached_data)
        except Exception:
            pass
        
        # Check rate limits
        if not await self._check_daily_limit():
            raise Exception("Etsy daily rate limit exceeded")
        
        while not await self.check_rate_limit(self.max_calls_per_second):
            await asyncio.sleep(0.1)
        
        # Ensure authenticated
        if not await self.authenticate():
            raise Exception("Etsy authentication failed")
        
        try:
            results = await self._search_listings(item_title, category, max_results)
            
            self.record_request()
            self.daily_call_count += 1
            
            # Cache results
            try:
                import json
                await self.redis_manager.cache_set(
                    cache_key,
                    json.dumps(results),
                    self.cache_ttl
                )
            except Exception:
                pass
            
            return results
            
        except Exception:
            return await self._retry_with_backoff(
                self._search_listings,
                item_title,
                category,
                max_results
            )

    async def _search_listings(
        self,
        item_title: str,
        category: str,
        max_results: int
    ) -> List[Dict]:
        """
        Call Etsy API to search listings.
        
        Args:
            item_title: Search query
            category: Item category
            max_results: Max results
            
        Returns:
            List of items
        """
        # Build API request
        params = {
            'keywords': item_title,
            'limit': min(max_results, 100),
            'sort_on': 'score',
            'sort_order': 'desc'
        }
        
        headers = {
            'x-api-key': self.api_key,
            'Authorization': f'Bearer {self.access_token}'
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.api_url}/listings/active",
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                
                data = response.json()
                return self._parse_listings_response(data)
                
            except httpx.HTTPError as e:
                raise Exception(f"Etsy API request failed: {str(e)}")

    def _parse_listings_response(self, data: Dict) -> List[Dict]:
        """Parse Etsy API response into standardized format."""
        items = []
        
        try:
            results = data.get('results', [])
            
            for listing in results:
                # Get price from listing
                price_data = listing.get('price', {})
                
                parsed_item = {
                    'title': listing.get('title', ''),
                    'price': float(price_data.get('amount', 0)) / 100 if price_data.get('divisor') == 100 else float(price_data.get('amount', 0)),
                    'rating': listing.get('rating', 0),
                    'reviews': listing.get('num_favorers', 0),
                    'url': listing.get('url', ''),
                    'shop_name': listing.get('shop_name', ''),
                    'quantity': listing.get('quantity', 0),
                    'views': listing.get('views', 0),
                    'source': 'etsy'
                }
                items.append(parsed_item)
                
        except (KeyError, ValueError) as e:
            pass
        
        return items

    async def _check_daily_limit(self) -> bool:
        """Check if within daily rate limit."""
        if datetime.utcnow() >= self.daily_reset_time:
            self.daily_call_count = 0
            self.daily_reset_time = datetime.utcnow() + timedelta(days=1)
        
        return self.daily_call_count < self.max_calls_per_day

    async def _retry_with_backoff(
        self,
        func,
        *args,
        max_retries: int = 3,
        **kwargs
    ) -> List[Dict]:
        """Retry API call with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
        
        return []

    async def is_healthy(self) -> bool:
        """Check if Etsy client is healthy."""
        if not all([self.api_key, self.secret_key]):
            return False
        
        return await self.authenticate()
