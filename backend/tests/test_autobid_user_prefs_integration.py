"""
Integration tests for AutoBid with User Preferences (Phase 14).
Tests that BidPolicy respects user seller preferences.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.services.bid_policy import BidPolicy


@pytest.fixture
def mock_db():
    """Mock database session."""
    return MagicMock()


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock()
    return redis


@pytest.fixture
def bid_policy(mock_db, mock_redis):
    """Create BidPolicy instance."""
    return BidPolicy(mock_db, mock_redis)


@pytest.mark.asyncio
async def test_bid_blocked_by_user_blocklist(bid_policy, mock_redis):
    """Test that bid is blocked when seller is in user blocklist."""
    import json
    
    # Mock user preferences with seller in blocklist
    user_prefs = {
        "user_id": 1,
        "team_id": 1,
        "allowlist": [],
        "blocklist": ["bad-seller:ebay"]
    }
    mock_redis.get.return_value = json.dumps(user_prefs)
    
    valuation = {
        "rec_max_bid": 1000,
        "confidence": 0.8,
        "risk_level": "medium"
    }
    
    user_rules = {
        "user_id": 1,
        "mode": "auto",
        "max_bid": 1500,
        "min_confidence": 0.6
    }
    
    decision = await bid_policy.evaluate_bid_decision(
        team_id=1,
        auction_id="A1",
        item_id="I1",
        current_price=500,
        valuation=valuation,
        user_rules=user_rules,
        seller_id="bad-seller",
        source="ebay"
    )
    
    assert decision["ok"] is False
    assert decision["blocked_by"] == "user_preference"
    assert "blocklist" in decision["reason"].lower() or "blocked" in decision["reason"].lower()


@pytest.mark.asyncio
async def test_bid_allowed_with_empty_allowlist(bid_policy, mock_redis):
    """Test that bid is allowed when allowlist is empty (default allow mode)."""
    import json
    
    # Mock user preferences with empty lists
    user_prefs = {
        "user_id": 1,
        "team_id": 1,
        "allowlist": [],
        "blocklist": []
    }
    mock_redis.get.return_value = json.dumps(user_prefs)
    
    valuation = {
        "rec_max_bid": 1000,
        "confidence": 0.8,
        "risk_level": "medium",
        "current_price": 500
    }
    
    user_rules = {
        "user_id": 1,
        "mode": "shadow",
        "max_bid": 1500,
        "min_confidence": 0.6
    }
    
    decision = await bid_policy.evaluate_bid_decision(
        team_id=1,
        auction_id="A1",
        item_id="I1",
        current_price=500,
        valuation=valuation,
        user_rules=user_rules,
        seller_id="any-seller",
        source="ebay"
    )
    
    # Should pass user preference check and proceed to other evaluations
    assert decision.get("blocked_by") != "user_preference"


@pytest.mark.asyncio
async def test_bid_blocked_not_in_allowlist(bid_policy, mock_redis):
    """Test that bid is blocked when seller not in allowlist (restricted mode)."""
    import json
    
    # Mock user preferences with allowlist (restricted mode)
    user_prefs = {
        "user_id": 1,
        "team_id": 1,
        "allowlist": ["trusted-seller:ebay"],
        "blocklist": []
    }
    mock_redis.get.return_value = json.dumps(user_prefs)
    
    valuation = {
        "rec_max_bid": 1000,
        "confidence": 0.8,
        "risk_level": "medium"
    }
    
    user_rules = {
        "user_id": 1,
        "mode": "auto",
        "max_bid": 1500,
        "min_confidence": 0.6
    }
    
    decision = await bid_policy.evaluate_bid_decision(
        team_id=1,
        auction_id="A1",
        item_id="I1",
        current_price=500,
        valuation=valuation,
        user_rules=user_rules,
        seller_id="unknown-seller",
        source="ebay"
    )
    
    assert decision["ok"] is False
    assert decision["blocked_by"] == "user_preference"
    assert "allowlist" in decision["reason"].lower() or "not in" in decision["reason"].lower()


@pytest.mark.asyncio
async def test_bid_allowed_in_allowlist(bid_policy, mock_redis):
    """Test that bid proceeds when seller is in allowlist."""
    import json
    
    # Mock user preferences with seller in allowlist
    user_prefs = {
        "user_id": 1,
        "team_id": 1,
        "allowlist": ["trusted-seller:ebay"],
        "blocklist": []
    }
    mock_redis.get.return_value = json.dumps(user_prefs)
    
    valuation = {
        "rec_max_bid": 1000,
        "confidence": 0.8,
        "risk_level": "medium",
        "current_price": 500
    }
    
    user_rules = {
        "user_id": 1,
        "mode": "shadow",
        "max_bid": 1500,
        "min_confidence": 0.6
    }
    
    decision = await bid_policy.evaluate_bid_decision(
        team_id=1,
        auction_id="A1",
        item_id="I1",
        current_price=500,
        valuation=valuation,
        user_rules=user_rules,
        seller_id="trusted-seller",
        source="ebay"
    )
    
    # Should pass user preference check
    assert decision.get("blocked_by") != "user_preference"


@pytest.mark.asyncio
async def test_blocklist_priority_over_allowlist(bid_policy, mock_redis):
    """Test that blocklist has priority over allowlist."""
    import json
    
    # Mock user preferences with seller in BOTH lists (shouldn't happen, but test priority)
    user_prefs = {
        "user_id": 1,
        "team_id": 1,
        "allowlist": ["seller-x:ebay"],
        "blocklist": ["seller-x:ebay"]  # Also in blocklist
    }
    mock_redis.get.return_value = json.dumps(user_prefs)
    
    valuation = {
        "rec_max_bid": 1000,
        "confidence": 0.8,
        "risk_level": "medium"
    }
    
    user_rules = {
        "user_id": 1,
        "mode": "auto",
        "max_bid": 1500,
        "min_confidence": 0.6
    }
    
    decision = await bid_policy.evaluate_bid_decision(
        team_id=1,
        auction_id="A1",
        item_id="I1",
        current_price=500,
        valuation=valuation,
        user_rules=user_rules,
        seller_id="seller-x",
        source="ebay"
    )
    
    # Blocklist should have priority
    assert decision["ok"] is False
    assert decision["blocked_by"] == "user_preference"


@pytest.mark.asyncio
async def test_bid_allowed_no_user_prefs_cached(bid_policy, mock_redis):
    """Test that bid is allowed when no user preferences are cached (fail open)."""
    # Mock Redis returning None (no cached preferences)
    mock_redis.get.return_value = None
    
    valuation = {
        "rec_max_bid": 1000,
        "confidence": 0.8,
        "risk_level": "medium",
        "current_price": 500
    }
    
    user_rules = {
        "user_id": 1,
        "mode": "shadow",
        "max_bid": 1500,
        "min_confidence": 0.6
    }
    
    decision = await bid_policy.evaluate_bid_decision(
        team_id=1,
        auction_id="A1",
        item_id="I1",
        current_price=500,
        valuation=valuation,
        user_rules=user_rules,
        seller_id="any-seller",
        source="ebay"
    )
    
    # Should not be blocked by user preferences (fail open)
    assert decision.get("blocked_by") != "user_preference"


@pytest.mark.asyncio
async def test_bid_without_seller_info_skips_preference_check(bid_policy, mock_redis):
    """Test that preference check is skipped when seller info not provided."""
    valuation = {
        "rec_max_bid": 1000,
        "confidence": 0.8,
        "risk_level": "medium",
        "current_price": 500
    }
    
    user_rules = {
        "user_id": 1,
        "mode": "shadow",
        "max_bid": 1500,
        "min_confidence": 0.6
    }
    
    decision = await bid_policy.evaluate_bid_decision(
        team_id=1,
        auction_id="A1",
        item_id="I1",
        current_price=500,
        valuation=valuation,
        user_rules=user_rules,
        seller_id=None,  # No seller info
        source=None
    )
    
    # Should not check preferences and not be blocked by them
    assert decision.get("blocked_by") != "user_preference"
    mock_redis.get.assert_not_called()
