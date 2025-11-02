"""Comprehensive tests for learning service."""
import pytest
from unittest.mock import Mock
from sqlmodel import Session, select
from backend.services.analytics.learning_service import LearningService
from backend.db.analytics_models import BidOutcome, CategoryMetrics


@pytest.fixture
def learning_service(session):
    """Create learning service instance."""
    return LearningService(session)


def test_learning_service_initialization(learning_service):
    """Test learning service initialization."""
    assert learning_service.min_sample_size == 10
    assert learning_service.learning_rate == 0.1
    assert learning_service.estimator is not None


@pytest.mark.asyncio
async def test_train_category_insufficient_data(learning_service, session):
    """Test training with insufficient data."""
    result = await learning_service.train_category_model('test_category')
    
    assert result['status'] == 'insufficient_data'
    assert result['sample_size'] < learning_service.min_sample_size


@pytest.mark.asyncio
async def test_train_category_with_data(learning_service, session):
    """Test training with sufficient data."""
    # Create test outcomes
    for i in range(15):
        outcome = BidOutcome(
            bid_id=i,
            item_id=i,
            user_id=1,
            estimated_value=1000.0,
            target_buy_price=800.0,
            actual_bid_amount=750.0,
            confidence_score=0.7,
            won_auction=True,
            actual_resale_price=950.0 + i * 10,
            gross_profit=200.0 + i * 10,
            profit_margin=0.2,
            roi=0.25,
            valuation_accuracy=0.8,
            category='antiques'
        )
        session.add(outcome)
    
    session.commit()
    
    result = await learning_service.train_category_model('antiques')
    
    assert result['status'] == 'trained'
    assert result['sample_size'] == 15
    assert 'optimal_margin' in result
    assert 'optimal_confidence' in result


@pytest.mark.asyncio
async def test_calculate_optimal_margin(learning_service):
    """Test optimal margin calculation."""
    outcomes = [
        Mock(
            actual_resale_price=1000.0,
            target_buy_price=800.0,
            won_auction=True
        ),
        Mock(
            actual_resale_price=900.0,
            target_buy_price=720.0,
            won_auction=True
        )
    ]
    
    margin = await learning_service._calculate_optimal_margin(outcomes)
    
    assert 0.05 <= margin <= 0.40
    assert isinstance(margin, float)


@pytest.mark.asyncio
async def test_calculate_optimal_margin_no_profitable(learning_service):
    """Test margin calculation with no profitable outcomes."""
    outcomes = [
        Mock(
            actual_resale_price=None,
            target_buy_price=800.0,
            won_auction=False
        )
    ]
    
    margin = await learning_service._calculate_optimal_margin(outcomes)
    
    # Should return default margin
    assert margin == 0.15


@pytest.mark.asyncio
async def test_calculate_optimal_confidence(learning_service):
    """Test optimal confidence threshold calculation."""
    outcomes = [
        # High confidence, profitable
        Mock(confidence_score=0.8, gross_profit=200.0),
        Mock(confidence_score=0.75, gross_profit=150.0),
        Mock(confidence_score=0.7, gross_profit=100.0),
        # Medium confidence, mixed
        Mock(confidence_score=0.6, gross_profit=50.0),
        Mock(confidence_score=0.55, gross_profit=-10.0),
        # Low confidence, unprofitable
        Mock(confidence_score=0.4, gross_profit=-50.0),
        Mock(confidence_score=0.3, gross_profit=-100.0)
    ]
    
    confidence = await learning_service._calculate_optimal_confidence(outcomes)
    
    # Should prefer higher threshold where profitability is better
    assert confidence >= 0.5


@pytest.mark.asyncio
async def test_calculate_source_weights(learning_service):
    """Test source weight calculation."""
    outcomes = [Mock()]
    
    weights = await learning_service._calculate_source_weights(outcomes, 'antiques')
    
    assert 'ebay' in weights
    assert 'etsy' in weights
    assert 'sahibinden' in weights
    assert weights['ebay'] == 1.0


@pytest.mark.asyncio
async def test_calculate_category_accuracy(learning_service):
    """Test category accuracy calculation."""
    outcomes = [
        Mock(valuation_accuracy=0.8),
        Mock(valuation_accuracy=0.9),
        Mock(valuation_accuracy=0.7)
    ]
    
    accuracy = await learning_service._calculate_category_accuracy(outcomes)
    
    assert 0.7 <= accuracy <= 0.9
    assert accuracy == pytest.approx(0.8, rel=0.1)


@pytest.mark.asyncio
async def test_calculate_category_accuracy_no_data(learning_service):
    """Test accuracy calculation with no data."""
    outcomes = [
        Mock(valuation_accuracy=None),
        Mock(valuation_accuracy=None)
    ]
    
    accuracy = await learning_service._calculate_category_accuracy(outcomes)
    
    assert accuracy == 0.5  # Default


