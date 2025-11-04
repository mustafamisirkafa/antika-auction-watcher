"""
Tests for Sprint 5: Learning-Based Bid Policy
"""

import pytest
import math
from backend.services.bid_policy import (
    BidPolicyEngine,
    BidDecision,
    EMA_ALPHA,
    CACHE_FRESHNESS_DECAY_FACTOR
)


@pytest.fixture
def engine():
    """Bid policy engine instance."""
    return BidPolicyEngine()


class TestConfidenceAdjustment:
    """Test cache-based confidence adjustment."""
    
    def test_fresh_cache_no_adjustment(self, engine):
        """Fresh cache (0 minutes) should have weight ~1.0."""
        adjusted = engine._adjust_confidence_for_cache(0.8, cache_age=0)
        assert abs(adjusted - 0.8) < 0.01  # ~0.8
    
    def test_15min_cache_moderate_adjustment(self, engine):
        """15-minute old cache should reduce confidence."""
        adjusted = engine._adjust_confidence_for_cache(0.8, cache_age=900)  # 15 min
        
        expected_weight = math.exp(-15 / CACHE_FRESHNESS_DECAY_FACTOR)
        expected = 0.8 * expected_weight
        
        assert abs(adjusted - expected) < 0.01
        assert adjusted < 0.8  # Should be reduced
    
    def test_30min_cache_significant_adjustment(self, engine):
        """30-minute old cache should significantly reduce confidence."""
        adjusted = engine._adjust_confidence_for_cache(0.8, cache_age=1800)  # 30 min
        
        # weight = exp(-30/30) = exp(-1) ? 0.368
        # adjusted = 0.8 * 0.368 ? 0.294
        assert 0.25 < adjusted < 0.35
    
    def test_60min_cache_major_adjustment(self, engine):
        """60-minute old cache should drastically reduce confidence."""
        adjusted = engine._adjust_confidence_for_cache(0.8, cache_age=3600)  # 60 min
        
        # weight = exp(-60/30) = exp(-2) ? 0.135
        # adjusted = 0.8 * 0.135 ? 0.108
        assert adjusted < 0.15
    
    def test_none_cache_age_no_adjustment(self, engine):
        """None cache age should not adjust confidence."""
        adjusted = engine._adjust_confidence_for_cache(0.8, cache_age=None)
        assert adjusted == 0.8


class TestEMASmoothing:
    """Test Exponential Moving Average smoothing."""
    
    def test_first_observation_no_smoothing(self, engine):
        """First observation should not be smoothed."""
        smoothed = engine._apply_ema_smoothing("item_123", 0.8)
        assert smoothed == 0.8
    
    def test_second_observation_applies_ema(self, engine):
        """Second observation should apply EMA formula."""
        # First observation
        engine._apply_ema_smoothing("item_123", 0.8)
        
        # Second observation
        smoothed = engine._apply_ema_smoothing("item_123", 0.6)
        
        # EMA = alpha * current + (1 - alpha) * previous
        # EMA = 0.2 * 0.6 + 0.8 * 0.8 = 0.12 + 0.64 = 0.76
        expected = EMA_ALPHA * 0.6 + (1 - EMA_ALPHA) * 0.8
        assert abs(smoothed - expected) < 0.01
    
    def test_ema_reduces_volatility(self, engine):
        """EMA should reduce volatility in confidence."""
        # Establish baseline
        engine._apply_ema_smoothing("item_123", 0.8)
        
        # Sudden drop
        smoothed = engine._apply_ema_smoothing("item_123", 0.3)
        
        # EMA should be between 0.3 and 0.8 (smoothed)
        assert 0.3 < smoothed < 0.8
    
    def test_get_confidence_history(self, engine):
        """Should retrieve confidence history for item."""
        engine._apply_ema_smoothing("item_123", 0.8)
        
        history = engine.get_confidence_history("item_123")
        assert history == 0.8
    
    def test_reset_confidence_history(self, engine):
        """Should reset confidence history."""
        engine._apply_ema_smoothing("item_123", 0.8)
        engine.reset_confidence_history("item_123")
        
        history = engine.get_confidence_history("item_123")
        assert history is None


