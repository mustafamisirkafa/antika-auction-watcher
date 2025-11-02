"""Integration tests for Phase 2 components."""
import pytest
from unittest.mock import patch, AsyncMock
from backend.services.valuation.real_estimator import RealValuationEstimator
from backend.services.marketplace.adapter_factory import adapter_factory


@pytest.mark.asyncio
async def test_end_to_end_valuation_flow():
    """Test complete valuation flow with real estimator."""
    estimator = RealValuationEstimator()
    
    # Mock the adapter factory to return test data
    class MockTestAdapter:
        def __init__(self, name, data):
            self.name = name
            self.data = data
        
        def get_source_name(self):
            return self.name
        
        async def search_comparables(self, title, category, **kwargs):
            return self.data
    
    mock_ebay = MockTestAdapter('ebay', [
        {'price': 500.0, 'sold': True, 'weight': 1.0, 'source': 'ebay'},
        {'price': 520.0, 'sold': True, 'weight': 1.0, 'source': 'ebay'},
        {'price': 480.0, 'sold': False, 'weight': 1.0, 'source': 'ebay'}
    ])
    
    mock_etsy = MockTestAdapter('etsy', [
        {'price': 510.0, 'reviews': 100, 'weight': 0.85, 'source': 'etsy'},
        {'price': 495.0, 'reviews': 50, 'weight': 0.85, 'source': 'etsy'}
    ])
    
    with patch('backend.services.valuation.real_estimator.adapter_factory') as mock_factory:
        mock_factory.initialize = AsyncMock()
        mock_factory.get_healthy_adapters = AsyncMock(
            return_value=[mock_ebay, mock_etsy]
        )
        
        value, target, confidence, comps = await estimator.estimate_value(
            'Vintage Watch',
            'jewelry'
        )
        
        # Verify results
        assert value > 0
        assert target > 0
        assert target < value
        assert 0 < confidence <= 1.0
        assert len(comps) == 5
        
        # Verify data from both sources
        sources = {c['source'] for c in comps}
        assert 'ebay' in sources
        assert 'etsy' in sources


@pytest.mark.asyncio
async def test_category_learning_integration(session):
    """Test integration between outcome tracker and learning service."""
    from backend.services.analytics.outcome_tracker import OutcomeTracker
    from backend.services.analytics.learning_service import LearningService
    from backend.db.models import Bid, Item, User
    
    # Create test user
    user = User(email="test@example.com", username="test", hashed_password="hash")
    session.add(user)
    
    # Create test item
    item = Item(
        title="Test Item",
        category="antiques",
        seller_name="Seller",
        estimated_value=1000.0,
        target_buy_price=800.0,
        confidence_score=0.75
    )
    session.add(item)
    session.commit()
    session.refresh(user)
    session.refresh(item)
    
    # Create test bids and outcomes
    tracker = OutcomeTracker(session)
    
    for i in range(12):
        bid = Bid(
            item_id=item.id,
            user_id=user.id,
            bid_amount=750.0 + i * 10,
            bid_type="semi_auto",
            success=True
        )
        session.add(bid)
        session.commit()
        session.refresh(bid)
        
        # Record outcome
        await tracker.record_bid_outcome(
            bid_id=bid.id,
            won_auction=True,
            actual_resale_price=950.0 + i * 20
        )
    
    # Now train the model
    learning = LearningService(session)
    result = await learning.train_category_model('antiques')
    
    assert result['status'] == 'trained'
    assert result['sample_size'] == 12


@pytest.mark.asyncio
async def test_adapter_health_failover():
    """Test that unhealthy adapters are excluded."""
    await adapter_factory.initialize()
    
    # Check health
    health_status = await adapter_factory.check_all_health()
    
    # Get only healthy adapters
    healthy = await adapter_factory.get_healthy_adapters()
    
    # Should only return adapters that are healthy
    for adapter in healthy:
        source = adapter.get_source_name()
        assert health_status.get(source, False) is True


@pytest.mark.asyncio
async def test_metrics_collection_flow(session):
    """Test complete metrics collection flow."""
    from backend.services.analytics.metrics_collector import MetricsCollector
    
    collector = MetricsCollector(session)
    
    # Simulate API request lifecycle
    await collector.record_request_time('/api/v1/items', 125.0, 200)
    
    # Simulate external API call
    await collector.record_external_api_call('ebay', True, 300.0)
    
    # Simulate database query
    await collector.record_database_query('SELECT', 45.0, 10)
    
    # Simulate cache operations
    await collector.record_cache_hit('item:123')
    await collector.record_cache_miss('item:456')
    
    # Get dashboard
    dashboard = await collector.get_dashboard_metrics()
    
    assert 'response_times' in dashboard
    assert 'external_api_usage' in dashboard
    assert 'cache_performance' in dashboard


@pytest.mark.asyncio
async def test_valuation_with_caching():
    """Test that valuation uses caching properly."""
    from backend.services.marketplace.ebay_client import EbayClient
    from unittest.mock import Mock, AsyncMock
    
    client = EbayClient()
    
    # Mock Redis manager
    client.redis_manager.cache_get = AsyncMock(return_value=None)
    client.redis_manager.cache_set = AsyncMock()
    
    # Mock API call
    with patch.object(client, '_find_completed_items') as mock_find:
        mock_find.return_value = [
            {'price': 100.0, 'sold': True, 'title': 'Test', 'source': 'ebay'}
        ]
        
        # First call should hit API
        result1 = await client.search_comparables('Test Item', 'antiques')
        
        # Verify cache_set was called
        assert client.redis_manager.cache_set.called
        
        # Verify result
        assert len(result1) >= 1


@pytest.mark.asyncio
async def test_rate_limited_api_calls():
    """Test that API calls respect rate limits."""
    from backend.services.marketplace.ebay_client import EbayClient
    
    client = EbayClient()
    
    # Make first request
    can_request_1 = await client.check_rate_limit(10)
    assert can_request_1 is True
    
    client.record_request()
    
    # Immediate second request should also be allowed
    # (10 calls per second)
    can_request_2 = await client.check_rate_limit(10)
    assert can_request_2 is True


@pytest.mark.asyncio
async def test_adapter_error_handling():
    """Test adapter error handling in valuation."""
    estimator = RealValuationEstimator()
    
    class FailingAdapter:
        def get_source_name(self):
            return 'failing'
        
        async def search_comparables(self, *args, **kwargs):
            raise Exception('API Error')
    
    class WorkingAdapter:
        def get_source_name(self):
            return 'working'
        
        async def search_comparables(self, *args, **kwargs):
            return [{'price': 100.0, 'weight': 1.0, 'source': 'working'}]
    
    with patch('backend.services.valuation.real_estimator.adapter_factory') as mock_factory:
        mock_factory.initialize = AsyncMock()
        mock_factory.get_healthy_adapters = AsyncMock(
            return_value=[FailingAdapter(), WorkingAdapter()]
        )
        
        # Should still work with one failing adapter
        value, target, confidence, comps = await estimator.estimate_value(
            'Test',
            'default'
        )
        
        assert len(comps) == 1
        assert comps[0]['source'] == 'working'