@pytest.mark.asyncio
async def test_update_category_learning_params(learning_service, session):
    """Test updating category learning parameters."""
    # Create initial metrics
    metrics = CategoryMetrics(
        category='test_category',
        recommended_safety_margin=0.15,
        confidence_threshold=0.6
    )
    session.add(metrics)
    session.commit()
    
    # Update parameters
    await learning_service._update_category_learning_params(
        'test_category',
        0.20,  # New optimal margin
        0.65   # New optimal confidence
    )
    
    # Check updated values
    statement = select(CategoryMetrics).where(
        CategoryMetrics.category == 'test_category'
    )
    updated = session.exec(statement).first()
    
    # Should be gradually adjusted (learning rate = 0.1)
    assert updated.recommended_safety_margin != 0.15
    assert updated.recommended_safety_margin != 0.20
    # New value = old * 0.9 + new * 0.1
    expected_margin = 0.15 * 0.9 + 0.20 * 0.1
    assert updated.recommended_safety_margin == pytest.approx(expected_margin)


@pytest.mark.asyncio
async def test_update_creates_new_metrics(learning_service, session):
    """Test that update creates metrics if not exist."""
    await learning_service._update_category_learning_params(
        'new_category',
        0.18,
        0.62
    )
    
    # Check that metrics were created
    statement = select(CategoryMetrics).where(
        CategoryMetrics.category == 'new_category'
    )
    metrics = session.exec(statement).first()
    
    assert metrics is not None
    assert metrics.category == 'new_category'


@pytest.mark.asyncio
async def test_retrain_all_categories(learning_service, session):
    """Test retraining all categories."""
    # Create outcomes for multiple categories
    for category in ['antiques', 'jewelry']:
        for i in range(12):
            outcome = BidOutcome(
                bid_id=i,
                item_id=i,
                user_id=1,
                estimated_value=1000.0,
                target_buy_price=800.0,
                actual_bid_amount=750.0,
                confidence_score=0.7,
                won_auction=True,
                actual_resale_price=950.0,
                gross_profit=200.0,
                category=category
            )
            session.add(outcome)
    
    session.commit()
    
    results = await learning_service.retrain_all_categories()
    
    assert 'antiques' in results
    assert 'jewelry' in results
    assert results['antiques']['status'] == 'trained'
    assert results['jewelry']['status'] == 'trained'


@pytest.mark.asyncio
async def test_get_learning_recommendations_insufficient_data(learning_service, session):
    """Test recommendations with insufficient data."""
    recommendations = await learning_service.get_learning_recommendations('test_category')
    
    assert recommendations['has_recommendations'] is False
    assert recommendations['reason'] == 'insufficient_data'


@pytest.mark.asyncio
async def test_get_learning_recommendations_with_data(learning_service, session):
    """Test recommendations with sufficient data."""
    # Create category metrics
    metrics = CategoryMetrics(
        category='antiques',
        total_bids=50,
        won_bids=35,
        win_rate=0.7,
        average_roi=0.25,
        sample_size=50,
        recommended_safety_margin=0.18,
        confidence_threshold=0.65
    )
    session.add(metrics)
    session.commit()
    
    recommendations = await learning_service.get_learning_recommendations('antiques')
    
    assert recommendations['has_recommendations'] is True
    assert recommendations['recommended_safety_margin'] == 0.18
    assert recommendations['recommended_confidence_threshold'] == 0.65
    assert recommendations['expected_win_rate'] == 0.7
    assert 'data_quality' in recommendations


@pytest.mark.asyncio
async def test_recommendations_include_warnings(learning_service, session):
    """Test that warnings are included when appropriate."""
    # Create metrics with low win rate
    metrics = CategoryMetrics(
        category='collectibles',
        total_bids=50,
        won_bids=20,
        win_rate=0.4,  # Low win rate
        average_roi=0.05,  # Low ROI
        sample_size=50
    )
    session.add(metrics)
    session.commit()
    
    recommendations = await learning_service.get_learning_recommendations('collectibles')
    
    assert 'warnings' in recommendations
    assert any('win rate' in w.lower() for w in recommendations['warnings'])
    assert any('roi' in w.lower() for w in recommendations['warnings'])


def test_assess_data_quality(learning_service):
    """Test data quality assessment."""
    mock_metrics = Mock()
    
    mock_metrics.sample_size = 150
    assert learning_service._assess_data_quality(mock_metrics) == 'excellent'
    
    mock_metrics.sample_size = 75
    assert learning_service._assess_data_quality(mock_metrics) == 'good'
    
    mock_metrics.sample_size = 30
    assert learning_service._assess_data_quality(mock_metrics) == 'fair'
    
    mock_metrics.sample_size = 5
    assert learning_service._assess_data_quality(mock_metrics) == 'poor'


@pytest.mark.asyncio
async def test_schedule_retraining(learning_service, session):
    """Test scheduled retraining."""
    # Create some outcomes
    for i in range(12):
        outcome = BidOutcome(
            bid_id=i,
            item_id=i,
            user_id=1,
            estimated_value=1000.0,
            target_buy_price=800.0,
            actual_bid_amount=750.0,
            confidence_score=0.7,
            won_auction=True,
            actual_resale_price=950.0,
            category='jewelry'
        )
        session.add(outcome)
    
    session.commit()
    
    summary = await learning_service.schedule_retraining()
    
    assert 'retrained_at' in summary
    assert summary['total_categories'] >= 1
    assert summary['successful'] >= 1
    assert 'details' in summary


