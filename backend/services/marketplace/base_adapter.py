"""Base adapter interface for marketplace integrations."""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import hashlib
import json


class MarketplaceAdapter(ABC):
    """Abstract base class for marketplace adapters."""

    def __init__(self):
        self.source_name = self.get_source_name()
        self._last_request_time: Optional[datetime] = None
        self._request_count = 0

    @abstractmethod
    def get_source_name(self) -> str:
        """Get the name of this marketplace source."""
        pass

    @abstractmethod
    async def search_comparables(
        self,
        item_title: str,
        category: str,
        **kwargs
    ) -> List[Dict]:
        """
        Search for comparable items.
        
        Args:
            item_title: Title/description of the item
            category: Item category
            **kwargs: Additional search parameters
            
        Returns:
            List of comparable items with pricing data
        """
        pass

    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the marketplace API.
        
        Returns:
            True if authentication successful, False otherwise
        """
        pass

    def generate_cache_key(self, item_title: str, category: str, **kwargs) -> str:
        """Generate a unique cache key for the search."""
        # Create a consistent hash of the search parameters
        params = {
            'title': item_title.lower().strip(),
            'category': category.lower().strip(),
            'source': self.source_name,
            **kwargs
        }
        
        # Sort keys for consistency
        param_str = json.dumps(params, sort_keys=True)
        hash_obj = hashlib.md5(param_str.encode())
        
        return f"marketplace:{self.source_name}:{hash_obj.hexdigest()}"

    async def check_rate_limit(self, calls_per_second: float) -> bool:
        """
        Check if we're within rate limits.
        
        Args:
            calls_per_second: Maximum calls per second allowed
            
        Returns:
            True if we can make a request, False if we should wait
        """
        if self._last_request_time is None:
            return True
        
        min_interval = timedelta(seconds=1.0 / calls_per_second)
        time_since_last = datetime.utcnow() - self._last_request_time
        
        return time_since_last >= min_interval

    def record_request(self):
        """Record that a request was made."""
        self._last_request_time = datetime.utcnow()
        self._request_count += 1

    def get_request_count(self) -> int:
        """Get total number of requests made."""
        return self._request_count

    async def is_healthy(self) -> bool:
        """
        Check if the adapter is healthy and can make requests.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            return await self.authenticate()
        except Exception:
            return False