class TestBidDecision:
    """Test bid decision logic."""
    
    def test_approve_bid_within_limits(self, engine):
        """Should approve bid within all limits."""
        context = {"current_price": 1000, "item_id": "item_123", "auction_id": "A1"}
        rule = {"max_bid": 2000, "min_confidence": 0.7, "step": 50, "mode": "auto"}
        
        decision = engine.compute_next_bid(
            context=context,
            rule=rule,
            rec_max_bid=1800,
            base_confidence=0.85,
            cache_age=30,
            seller_trust_score=0.95
        )
        
        assert decision.ok is True
        assert decision.next_bid == 1050  # 1000 + 50
        assert decision.reason == "approved"
        assert decision.mode == "auto"
    
    def test_deny_low_confidence(self, engine):
        """Should deny bid if adjusted confidence too low."""
        context = {"current_price": 1000, "item_id": "item_123", "auction_id": "A1"}
        rule = {"max_bid": 2000, "min_confidence": 0.8, "step": 50}
        
        decision = engine.compute_next_bid(
            context=context,
            rule=rule,
            rec_max_bid=1800,
            base_confidence=0.5,  # Low confidence
            cache_age=3600,  # Stale cache reduces it further
            seller_trust_score=0.7
        )
        
        assert decision.ok is False
        assert decision.reason == "confidence_too_low"
        assert decision.mode == "hold"
    
    def test_deny_over_user_max(self, engine):
        """Should deny if current price over user max."""
        context = {"current_price": 2100, "item_id": "item_123", "auction_id": "A1"}
        rule = {"max_bid": 2000, "min_confidence": 0.7, "step": 50}
        
        decision = engine.compute_next_bid(
            context=context,
            rule=rule,
            rec_max_bid=2500,
            base_confidence=0.85
        )
        
        assert decision.ok is False
        assert decision.reason == "over_user_max"
    
    def test_deny_over_rec_max(self, engine):
        """Should deny if current price over recommended max."""
        context = {"current_price": 1900, "item_id": "item_123", "auction_id": "A1"}
        rule = {"max_bid": 2500, "min_confidence": 0.7, "step": 50}
        
        decision = engine.compute_next_bid(
            context=context,
            rule=rule,
            rec_max_bid=1800,  # Lower than current price
            base_confidence=0.85
        )
        
        assert decision.ok is False
        assert decision.reason == "over_rec_max"
    
    def test_stop_loss_triggered(self, engine):
        """Should trigger stop-loss if configured."""
        context = {"current_price": 1600, "item_id": "item_123", "auction_id": "A1"}
        rule = {
            "max_bid": 2000,
            "min_confidence": 0.7,
            "step": 50,
            "stop_loss_pct": 10  # 10% stop-loss
        }
        
        # rec_max_bid = 1700, stop_loss = 1700 * 0.9 = 1530
        # proposed_bid = 1650 > 1530 ? trigger stop-loss
        decision = engine.compute_next_bid(
            context=context,
            rule=rule,
            rec_max_bid=1700,
            base_confidence=0.85
        )
        
        assert decision.ok is False
        assert decision.reason == "stop_loss_triggered"
    
    def test_seller_trust_reduces_confidence(self, engine):
        """Low seller trust should reduce confidence."""
        context = {"current_price": 1000, "item_id": "item_123", "auction_id": "A1"}
        rule = {"max_bid": 2000, "min_confidence": 0.75, "step": 50}
        
        decision = engine.compute_next_bid(
            context=context,
            rule=rule,
            rec_max_bid=1800,
            base_confidence=0.85,
            cache_age=0,
            seller_trust_score=0.5  # Low trust
        )
        
        # adjusted = 0.85 * 1.0 (fresh) * 0.5 (trust) = 0.425
        # 0.425 < 0.75 ? deny
        assert decision.ok is False
        assert decision.reason == "confidence_too_low"
        assert decision.seller_trust == 0.5


class TestBidDecisionMetadata:
    """Test bid decision metadata tracking."""
    
    def test_decision_includes_cache_age(self, engine):
        """Decision should include cache age metadata."""
        context = {"current_price": 1000, "item_id": "item_123", "auction_id": "A1"}
        rule = {"max_bid": 2000, "min_confidence": 0.7, "step": 50}
        
        decision = engine.compute_next_bid(
            context=context,
            rule=rule,
            rec_max_bid=1800,
            base_confidence=0.85,
            cache_age=600
        )
        
        assert decision.cache_age == 600
    
    def test_decision_includes_confidence_breakdown(self, engine):
        """Decision should include confidence breakdown."""
        context = {"current_price": 1000, "item_id": "item_123", "auction_id": "A1"}
        rule = {"max_bid": 2000, "min_confidence": 0.7, "step": 50}
        
        decision = engine.compute_next_bid(
            context=context,
            rule=rule,
            rec_max_bid=1800,
            base_confidence=0.85,
            cache_age=600,
            seller_trust_score=0.9
        )
        
        assert decision.base_confidence == 0.85
        assert decision.adjusted_confidence is not None
        assert decision.seller_trust == 0.9
        assert decision.confidence is not None  # Final EMA-smoothed confidence


class TestProposedBidCalculation:
    """Test proposed bid calculation."""
    
    def test_proposed_bid_respects_step(self, engine):
        """Proposed bid should add step to current price."""
        context = {"current_price": 1000, "item_id": "item_123", "auction_id": "A1"}
        rule = {"max_bid": 2000, "min_confidence": 0.7, "step": 100}
        
        decision = engine.compute_next_bid(
            context=context,
            rule=rule,
            rec_max_bid=1800,
            base_confidence=0.85
        )
        
        assert decision.next_bid == 1100  # 1000 + 100
    
    def test_proposed_bid_capped_at_user_max(self, engine):
        """Proposed bid should not exceed user max."""
        context = {"current_price": 1980, "item_id": "item_123", "auction_id": "A1"}
        rule = {"max_bid": 2000, "min_confidence": 0.7, "step": 50}
        
        decision = engine.compute_next_bid(
            context=context,
            rule=rule,
            rec_max_bid=2500,
            base_confidence=0.85
        )
        
        assert decision.ok is True
        assert decision.next_bid == 2000  # Capped at user_max
    
    def test_proposed_bid_capped_at_rec_max(self, engine):
        """Proposed bid should not exceed recommended max."""
        context = {"current_price": 1780, "item_id": "item_123", "auction_id": "A1"}
        rule = {"max_bid": 2500, "min_confidence": 0.7, "step": 50}
        
        decision = engine.compute_next_bid(
            context=context,
            rule=rule,
            rec_max_bid=1800,
            base_confidence=0.85
        )
        
        assert decision.ok is True
        assert decision.next_bid == 1800  # Capped at rec_max


# Run with: pytest backend/tests/test_bid_policy.py -v --cov=backend/services/bid_policy
