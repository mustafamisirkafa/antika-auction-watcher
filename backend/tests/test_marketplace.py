"""Tests for marketplace integrations."""
import pytest
from backend.services.marketplace.ebay_client import EbayClient
from backend.services.marketplace.etsy_client import EtsyClient
from backend.services.marketplace.sahibinden_scraper import SahibindenScraper
from backend.services.marketplace.adapter_factory import AdapterFactory, MarketplaceSource


@pytest.mark.asyncio
async def test_ebay_client_initialization():
    """Test eBay client initialization."""
    client = EbayClient()
    
    assert client.get_source_name() == "ebay"
    assert client.max_calls_per_second == 10
    assert client.max_calls_per_day == 5000


@pytest.mark.asyncio
async def test_ebay_client_authentication():
    """Test eBay OAuth authentication."""
    client = EbayClient()
    
    # Should return False without credentials
    result = await client.authenticate()
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_ebay_cache_key_generation():
    """Test cache key generation."""
    client = EbayClient()
    
    key1 = client.generate_cache_key("vintage watch", "jewelry")
    key2 = client.generate_cache_key("vintage watch", "jewelry")
    key3 = client.generate_cache_key("vintage clock", "jewelry")
    
    # Same inputs should produce same key
    assert key1 == key2
    
    # Different inputs should produce different keys
    assert key1 != key3
    
    # Key should include source name
    assert "ebay" in key1


@pytest.mark.asyncio
async def test_etsy_client_initialization():
    """Test Etsy client initialization."""
    client = EtsyClient()
    
    assert client.get_source_name() == "etsy"
    assert client.max_calls_per_second == 10
    assert client.max_calls_per_day == 10000


@pytest.mark.asyncio
async def test_etsy_client_authentication():
    """Test Etsy OAuth authentication."""
    client = EtsyClient()
    
    result = await client.authenticate()
    assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_sahibinden_scraper_initialization():
    """Test Sahibinden scraper initialization."""
    scraper = SahibindenScraper()
    
    assert scraper.get_source_name() == "sahibinden"
    assert scraper.min_request_interval == 2.0
    assert len(scraper.user_agents) > 0


@pytest.mark.asyncio
async def test_sahibinden_authentication():
    """Test Sahibinden authentication (always True)."""
    scraper = SahibindenScraper()
    
    result = await scraper.authenticate()
    assert result is True


@pytest.mark.asyncio
async def test_adapter_factory_initialization():
    """Test adapter factory initialization."""
    factory = AdapterFactory()
    
    await factory.initialize()
    
    assert factory.get_adapter_count() == 3


@pytest.mark.asyncio
async def test_adapter_factory_get_adapter():
    """Test getting specific adapter."""
    factory = AdapterFactory()
    
    ebay = await factory.get_adapter(MarketplaceSource.EBAY)
    assert ebay is not None
    assert ebay.get_source_name() == "ebay"
    
    etsy = await factory.get_adapter(MarketplaceSource.ETSY)
    assert etsy is not None
    assert etsy.get_source_name() == "etsy"
    
    sahib = await factory.get_adapter(MarketplaceSource.SAHIBINDEN)
    assert sahib is not None
    assert sahib.get_source_name() == "sahibinden"


@pytest.mark.asyncio
async def test_adapter_factory_get_all_adapters():
    """Test getting all adapters."""
    factory = AdapterFactory()
    
    adapters = await factory.get_all_adapters()
    
    assert len(adapters) == 3
    assert all(hasattr(adapter, 'search_comparables') for adapter in adapters)


@pytest.mark.asyncio
async def test_adapter_factory_health_check():
    """Test adapter health checking."""
    factory = AdapterFactory()
    
    health_status = await factory.check_all_health()
    
    assert isinstance(health_status, dict)
    assert len(health_status) == 3
    assert all(isinstance(v, bool) for v in health_status.values())


@pytest.mark.asyncio
async def test_rate_limiting():
    """Test rate limiting logic."""
    client = EbayClient()
    
    # Should be able to make first request
    can_request = await client.check_rate_limit(10)
    assert can_request is True
    
    # Record request
    client.record_request()
    
    # Request count should increment
    assert client.get_request_count() == 1
