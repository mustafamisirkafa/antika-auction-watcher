"""Mock adapters for marketplace data (eBay, Etsy, Sahibinden)."""
import random
from typing import List, Dict
from abc import ABC, abstractmethod


class MarketplaceAdapter(ABC):
    """Abstract base class for marketplace adapters."""

    @abstractmethod
    async def search_comparables(self, item_title: str, category: str) -> List[Dict]:
        """Search for comparable items."""
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Get the name of this marketplace source."""
        pass


class MockEbayAdapter(MarketplaceAdapter):
    """Mock eBay adapter for Phase 1 testing."""

    def __init__(self):
        self.source = "ebay"
        # Deterministic seed for testing
        self.random = random.Random(42)

    def get_source_name(self) -> str:
        """Get source name."""
        return self.source

    async def search_comparables(self, item_title: str, category: str) -> List[Dict]:
        """Search for comparable items (mock data)."""
        # Generate deterministic mock data
        base_price = self._calculate_base_price(category)
        num_results = self.random.randint(3, 8)
        
        comparables = []
        for i in range(num_results):
            variance = self.random.uniform(-0.3, 0.3)
            price = base_price * (1 + variance)
            
            comparables.append({
                "title": f"{item_title} - Similar Item {i+1}",
                "price": round(price, 2),
                "sold": self.random.choice([True, False]),
                "condition": self.random.choice(["new", "like_new", "good", "acceptable"]),
                "url": f"https://ebay.com/item/mock-{i+1}"
            })
        
        return comparables

    def _calculate_base_price(self, category: str) -> float:
        """Calculate base price based on category."""
        category_prices = {
            "antiques": 500.0,
            "jewelry": 800.0,
            "collectibles": 300.0,
            "art": 1000.0,
            "furniture": 600.0,
            "books": 50.0,
            "default": 200.0
        }
        return category_prices.get(category.lower(), category_prices["default"])


class MockEtsyAdapter(MarketplaceAdapter):
    """Mock Etsy adapter for Phase 1 testing."""

    def __init__(self):
        self.source = "etsy"
        self.random = random.Random(123)

    def get_source_name(self) -> str:
        """Get source name."""
        return self.source

    async def search_comparables(self, item_title: str, category: str) -> List[Dict]:
        """Search for comparable items (mock data)."""
        base_price = self._calculate_base_price(category)
        num_results = self.random.randint(4, 10)
        
        comparables = []
        for i in range(num_results):
            variance = self.random.uniform(-0.25, 0.35)
            price = base_price * (1 + variance)
            
            comparables.append({
                "title": f"{item_title} - Handmade {i+1}",
                "price": round(price, 2),
                "rating": round(self.random.uniform(4.0, 5.0), 1),
                "reviews": self.random.randint(5, 500),
                "url": f"https://etsy.com/listing/mock-{i+1}"
            })
        
        return comparables

    def _calculate_base_price(self, category: str) -> float:
        """Calculate base price based on category."""
        category_prices = {
            "antiques": 450.0,
            "jewelry": 750.0,
            "collectibles": 250.0,
            "art": 900.0,
            "furniture": 550.0,
            "books": 40.0,
            "default": 180.0
        }
        return category_prices.get(category.lower(), category_prices["default"])


class MockSahibindenAdapter(MarketplaceAdapter):
    """Mock Sahibinden adapter for Phase 1 testing."""

    def __init__(self):
        self.source = "sahibinden"
        self.random = random.Random(456)

    def get_source_name(self) -> str:
        """Get source name."""
        return self.source

    async def search_comparables(self, item_title: str, category: str) -> List[Dict]:
        """Search for comparable items (mock data)."""
        base_price = self._calculate_base_price(category)
        num_results = self.random.randint(5, 12)
        
        comparables = []
        for i in range(num_results):
            variance = self.random.uniform(-0.4, 0.4)
            price = base_price * (1 + variance)
            
            comparables.append({
                "title": f"{item_title} - ?kinci El {i+1}",
                "price": round(price, 2),
                "location": self.random.choice(["?stanbul", "Ankara", "?zmir"]),
                "date_posted": f"2024-{self.random.randint(1,12):02d}-{self.random.randint(1,28):02d}",
                "url": f"https://sahibinden.com/ilan/mock-{i+1}"
            })
        
        return comparables

    def _calculate_base_price(self, category: str) -> float:
        """Calculate base price based on category."""
        category_prices = {
            "antiques": 400.0,
            "jewelry": 700.0,
            "collectibles": 200.0,
            "art": 800.0,
            "furniture": 500.0,
            "books": 35.0,
            "default": 150.0
        }
        return category_prices.get(category.lower(), category_prices["default"])