@pytest.mark.asyncio
async def test_get_model_performance_report_no_data(learning_service, session):
    """Test performance report with no data."""
    report = await learning_service.get_model_performance_report()
    
    assert report['status'] == 'no_data'
    assert report['categories_tracked'] == 0


@pytest.mark.asyncio
async def test_get_model_performance_report_with_data(learning_service, session):
    """Test performance report with data."""
    # Create category metrics
    metrics1 = CategoryMetrics(
        category='antiques',
        total_bids=50,
        won_bids=35,
        total_profit=5000.0,
        average_roi=0.3,
        average_valuation_accuracy=0.85,
        sample_size=50
    )
    
    metrics2 = CategoryMetrics(
        category='jewelry',
        total_bids=30,
        won_bids=25,
        total_profit=3000.0,
        average_roi=0.25,
        average_valuation_accuracy=0.80,
        sample_size=30
    )
    
    session.add(metrics1)
    session.add(metrics2)
    session.commit()
    
    report = await learning_service.get_model_performance_report()
    
    assert report['status'] == 'success'
    assert report['categories_tracked'] == 2
    assert 'aggregate_stats' in report
    assert report['aggregate_stats']['total_bids'] == 80
    assert report['aggregate_stats']['total_won'] == 60
    assert 'best_category' in report
    assert 'worst_category' in report


@pytest.mark.asyncio
async def test_learning_rate_adjustment(learning_service, session):
    """Test that learning rate properly adjusts parameters."""
    # Create initial metrics
    initial_margin = 0.15
    initial_confidence = 0.60
    
    metrics = CategoryMetrics(
        category='test',
        recommended_safety_margin=initial_margin,
        confidence_threshold=initial_confidence
    )
    session.add(metrics)
    session.commit()
    
    # Apply update with different values
    new_margin = 0.25
    new_confidence = 0.70
    
    await learning_service._update_category_learning_params(
        'test',
        new_margin,
        new_confidence
    )
    
    # Retrieve updated metrics
    statement = select(CategoryMetrics).where(CategoryMetrics.category == 'test')
    updated = session.exec(statement).first()
    
    # With learning rate 0.1:
    # new_value = old_value * 0.9 + new_value * 0.1
    expected_margin = initial_margin * 0.9 + new_margin * 0.1
    expected_confidence = initial_confidence * 0.9 + new_confidence * 0.1
    
    assert updated.recommended_safety_margin == pytest.approx(expected_margin)
    assert updated.confidence_threshold == pytest.approx(expected_confidence)


@pytest.mark.asyncio
async def test_optimal_margin_with_losses(learning_service):
    """Test margin calculation includes safety buffer."""
    outcomes = [
        Mock(actual_resale_price=1000.0, target_buy_price=900.0, won_auction=True),
        Mock(actual_resale_price=950.0, target_buy_price=850.0, won_auction=True)
    ]
    
    margin = await learning_service._calculate_optimal_margin(outcomes)
    
    # Should add 10% safety buffer
    # So margin should be slightly higher than median optimal
    assert margin > 0.1


@pytest.mark.asyncio
async def test_confidence_buckets(learning_service):
    """Test confidence bucketing in optimal confidence calculation."""
    outcomes = [
        # High confidence bucket (>= 0.7)
        Mock(confidence_score=0.9, gross_profit=200.0),
        Mock(confidence_score=0.8, gross_profit=180.0),
        Mock(confidence_score=0.75, gross_profit=150.0),
        # Medium confidence bucket (0.5-0.7)
        Mock(confidence_score=0.65, gross_profit=100.0),
        Mock(confidence_score=0.6, gross_profit=-20.0),
        # Low confidence bucket (< 0.5)
        Mock(confidence_score=0.4, gross_profit=-50.0),
        Mock(confidence_score=0.3, gross_profit=-100.0)
    ]
    
    confidence = await learning_service._calculate_optimal_confidence(outcomes)
    
    # High confidence bucket has 100% win rate, so should recommend 0.7
    assert confidence == 0.7


@pytest.mark.asyncio
async def test_optimal_margin_clamped(learning_service):
    """Test that optimal margin is clamped to valid range."""
    # Test very high margins
    outcomes = [
        Mock(actual_resale_price=1000.0, target_buy_price=100.0, won_auction=True)
    ]
    
    margin = await learning_service._calculate_optimal_margin(outcomes)
    
    # Should be clamped to maximum 40%
    assert margin <= 0.40
    
    # Test very low margins  
    outcomes = [
        Mock(actual_resale_price=1000.0, target_buy_price=990.0, won_auction=True)
    ]
    
    margin = await learning_service._calculate_optimal_margin(outcomes)
    
    # Should be at least 5%
    assert margin >= 0.05
