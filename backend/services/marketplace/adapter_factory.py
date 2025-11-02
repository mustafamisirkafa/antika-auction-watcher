"""Factory for managing marketplace adapters."""
from typing import List, Dict, Optional
from enum import Enum
from backend.services.marketplace.ebay_client import EbayClient
from backend.services.marketplace.etsy_client import EtsyClient
from backend.services.marketplace.sahibinden_scraper import SahibindenScraper
from backend.services.marketplace.base_adapter import MarketplaceAdapter


class MarketplaceSource(str, Enum):
    """Available marketplace sources."""
    EBAY = "ebay"
    ETSY = "etsy"
    SAHIBINDEN = "sahibinden"


class AdapterFactory:
    """
    Factory for creating and managing marketplace adapters.
    
    Implements health checking and failover logic.
    """

    def __init__(self):
        self._adapters: Dict[str, MarketplaceAdapter] = {}
        self._health_status: Dict[str, bool] = {}
        self._initialized = False

    async def initialize(self):
        """Initialize all adapters."""
        if self._initialized:
            return
        
        # Create adapter instances
        self._adapters = {
            MarketplaceSource.EBAY: EbayClient(),
            MarketplaceSource.ETSY: EtsyClient(),
            MarketplaceSource.SAHIBINDEN: SahibindenScraper()
        }
        
        # Check initial health
        await self.check_all_health()
        
        self._initialized = True

    async def get_adapter(self, source: str) -> Optional[MarketplaceAdapter]:
        """
        Get a specific adapter by source name.
        
        Args:
            source: Source name (ebay, etsy, sahibinden)
            
        Returns:
            Adapter instance or None if not available
        """
        if not self._initialized:
            await self.initialize()
        
        return self._adapters.get(source)

    async def get_all_adapters(self) -> List[MarketplaceAdapter]:
        """
        Get all available adapters.
        
        Returns:
            List of adapter instances
        """
        if not self._initialized:
            await self.initialize()
        
        return list(self._adapters.values())

    async def get_healthy_adapters(self) -> List[MarketplaceAdapter]:
        """
        Get only healthy adapters.
        
        Returns:
            List of healthy adapter instances
        """
        if not self._initialized:
            await self.initialize()
        
        await self.check_all_health()
        
        return [
            adapter for source, adapter in self._adapters.items()
            if self._health_status.get(source, False)
        ]

    async def check_all_health(self) -> Dict[str, bool]:
        """
        Check health of all adapters.
        
        Returns:
            Dictionary mapping source names to health status
        """
        for source, adapter in self._adapters.items():
            try:
                self._health_status[source] = await adapter.is_healthy()
            except Exception:
                self._health_status[source] = False
        
        return self._health_status.copy()

    async def get_health_status(self) -> Dict[str, bool]:
        """
        Get current health status of all adapters.
        
        Returns:
            Dictionary mapping source names to health status
        """
        return self._health_status.copy()

    def get_adapter_count(self) -> int:
        """Get total number of adapters."""
        return len(self._adapters)

    def get_healthy_adapter_count(self) -> int:
        """Get number of healthy adapters."""
        return sum(1 for healthy in self._health_status.values() if healthy)


# Global factory instance
adapter_factory = AdapterFactory()
