"""Comprehensive tests for real valuation estimator."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.services.valuation.real_estimator import RealValuationEstimator
from backend.services.marketplace.base_adapter import MarketplaceAdapter


class MockAdapter(MarketplaceAdapter):
    """Mock adapter for testing."""
    
    def __init__(self, name: str, data: list):
        super().__init__()
        self.name = name
        self.data = data
    
    def get_source_name(self):
        return self.name
    
    async def search_comparables(self, item_title, category, **kwargs):
        return self.data
    
    async def authenticate(self):
        return True


@pytest.fixture
def estimator():
    """Create estimator instance."""
    return RealValuationEstimator()


def test_estimator_initialization(estimator):
    """Test estimator initialization."""
    assert estimator.safety_margin == 0.15
    assert 'ebay' in estimator.source_weights
    assert 'antiques' in estimator.category_factors


def test_source_weights(estimator):
    """Test source reliability weights."""
    assert estimator.source_weights['ebay'] == 1.0
    assert estimator.source_weights['etsy'] == 0.85
    assert estimator.source_weights['sahibinden'] == 0.7


def test_category_factors(estimator):
    """Test category-specific factors."""
    antiques = estimator.category_factors['antiques']
    assert antiques['premium'] == 1.2
    assert antiques['volatility'] == 0.3
    
    jewelry = estimator.category_factors['jewelry']
    assert jewelry['premium'] == 1.15
    assert jewelry['volatility'] == 0.25


@pytest.mark.asyncio
async def test_estimate_value_no_adapters(estimator):
    """Test estimation with no adapters available."""
    with patch('backend.services.valuation.real_estimator.adapter_factory') as mock_factory:
        mock_factory.initialize = AsyncMock()
        mock_factory.get_healthy_adapters = AsyncMock(return_value=[])
        mock_factory.get_all_adapters = AsyncMock(return_value=[])
        
        value, target, confidence, comps = await estimator.estimate_value(
            'Test Item',
            'antiques'
        )
        
        assert value == 0.0
        assert target == 0.0
        assert confidence == 0.0
        assert len(comps) == 0


@pytest.mark.asyncio
async def test_estimate_value_single_source(estimator):
    """Test estimation with single data source."""
    mock_adapter = MockAdapter('ebay', [
        {'price': 100.0, 'sold': True, 'weight': 1.0, 'source': 'ebay'},
        {'price': 110.0, 'sold': True, 'weight': 1.0, 'source': 'ebay'},
        {'price': 105.0, 'sold': False, 'weight': 1.0, 'source': 'ebay'}
    ])
    
    with patch('backend.services.valuation.real_estimator.adapter_factory') as mock_factory:
        mock_factory.initialize = AsyncMock()
        mock_factory.get_healthy_adapters = AsyncMock(return_value=[mock_adapter])
        
        value, target, confidence, comps = await estimator.estimate_value(
            'Test Item',
            'antiques'
        )
        
        assert value > 0
        assert target > 0
        assert target < value  # Target should be lower than estimate
        assert 0 < confidence <= 1.0
        assert len(comps) == 3


@pytest.mark.asyncio
async def test_estimate_value_multiple_sources(estimator):
    """Test estimation with multiple data sources."""
    ebay_adapter = MockAdapter('ebay', [
        {'price': 100.0, 'sold': True, 'weight': 1.0, 'source': 'ebay'}
    ])
    
    etsy_adapter = MockAdapter('etsy', [
        {'price': 95.0, 'reviews': 100, 'weight': 0.85, 'source': 'etsy'}
    ])
    
    with patch('backend.services.valuation.real_estimator.adapter_factory') as mock_factory:
        mock_factory.initialize = AsyncMock()
        mock_factory.get_healthy_adapters = AsyncMock(
            return_value=[ebay_adapter, etsy_adapter]
        )
        
        value, target, confidence, comps = await estimator.estimate_value(
            'Test Item',
            'jewelry'
        )
        
        assert value > 0
        assert len(comps) == 2
        assert any(c['source'] == 'ebay' for c in comps)
        assert any(c['source'] == 'etsy' for c in comps)


def test_calculate_estimated_value_empty(estimator):
    """Test value calculation with no comparables."""
    result = estimator._calculate_estimated_value_v2([], 'antiques')
    
    assert result == 0.0


def test_calculate_estimated_value_with_data(estimator):
    """Test value calculation with comparables."""
    comparables = [
        {'price': 100.0, 'weight': 1.0, 'sold': True},
        {'price': 110.0, 'weight': 1.0, 'sold': True},
        {'price': 105.0, 'weight': 1.0, 'sold': False}
    ]
    
    result = estimator._calculate_estimated_value_v2(comparables, 'antiques')
    
    # Should apply antiques premium (1.2x)
    assert result > 100.0
    assert result < 150.0  # Reasonable upper bound


def test_calculate_estimated_value_sold_weight(estimator):
    """Test that sold items get higher weight."""
    comparables_with_sold = [
        {'price': 100.0, 'weight': 1.0, 'sold': True},  # Gets 1.5x weight
        {'price': 200.0, 'weight': 1.0, 'sold': False}
    ]
    
    result_with_sold = estimator._calculate_estimated_value_v2(
        comparables_with_sold, 'default'
    )
    
    # Result should be closer to 100 than 200 due to sold item weighting
    assert result_with_sold < 150.0


def test_calculate_confidence_empty(estimator):
    """Test confidence calculation with no data."""
    confidence = estimator._calculate_confidence_v2([], 'antiques')
    
    assert confidence == 0.0


def test_calculate_confidence_single_item(estimator):
    """Test confidence with single comparable."""
    comparables = [
        {'price': 100.0, 'source': 'ebay', 'sold': True}
    ]
    
    confidence = estimator._calculate_confidence_v2(comparables, 'antiques')
    
    # Should have moderate confidence with single item
    assert 0.0 < confidence < 0.8


def test_calculate_confidence_many_items(estimator):
    """Test confidence with many comparables."""
    comparables = [
        {'price': 100.0 + i, 'source': 'ebay', 'sold': True}
        for i in range(20)
    ]
    
    confidence = estimator._calculate_confidence_v2(comparables, 'jewelry')
    
    # Should have high confidence with many consistent items
    assert confidence > 0.5


def test_calculate_confidence_high_variance(estimator):
    """Test confidence with high price variance."""
    comparables = [
        {'price': 50.0, 'source': 'ebay'},
        {'price': 500.0, 'source': 'ebay'},
        {'price': 100.0, 'source': 'etsy'}
    ]
    
    confidence = estimator._calculate_confidence_v2(comparables, 'art')
    
    # High variance should reduce confidence
    # But art has 40% expected volatility, so not too penalized
    assert 0.0 < confidence < 1.0


def test_calculate_confidence_source_diversity(estimator):
    """Test that source diversity increases confidence."""
    # Single source
    single_source = [
        {'price': 100.0, 'source': 'ebay'},
        {'price': 105.0, 'source': 'ebay'}
    ]
    
    conf_single = estimator._calculate_confidence_v2(single_source, 'default')
    
    # Multiple sources
    multi_source = [
        {'price': 100.0, 'source': 'ebay'},
        {'price': 105.0, 'source': 'etsy'},
        {'price': 102.0, 'source': 'sahibinden'}
    ]
    
    conf_multi = estimator._calculate_confidence_v2(multi_source, 'default')
    
    # Multi-source should have higher confidence
    assert conf_multi > conf_single


def test_calculate_target_price_high_confidence(estimator):
    """Test target price with high confidence."""
    target = estimator._calculate_target_price_v2(1000.0, 0.9, 'jewelry')
    
    # High confidence should result in higher target (lower margin)
    assert target > 800.0
    assert target < 1000.0


def test_calculate_target_price_low_confidence(estimator):
    """Test target price with low confidence."""
    target = estimator._calculate_target_price_v2(1000.0, 0.3, 'jewelry')
    
    # Low confidence should result in lower target (higher margin)
    assert target < 800.0


def test_calculate_target_price_volatile_category(estimator):
    """Test target price for volatile category."""
    # Art has 40% volatility
    target_art = estimator._calculate_target_price_v2(1000.0, 0.7, 'art')
    
    # Books have 15% volatility
    target_books = estimator._calculate_target_price_v2(1000.0, 0.7, 'books')
    
    # More volatile category should have lower target (higher safety margin)
    assert target_art < target_books


def test_calculate_target_price_margins_clamped(estimator):
    """Test that margins are clamped to reasonable range."""
    # Test minimum margin (5%)
    target_min = estimator._calculate_target_price_v2(100.0, 1.0, 'books')
    assert target_min >= 60.0  # Not less than 40% margin
    
    # Test maximum margin (40%)
    target_max = estimator._calculate_target_price_v2(100.0, 0.0, 'art')
    assert target_max >= 60.0  # Cap at 40% margin


def test_remove_outliers_small_dataset(estimator):
    """Test outlier removal with small dataset."""
    prices = [100.0, 105.0, 110.0]
    
    result = estimator._remove_outliers(prices)
    
    # Small dataset should not remove outliers
    assert len(result) == len(prices)


def test_remove_outliers_with_outliers(estimator):
    """Test outlier removal with actual outliers."""
    prices = [
        100.0, 105.0, 110.0, 108.0, 102.0,  # Normal range
        500.0  # Clear outlier
    ]
    
    result = estimator._remove_outliers(prices)
    
    # Should remove the outlier
    assert 500.0 not in result
    assert len(result) < len(prices)


def test_remove_outliers_no_outliers(estimator):
    """Test outlier removal with no outliers."""
    prices = [100.0 + i for i in range(10)]  # Consistent range
    
    result = estimator._remove_outliers(prices)
    
    # Should keep all prices
    assert len(result) == len(prices)


def test_update_category_accuracy(estimator):
    """Test updating category accuracy."""
    estimator.update_category_accuracy('antiques', 0.85)
    
    assert estimator.historical_accuracy['antiques'] == 0.85


def test_update_learning_parameters_profitable(estimator):
    """Test learning update with profitable outcome."""
    initial_margin = estimator.safety_margin
    
    # Simulate highly profitable outcome
    estimator.update_learning_parameters(
        actual_resale_price=1000.0,
        estimated_value=800.0,
        target_buy_price=500.0,
        category='jewelry'
    )
    
    # Margin should decrease (less conservative)
    assert estimator.safety_margin <= initial_margin


def test_update_learning_parameters_loss(estimator):
    """Test learning update with loss."""
    initial_margin = estimator.safety_margin
    
    # Simulate loss
    estimator.update_learning_parameters(
        actual_resale_price=400.0,
        estimated_value=600.0,
        target_buy_price=500.0,
        category='jewelry'
    )
    
    # Margin should increase (more conservative)
    assert estimator.safety_margin > initial_margin


def test_update_learning_parameters_category_accuracy(estimator):
    """Test that category accuracy is updated."""
    estimator.update_learning_parameters(
        actual_resale_price=800.0,
        estimated_value=820.0,
        target_buy_price=600.0,
        category='collectibles'
    )
    
    # Should have recorded accuracy for this category
    assert 'collectibles' in estimator.historical_accuracy
    # Accuracy should be high (estimate was close)
    assert estimator.historical_accuracy['collectibles'] > 0.9


@pytest.mark.asyncio
async def test_estimate_value_adapter_failure(estimator):
    """Test estimation when adapter fails."""
    failing_adapter = MockAdapter('ebay', [])
    failing_adapter.search_comparables = AsyncMock(
        side_effect=Exception('API Error')
    )
    
    working_adapter = MockAdapter('etsy', [
        {'price': 100.0, 'weight': 0.85, 'source': 'etsy'}
    ])
    
    with patch('backend.services.valuation.real_estimator.adapter_factory') as mock_factory:
        mock_factory.initialize = AsyncMock()
        mock_factory.get_healthy_adapters = AsyncMock(
            return_value=[failing_adapter, working_adapter]
        )
        
        value, target, confidence, comps = await estimator.estimate_value(
            'Test Item',
            'antiques'
        )
        
        # Should still work with one adapter
        assert len(comps) == 1
        assert comps[0]['source'] == 'etsy'


def test_category_factors_coverage(estimator):
    """Test that all major categories have factors."""
    categories = ['antiques', 'jewelry', 'collectibles', 'art', 'furniture', 'books']
    
    for category in categories:
        assert category in estimator.category_factors
        factors = estimator.category_factors[category]
        assert 'premium' in factors
        assert 'volatility' in factors
        assert 0.5 <= factors['premium'] <= 1.5
        assert 0.0 <= factors['volatility'] <= 0.5


def test_historical_accuracy_tracking(estimator):
    """Test historical accuracy tracking over multiple updates."""
    # First update
    estimator.update_learning_parameters(800, 820, 600, 'antiques')
    first_accuracy = estimator.historical_accuracy['antiques']
    
    # Second update (less accurate)
    estimator.update_learning_parameters(700, 820, 600, 'antiques')
    second_accuracy = estimator.historical_accuracy['antiques']
    
    # Should use moving average (70% old, 30% new)
    assert second_accuracy < first_accuracy
    assert second_accuracy > 0  # Still positive


def test_safety_margin_bounds(estimator):
    """Test that safety margin stays within bounds."""
    # Try to push margin very low
    for _ in range(20):
        estimator.update_learning_parameters(2000, 1000, 500, 'test')
    
    assert estimator.safety_margin >= 0.05  # Minimum 5%
    
    # Reset and push margin very high
    estimator.safety_margin = 0.15
    for _ in range(20):
        estimator.update_learning_parameters(300, 1000, 500, 'test')
    
    assert estimator.safety_margin <= 0.40  # Maximum 40%
