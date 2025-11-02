"""Tests for bidding engine."""
import pytest
from backend.services.bidding.agent import BiddingAgent, BidMode, BidDecision


def test_bidding_agent_initialization():
    """Test bidding agent initialization."""
    agent = BiddingAgent(mode=BidMode.AUTO)
    
    assert agent.mode == BidMode.AUTO
    assert len(agent.recent_bids) == 0


def test_should_bid_success():
    """Test successful bid decision."""
    agent = BiddingAgent()
    
    decision, reason = agent.should_bid(
        item_id=1,
        current_price=100.0,
        target_buy_price=200.0,
        confidence_score=0.8
    )
    
    assert decision == BidDecision.BID
    assert "confidence" in reason.lower()


def test_should_bid_price_too_high():
    """Test bid rejection when price is too high."""
    agent = BiddingAgent()
    
    decision, reason = agent.should_bid(
        item_id=1,
        current_price=250.0,
        target_buy_price=200.0,
        confidence_score=0.8
    )
    
    assert decision == BidDecision.SKIP
    assert "too high" in reason.lower()


def test_should_bid_low_confidence():
    """Test bid rejection due to low confidence."""
    agent = BiddingAgent()
    
    decision, reason = agent.should_bid(
        item_id=1,
        current_price=100.0,
        target_buy_price=200.0,
        confidence_score=0.3
    )
    
    assert decision == BidDecision.SKIP
    assert "confidence" in reason.lower()


def test_should_bid_duplicate_prevention():
    """Test duplicate bid prevention."""
    agent = BiddingAgent()
    
    # Record a bid
    agent.record_bid(item_id=1)
    
    # Try to bid again immediately
    decision, reason = agent.should_bid(
        item_id=1,
        current_price=100.0,
        target_buy_price=200.0,
        confidence_score=0.8
    )
    
    assert decision == BidDecision.SKIP
    assert "duplicate" in reason.lower()


def test_calculate_bid_amount():
    """Test bid amount calculation."""
    agent = BiddingAgent()
    
    bid_amount = agent.calculate_bid_amount(
        current_price=100.0,
        target_buy_price=200.0,
        bid_increment=10.0
    )
    
    assert bid_amount == 110.0


def test_calculate_bid_amount_near_target():
    """Test bid amount when near target price."""
    agent = BiddingAgent()
    
    bid_amount = agent.calculate_bid_amount(
        current_price=195.0,
        target_buy_price=200.0,
        bid_increment=10.0
    )
    
    # Should not exceed target
    assert bid_amount <= 200.0


def test_requires_confirmation():
    """Test confirmation requirement based on mode."""
    auto_agent = BiddingAgent(mode=BidMode.AUTO)
    semi_auto_agent = BiddingAgent(mode=BidMode.SEMI_AUTO)
    
    assert auto_agent.requires_confirmation() is False
    assert semi_auto_agent.requires_confirmation() is True
