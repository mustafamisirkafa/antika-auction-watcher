"""Tests for valuation engine."""
import pytest
from backend.services.valuation.estimator import ValuationEstimator
from backend.services.valuation.adapters import (
    MockEbayAdapter,
    MockEtsyAdapter,
    MockSahibindenAdapter
)


@pytest.mark.asyncio
async def test_ebay_adapter():
    """Test eBay mock adapter."""
    adapter = MockEbayAdapter()
    
    results = await adapter.search_comparables("Vintage Clock", "antiques")
    
    assert len(results) >= 3
    assert all("price" in item for item in results)
    assert all("title" in item for item in results)
    assert adapter.get_source_name() == "ebay"


@pytest.mark.asyncio
async def test_etsy_adapter():
    """Test Etsy mock adapter."""
    adapter = MockEtsyAdapter()
    
    results = await adapter.search_comparables("Handmade Ring", "jewelry")
    
    assert len(results) >= 4
    assert all("price" in item for item in results)
    assert all("rating" in item for item in results)
    assert adapter.get_source_name() == "etsy"


@pytest.mark.asyncio
async def test_sahibinden_adapter():
    """Test Sahibinden mock adapter."""
    adapter = MockSahibindenAdapter()
    
    results = await adapter.search_comparables("Antika Saat", "antiques")
    
    assert len(results) >= 5
    assert all("price" in item for item in results)
    assert all("location" in item for item in results)
    assert adapter.get_source_name() == "sahibinden"


@pytest.mark.asyncio
async def test_valuation_estimator():
    """Test valuation estimator."""
    estimator = ValuationEstimator()
    
    estimated_value, target_price, confidence, comparables = (
        await estimator.estimate_value("Vintage Watch", "antiques")
    )
    
    assert estimated_value > 0
    assert target_price > 0
    assert target_price < estimated_value  # Target should be below estimate
    assert 0 <= confidence <= 1
    assert len(comparables) > 0


@pytest.mark.asyncio
async def test_valuation_confidence_calculation():
    """Test confidence score calculation."""
    estimator = ValuationEstimator()
    
    _, _, confidence, _ = await estimator.estimate_value("Test Item", "jewelry")
    
    # Confidence should be reasonable
    assert 0.3 <= confidence <= 1.0


def test_learning_parameter_update():
    """Test learning parameter updates."""
    estimator = ValuationEstimator()
    
    initial_margin = estimator.safety_margin
    
    # Simulate profitable outcome
    estimator.update_learning_parameters(
        actual_resale_price=600,
        estimated_value=500,
        target_buy_price=400
    )
    
    # Safety margin should decrease (being less conservative)
    assert estimator.safety_margin <= initial_margin
    
    # Simulate loss
    estimator.update_learning_parameters(
        actual_resale_price=300,
        estimated_value=500,
        target_buy_price=400
    )
    
    # Safety margin should increase (being more conservative)
    assert estimator.safety_margin > 0.05
