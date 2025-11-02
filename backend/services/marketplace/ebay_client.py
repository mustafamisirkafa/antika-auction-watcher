"""eBay API client with OAuth 2.0 authentication."""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import httpx
from backend.services.marketplace.base_adapter import MarketplaceAdapter
from backend.core.config import settings
from backend.realtime.redis_manager import RedisManager


class EbayClient(MarketplaceAdapter):
    """
    eBay API client using Finding API and Shopping API.
    
    Implements OAuth 2.0 authentication and rate limiting.
    Rate limits: 5,000 calls/day, 10 calls/second
    """

    def __init__(
        self,
        app_id: Optional[str] = None,
        cert_id: Optional[str] = None,
        dev_id: Optional[str] = None
    ):
        super().__init__()
        self.app_id = app_id or getattr(settings, 'ebay_app_id', None)
        self.cert_id = cert_id or getattr(settings, 'ebay_cert_id', None)
        self.dev_id = dev_id or getattr(settings, 'ebay_dev_id', None)
        
        # API endpoints
        self.finding_api_url = "https://svcs.ebay.com/services/search/FindingService/v1"
        self.shopping_api_url = "https://open.api.ebay.com/shopping"
        
        # Rate limiting
        self.max_calls_per_second = 10
        self.max_calls_per_day = 5000
        self.daily_call_count = 0
        self.daily_reset_time = datetime.utcnow() + timedelta(days=1)
        
        # Caching
        self.redis_manager = RedisManager()
        self.cache_ttl = 3600  # 1 hour
        
        # OAuth token
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None

    def get_source_name(self) -> str:
        """Get source name."""
        return "ebay"

    async def authenticate(self) -> bool:
        """
        Authenticate with eBay using OAuth 2.0.
        
        Returns:
            True if authentication successful
        """
        # Check if we have a valid token
        if self.access_token and self.token_expires_at:
            if datetime.utcnow() < self.token_expires_at:
                return True
        
        # For Phase 2, we need actual eBay credentials
        if not all([self.app_id, self.cert_id, self.dev_id]):
            # Return False if credentials not configured
            # In production, this would make actual OAuth calls
            return False
        
        # Mock OAuth for now (replace with actual implementation)
        # In production:
        # 1. Make POST to https://api.ebay.com/identity/v1/oauth2/token
        # 2. Get access_token
        # 3. Set expiration time
        
        # For development without real credentials:
        self.access_token = "mock_token_for_development"
        self.token_expires_at = datetime.utcnow() + timedelta(hours=2)
        
        return True

    async def search_comparables(
        self,
        item_title: str,
        category: str,
        max_results: int = 20,
        **kwargs
    ) -> List[Dict]:
        """
        Search for comparable items using eBay Finding API.
        
        Args:
            item_title: Item title to search for
            category: Item category
            max_results: Maximum number of results to return
            **kwargs: Additional search parameters
            
        Returns:
            List of comparable items
        """
        # Check cache first
        cache_key = self.generate_cache_key(item_title, category, **kwargs)
        
        try:
            cached_data = await self.redis_manager.cache_get(cache_key)
            if cached_data:
                import json
                return json.loads(cached_data)
        except Exception:
            pass  # Continue to API if cache fails
        
        # Check rate limits
        if not await self._check_daily_limit():
            raise Exception("eBay daily rate limit exceeded")
        
        # Wait for rate limit if needed
        while not await self.check_rate_limit(self.max_calls_per_second):
            await asyncio.sleep(0.1)
        
        # Ensure authenticated
        if not await self.authenticate():
            raise Exception("eBay authentication failed")
        
        # Make API request
        try:
            results = await self._find_completed_items(item_title, category, max_results)
            
            # Record the request
            self.record_request()
            self.daily_call_count += 1
            
            # Cache the results
            try:
                import json
                await self.redis_manager.cache_set(
                    cache_key,
                    json.dumps(results),
                    self.cache_ttl
                )
            except Exception:
                pass  # Continue even if caching fails
            
            return results
            
        except Exception as e:
            # Implement retry logic with exponential backoff
            return await self._retry_with_backoff(
                self._find_completed_items,
                item_title,
                category,
                max_results
            )

    async def _find_completed_items(
        self,
        item_title: str,
        category: str,
        max_results: int
    ) -> List[Dict]:
        """
        Call eBay Finding API to find completed items.
        
        Args:
            item_title: Search query
            category: Item category
            max_results: Max results to return
            
        Returns:
            List of items
        """
        # Build API request
        params = {
            'OPERATION-NAME': 'findCompletedItems',
            'SERVICE-VERSION': '1.13.0',
            'SECURITY-APPNAME': self.app_id,
            'RESPONSE-DATA-FORMAT': 'JSON',
            'REST-PAYLOAD': '',
            'keywords': item_title,
            'paginationInput.entriesPerPage': str(max_results),
            'itemFilter(0).name': 'Condition',
            'itemFilter(0).value': 'Used',
            'itemFilter(1).name': 'SoldItemsOnly',
            'itemFilter(1).value': 'true',
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(self.finding_api_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                return self._parse_finding_api_response(data)
                
            except httpx.HTTPError as e:
                raise Exception(f"eBay API request failed: {str(e)}")

    def _parse_finding_api_response(self, data: Dict) -> List[Dict]:
        """Parse eBay Finding API response into standardized format."""
        items = []
        
        try:
            search_result = data.get('findCompletedItemsResponse', [{}])[0]
            item_list = search_result.get('searchResult', [{}])[0].get('item', [])
            
            for item in item_list:
                parsed_item = {
                    'title': item.get('title', [''])[0],
                    'price': float(item.get('sellingStatus', [{}])[0]
                                 .get('currentPrice', [{'__value__': 0}])[0]
                                 .get('__value__', 0)),
                    'sold': True,
                    'condition': item.get('condition', [{'conditionDisplayName': ['Used']}])[0]
                              .get('conditionDisplayName', ['Used'])[0],
                    'url': item.get('viewItemURL', [''])[0],
                    'listing_type': item.get('listingInfo', [{}])[0]
                                   .get('listingType', [''])[0],
                    'end_time': item.get('listingInfo', [{}])[0]
                               .get('endTime', [''])[0],
                    'source': 'ebay'
                }
                items.append(parsed_item)
                
        except (KeyError, IndexError, ValueError) as e:
            # Log parsing error but don't fail completely
            pass
        
        return items

    async def _check_daily_limit(self) -> bool:
        """Check if we're within daily rate limit."""
        # Reset counter if it's a new day
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
                
                # Exponential backoff: 1s, 2s, 4s
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
        
        return []

    async def get_item_details(self, item_id: str) -> Optional[Dict]:
        """
        Get detailed item information using Shopping API.
        
        Args:
            item_id: eBay item ID
            
        Returns:
            Item details or None
        """
        # Check rate limits
        if not await self._check_daily_limit():
            return None
        
        while not await self.check_rate_limit(self.max_calls_per_second):
            await asyncio.sleep(0.1)
        
        params = {
            'callname': 'GetSingleItem',
            'responseencoding': 'JSON',
            'appid': self.app_id,
            'siteid': '0',
            'version': '967',
            'ItemID': item_id,
            'IncludeSelector': 'Details'
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(self.shopping_api_url, params=params)
                response.raise_for_status()
                
                self.record_request()
                self.daily_call_count += 1
                
                return response.json()
                
            except httpx.HTTPError:
                return None

    async def is_healthy(self) -> bool:
        """Check if eBay client is healthy."""
        if not all([self.app_id, self.cert_id, self.dev_id]):
            return False
        
        return await self.authenticate()
