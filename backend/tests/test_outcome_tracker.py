"""Comprehensive tests for outcome tracker."""
import pytest
from datetime import datetime, timedelta
from backend.services.analytics.outcome_tracker import OutcomeTracker
from backend.db.analytics_models import BidOutcome, CategoryMetrics
from backend.db.models import Bid, Item, User


@pytest.fixture
def outcome_tracker(session):
    """Create outcome tracker instance."""
    return OutcomeTracker(session)


@pytest.fixture
def test_user(session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def test_item(session):
    """Create a test item."""
    item = Item(
        title="Test Item",
        category="antiques",
        seller_name="Seller",
        current_price=100.0,
        estimated_value=500.0,
        target_buy_price=400.0,
        confidence_score=0.75
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@pytest.fixture
def test_bid(session, test_user, test_item):
    """Create a test bid."""
    bid = Bid(
        item_id=test_item.id,
        user_id=test_user.id,
        bid_amount=380.0,
        bid_type="semi_auto",
        success=True
    )
    session.add(bid)
    session.commit()
    session.refresh(bid)
    return bid


@pytest.mark.asyncio
async def test_record_bid_outcome_won_and_resold(
    outcome_tracker,
    session,
    test_bid,
    test_item
):
    """Test recording successful outcome with resale."""
    outcome = await outcome_tracker.record_bid_outcome(
        bid_id=test_bid.id,
        won_auction=True,
        actual_resale_price=550.0
    )
    
    assert outcome.bid_id == test_bid.id
    assert outcome.won_auction is True
    assert outcome.actual_resale_price == 550.0
    
    # Check profitability metrics
    assert outcome.gross_profit == 550.0 - 380.0  # 170.0
    assert outcome.gross_profit == 170.0
    assert outcome.profit_margin is not None
    assert outcome.roi is not None
    assert outcome.valuation_accuracy is not None


@pytest.mark.asyncio
async def test_record_bid_outcome_won_no_resale(
    outcome_tracker,
    test_bid
):
    """Test recording won auction without resale data."""
    outcome = await outcome_tracker.record_bid_outcome(
        bid_id=test_bid.id,
        won_auction=True,
        actual_resale_price=None
    )
    
    assert outcome.won_auction is True
    assert outcome.actual_resale_price is None
    assert outcome.gross_profit is None
    assert outcome.roi is None


@pytest.mark.asyncio
async def test_record_bid_outcome_lost(outcome_tracker, test_bid):
    """Test recording lost auction."""
    outcome = await outcome_tracker.record_bid_outcome(
        bid_id=test_bid.id,
        won_auction=False
    )
    
    assert outcome.won_auction is False
    assert outcome.gross_profit is None


@pytest.mark.asyncio
async def test_record_bid_outcome_invalid_bid(outcome_tracker):
    """Test recording outcome for non-existent bid."""
    with pytest.raises(ValueError, match="Bid .* not found"):
        await outcome_tracker.record_bid_outcome(
            bid_id=99999,
            won_auction=True
        )


@pytest.mark.asyncio
async def test_get_outcome_by_bid(outcome_tracker, session, test_bid):
    """Test retrieving outcome by bid ID."""
    # Record an outcome
    await outcome_tracker.record_bid_outcome(test_bid.id, True, 500.0)
    
    # Retrieve it
    outcome = await outcome_tracker.get_outcome_by_bid(test_bid.id)
    
    assert outcome is not None
    assert outcome.bid_id == test_bid.id


@pytest.mark.asyncio
async def test_get_outcome_by_bid_not_found(outcome_tracker):
    """Test retrieving non-existent outcome."""
    outcome = await outcome_tracker.get_outcome_by_bid(99999)
    
    assert outcome is None


@pytest.mark.asyncio
async def test_get_category_performance(outcome_tracker, session, test_bid):
    """Test getting category performance metrics."""
    # Create multiple outcomes
    for i in range(5):
        await outcome_tracker.record_bid_outcome(
            test_bid.id,
            won_auction=(i < 3),  # 3 wins, 2 losses
            actual_resale_price=500.0 if i < 3 else None
        )
    
    performance = await outcome_tracker.get_category_performance('antiques')
    
    assert performance['category'] == 'antiques'
    assert performance['total_bids'] >= 5
    assert performance['won_bids'] >= 3


@pytest.mark.asyncio
async def test_get_category_performance_no_data(outcome_tracker):
    """Test category performance with no data."""
    performance = await outcome_tracker.get_category_performance('nonexistent')
    
    assert performance['total_bids'] == 0
    assert performance['win_rate'] == 0.0


@pytest.mark.asyncio
async def test_get_user_performance(outcome_tracker, session, test_user, test_bid):
    """Test getting user performance metrics."""
    # Record outcomes
    await outcome_tracker.record_bid_outcome(test_bid.id, True, 500.0)
    
    performance = await outcome_tracker.get_user_performance(test_user.id)
    
    assert performance['user_id'] == test_user.id
    assert performance['total_bids'] >= 1
    assert performance['won_bids'] >= 1


@pytest.mark.asyncio
async def test_get_user_performance_no_data(outcome_tracker):
    """Test user performance with no data."""
    performance = await outcome_tracker.get_user_performance(99999)
    
    assert performance['total_bids'] == 0
    assert performance['total_profit'] == 0.0


@pytest.mark.asyncio
async def test_get_time_series_metrics(outcome_tracker, session, test_bid, test_item):
    """Test time-series metrics generation."""
    # Create outcomes over multiple days
    base_time = datetime.utcnow()
    
    for i in range(5):
        outcome = BidOutcome(
            bid_id=test_bid.id,
            item_id=test_item.id,
            user_id=test_bid.user_id,
            estimated_value=500.0,
            target_buy_price=400.0,
            actual_bid_amount=380.0,
            confidence_score=0.7,
            won_auction=True,
            gross_profit=100.0,
            category='antiques',
            created_at=base_time - timedelta(days=i)
        )
        session.add(outcome)
    
    session.commit()
    
    time_series = await outcome_tracker.get_time_series_metrics(days=7)
    
    assert isinstance(time_series, list)
    assert len(time_series) > 0
    
    for daily_metrics in time_series:
        assert 'date' in daily_metrics
        assert 'total_bids' in daily_metrics
        assert 'won_bids' in daily_metrics


@pytest.mark.asyncio
async def test_get_time_series_with_category_filter(
    outcome_tracker,
    session,
    test_bid,
    test_item
):
    """Test time-series with category filter."""
    outcome = BidOutcome(
        bid_id=test_bid.id,
        item_id=test_item.id,
        user_id=test_bid.user_id,
        estimated_value=500.0,
        target_buy_price=400.0,
        actual_bid_amount=380.0,
        confidence_score=0.7,
        category='antiques'
    )
    session.add(outcome)
    session.commit()
    
    time_series = await outcome_tracker.get_time_series_metrics(
        days=7,
        category='antiques'
    )
    
    assert isinstance(time_series, list)


@pytest.mark.asyncio
async def test_export_outcomes_csv(outcome_tracker, session, test_bid, test_item):
    """Test CSV export functionality."""
    # Create outcome
    outcome = BidOutcome(
        bid_id=test_bid.id,
        item_id=test_item.id,
        user_id=test_bid.user_id,
        estimated_value=500.0,
        target_buy_price=400.0,
        actual_bid_amount=380.0,
        confidence_score=0.75,
        won_auction=True,
        actual_resale_price=550.0,
        gross_profit=170.0,
        roi=0.447,
        valuation_accuracy=0.90,
        category='antiques'
    )
    session.add(outcome)
    session.commit()
    
    csv_data = await outcome_tracker.export_outcomes_csv()
    
    assert isinstance(csv_data, str)
    assert 'bid_id,item_id,category' in csv_data  # Header
    assert 'antiques' in csv_data  # Data


@pytest.mark.asyncio
async def test_export_outcomes_csv_with_filters(
    outcome_tracker,
    session,
    test_bid,
    test_item
):
    """Test CSV export with category filter."""
    outcome = BidOutcome(
        bid_id=test_bid.id,
        item_id=test_item.id,
        user_id=test_bid.user_id,
        estimated_value=500.0,
        target_buy_price=400.0,
        actual_bid_amount=380.0,
        confidence_score=0.7,
        category='jewelry'
    )
    session.add(outcome)
    session.commit()
    
    csv_data = await outcome_tracker.export_outcomes_csv(category='jewelry')
    
    assert 'jewelry' in csv_data


@pytest.mark.asyncio
async def test_profitability_calculations(outcome_tracker, test_bid):
    """Test profitability metric calculations."""
    outcome = await outcome_tracker.record_bid_outcome(
        bid_id=test_bid.id,
        won_auction=True,
        actual_resale_price=500.0
    )
    
    # Bid amount was 380
    expected_profit = 500.0 - 380.0  # 120.0
    expected_margin = 120.0 / 500.0  # 0.24
    expected_roi = 120.0 / 380.0     # ~0.316
    
    assert outcome.gross_profit == pytest.approx(expected_profit)
    assert outcome.profit_margin == pytest.approx(expected_margin, rel=0.01)
    assert outcome.roi == pytest.approx(expected_roi, rel=0.01)


@pytest.mark.asyncio
async def test_valuation_accuracy_calculation(outcome_tracker, test_bid, test_item):
    """Test valuation accuracy calculation."""
    # Item estimated_value is 500, we'll set resale to 520
    outcome = await outcome_tracker.record_bid_outcome(
        bid_id=test_bid.id,
        won_auction=True,
        actual_resale_price=520.0
    )
    
    # Accuracy should be high (estimate was close)
    assert outcome.valuation_accuracy > 0.9
    assert outcome.valuation_accuracy <= 1.0


@pytest.mark.asyncio
async def test_category_metrics_auto_update(
    outcome_tracker,
    session,
    test_bid
):
    """Test that category metrics are automatically updated."""
    await outcome_tracker.record_bid_outcome(
        test_bid.id,
        True,
        500.0
    )
    
    # Check that category metrics were updated
    from sqlmodel import select
    statement = select(CategoryMetrics).where(
        CategoryMetrics.category == 'antiques'
    )
    metrics = session.exec(statement).first()
    
    # Metrics should have been created/updated
    assert metrics is not None
    assert metrics.total_bids > 0
