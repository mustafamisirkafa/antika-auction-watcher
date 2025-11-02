"""
Test suite for Profit Advisor Service (Phase 9).
"""
import pytest
from datetime import datetime, timedelta
from sqlmodel import Session
import asyncio

from backend.models.profit import AuctionItem, ProfitEstimate, MarketReference
from backend.services.profit_advisor import ProfitAdvisorService
from backend.db.models import User
from backend.models.team_models import Team


@pytest.fixture
def test_user(session: Session):
    """Create a test user."""
    user = User(email="test@example.com", username="testuser", hashed_password="hashed")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def test_team(session: Session, test_user: User):
    """Create a test team."""
    team = Team(name="Test Team", owner_id=test_user.id, plan_code="PRO")
    session.add(team)
    session.commit()
    session.refresh(team)
    return team


@pytest.fixture
def auction_item(session: Session, test_team: Team):
    """Create a test auction item."""
    item = AuctionItem(
        lot_id="LOT-2025-001",
        title="19th Century Silver Candleholder",
        category="silver",
        starting_price=800.0,
        auction_date=datetime.utcnow() + timedelta(days=7),
        source="Christie's",
        team_id=test_team.id
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@pytest.mark.asyncio
async def test_analyze_item(session: Session, auction_item: AuctionItem):
    """Test analyzing a single auction item."""
    advisor = ProfitAdvisorService(session)
    
    estimate = await advisor.analyze_item(auction_item)
    
    assert estimate.id is not None
    assert estimate.auction_item_id == auction_item.id
    assert estimate.estimated_value > 0
    assert estimate.recommended_max_bid > 0
    assert 0 <= estimate.confidence <= 1
    assert estimate.risk_level in ['low', 'medium', 'high']


@pytest.mark.asyncio
async def test_market_references_created(session: Session, auction_item: AuctionItem):
    """Test that market references are saved."""
    advisor = ProfitAdvisorService(session)
    
    await advisor.analyze_item(auction_item)
    
    # Check market references were created
    from sqlmodel import select
    statement = select(MarketReference).where(
        MarketReference.auction_item_id == auction_item.id
    )
    references = session.exec(statement).all()
    
    assert len(references) > 0
    assert all(ref.source in ['ebay', 'etsy', 'sahibinden', 'letgo'] for ref in references)


@pytest.mark.asyncio
async def test_profit_margin_calculation(session: Session, auction_item: AuctionItem):
    """Test profit margin calculation."""
    advisor = ProfitAdvisorService(session)
    
    estimate = await advisor.analyze_item(auction_item)
    
    # Profit margin should be reasonable
    assert -0.5 <= estimate.profit_margin <= 1.0
    
    # Recommended bid should be below market value (for profit)
    assert estimate.recommended_max_bid <= estimate.estimated_value


@pytest.mark.asyncio
async def test_confidence_score(session: Session, auction_item: AuctionItem):
    """Test confidence score calculation."""
    advisor = ProfitAdvisorService(session)
    
    estimate = await advisor.analyze_item(auction_item)
    
    # Confidence should be between 0 and 1
    assert 0 <= estimate.confidence <= 1
    
    # Higher liquidity should correlate with higher confidence
    assert 0 <= estimate.liquidity_avg <= 1


@pytest.mark.asyncio
async def test_risk_level_determination(session: Session, auction_item: AuctionItem):
    """Test risk level determination."""
    advisor = ProfitAdvisorService(session)
    
    estimate = await advisor.analyze_item(auction_item)
    
    # Risk level should be valid
    assert estimate.risk_level in ['low', 'medium', 'high']
    
    # High confidence + good margin should trend toward low risk
    if estimate.confidence >= 0.8 and estimate.profit_margin >= 0.15:
        assert estimate.risk_level in ['low', 'medium']


@pytest.mark.asyncio
async def test_cached_estimate(session: Session, auction_item: AuctionItem):
    """Test that recent estimates are cached."""
    advisor = ProfitAdvisorService(session)
    
    # First analysis
    estimate1 = await advisor.analyze_item(auction_item)
    
    # Second analysis (should use cached)
    estimate2 = await advisor.analyze_item(auction_item, force_refresh=False)
    
    # Should return same estimate
    assert estimate1.id == estimate2.id


@pytest.mark.asyncio
async def test_force_refresh(session: Session, auction_item: AuctionItem):
    """Test force refresh of estimates."""
    advisor = ProfitAdvisorService(session)
    
    # First analysis
    estimate1 = await advisor.analyze_item(auction_item)
    
    # Force refresh
    estimate2 = await advisor.analyze_item(auction_item, force_refresh=True)
    
    # Should create new estimate
    assert estimate1.id != estimate2.id


@pytest.mark.asyncio
async def test_low_confidence_estimate(session: Session, test_team: Team):
    """Test low confidence estimate when no market data."""
    # This would require mocking the market fetcher to return empty results
    # For now, we'll just verify the method exists and handles edge cases
    advisor = ProfitAdvisorService(session)
    
    item = AuctionItem(
        lot_id="LOT-2025-002",
        title="Rare Unknown Item",
        category="unknown",
        starting_price=100.0,
        auction_date=datetime.utcnow() + timedelta(days=1),
        source="Unknown",
        team_id=test_team.id
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    
    estimate = await advisor.analyze_item(item)
    
    # Should still create an estimate, even if low confidence
    assert estimate is not None
    assert estimate.confidence >= 0


@pytest.mark.asyncio
async def test_analyze_team_items(session: Session, test_team: Team):
    """Test analyzing all items for a team."""
    # Create multiple items
    items = []
    for i in range(3):
        item = AuctionItem(
            lot_id=f"LOT-2025-{i:03d}",
            title=f"Test Item {i}",
            category="ceramics",
            starting_price=100.0 * (i + 1),
            auction_date=datetime.utcnow() + timedelta(days=i + 1),
            source="Test",
            team_id=test_team.id
        )
        session.add(item)
        items.append(item)
    
    session.commit()
    
    advisor = ProfitAdvisorService(session)
    estimates = await advisor.analyze_team_items(test_team.id)
    
    assert len(estimates) == 3
    assert all(isinstance(e, ProfitEstimate) for e in estimates)


@pytest.mark.asyncio
async def test_get_team_estimates(session: Session, test_team: Team, auction_item: AuctionItem):
    """Test retrieving team estimates with filters."""
    advisor = ProfitAdvisorService(session)
    
    # Create estimate
    await advisor.analyze_item(auction_item)
    
    # Get all estimates
    estimates = advisor.get_team_estimates(test_team.id)
    assert len(estimates) > 0
    
    # Filter by confidence
    high_conf = advisor.get_team_estimates(test_team.id, min_confidence=0.8)
    assert all(e.confidence >= 0.8 for e in high_conf)
    
    # Filter by risk
    low_risk = advisor.get_team_estimates(test_team.id, max_risk='low')
    assert all(e.risk_level == 'low' for e in low_risk)


@pytest.mark.asyncio
async def test_estimate_expiration(session: Session, auction_item: AuctionItem):
    """Test that estimates have expiration dates."""
    advisor = ProfitAdvisorService(session)
    
    estimate = await advisor.analyze_item(auction_item)
    
    assert estimate.expires_at is not None
    assert estimate.expires_at > datetime.utcnow()
