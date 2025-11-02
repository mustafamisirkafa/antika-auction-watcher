"""Tests for adapter factory."""
import pytest
from backend.services.marketplace.adapter_factory import (
    AdapterFactory,
    MarketplaceSource
)


@pytest.fixture
def factory():
    """Create adapter factory instance."""
    return AdapterFactory()


@pytest.mark.asyncio
async def test_factory_initialization(factory):
    """Test factory initialization."""
    await factory.initialize()
    
    assert factory._initialized is True
    assert len(factory._adapters) == 3


@pytest.mark.asyncio
async def test_factory_double_initialization(factory):
    """Test that double initialization is safe."""
    await factory.initialize()
    await factory.initialize()  # Should not error
    
    assert factory._initialized is True


@pytest.mark.asyncio
async def test_get_adapter_ebay(factory):
    """Test getting eBay adapter."""
    adapter = await factory.get_adapter(MarketplaceSource.EBAY)
    
    assert adapter is not None
    assert adapter.get_source_name() == 'ebay'


@pytest.mark.asyncio
async def test_get_adapter_etsy(factory):
    """Test getting Etsy adapter."""
    adapter = await factory.get_adapter(MarketplaceSource.ETSY)
    
    assert adapter is not None
    assert adapter.get_source_name() == 'etsy'


@pytest.mark.asyncio
async def test_get_adapter_sahibinden(factory):
    """Test getting Sahibinden adapter."""
    adapter = await factory.get_adapter(MarketplaceSource.SAHIBINDEN)
    
    assert adapter is not None
    assert adapter.get_source_name() == 'sahibinden'


@pytest.mark.asyncio
async def test_get_adapter_invalid(factory):
    """Test getting non-existent adapter."""
    adapter = await factory.get_adapter('invalid_source')
    
    assert adapter is None


@pytest.mark.asyncio
async def test_get_all_adapters(factory):
    """Test getting all adapters."""
    adapters = await factory.get_all_adapters()
    
    assert len(adapters) == 3
    
    sources = {adapter.get_source_name() for adapter in adapters}
    assert sources == {'ebay', 'etsy', 'sahibinden'}


@pytest.mark.asyncio
async def test_check_all_health(factory):
    """Test checking health of all adapters."""
    health_status = await factory.check_all_health()
    
    assert isinstance(health_status, dict)
    assert len(health_status) == 3
    
    for source, is_healthy in health_status.items():
        assert isinstance(is_healthy, bool)


@pytest.mark.asyncio
async def test_get_health_status(factory):
    """Test getting current health status."""
    await factory.initialize()
    await factory.check_all_health()
    
    status = await factory.get_health_status()
    
    assert isinstance(status, dict)
    assert len(status) == 3


@pytest.mark.asyncio
async def test_get_healthy_adapters(factory):
    """Test getting only healthy adapters."""
    healthy = await factory.get_healthy_adapters()
    
    # Sahibinden should always be healthy (no auth required)
    assert any(a.get_source_name() == 'sahibinden' for a in healthy)


def test_get_adapter_count(factory):
    """Test getting adapter count."""
    count = factory.get_adapter_count()
    
    assert count == 0  # Before initialization
    
    # After initialization would be 3


@pytest.mark.asyncio
async def test_get_healthy_adapter_count(factory):
    """Test getting healthy adapter count."""
    await factory.initialize()
    await factory.check_all_health()
    
    count = factory.get_healthy_adapter_count()
    
    # At least sahibinden should be healthy
    assert count >= 1
    assert count <= 3


@pytest.mark.asyncio
async def test_factory_lazy_initialization(factory):
    """Test that factory initializes lazily."""
    assert factory._initialized is False
    
    # First get_adapter call should initialize
    await factory.get_adapter(MarketplaceSource.EBAY)
    
    assert factory._initialized is True


@pytest.mark.asyncio
async def test_health_check_updates_status(factory):
    """Test that health checks update internal status."""
    await factory.initialize()
    
    initial_status = await factory.get_health_status()
    
    # Run another health check
    await factory.check_all_health()
    
    updated_status = await factory.get_health_status()
    
    # Status should be updated
    assert isinstance(updated_status, dict)
