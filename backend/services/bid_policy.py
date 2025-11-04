"""
Sprint 5: Learning-Based Bid Policy with Adaptive Confidence

Features:
- Adaptive confidence scoring based on cache freshness
- Seller trust integration
- Exponential Moving Average (EMA) smoothing
- Enhanced audit logging
"""

import math
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# EMA smoothing parameter (alpha)
EMA_ALPHA = 0.2

# Confidence adjustment parameters
CACHE_FRESHNESS_DECAY_FACTOR = 30  # Minutes


@dataclass
class BidDecision:
    """Bid decision with confidence and reasoning."""
    ok: bool
    next_bid: Optional[float]
    reason: str
    mode: str
    confidence: float
    cache_age: Optional[float] = None
    adjusted_confidence: Optional[float] = None
    seller_trust: Optional[float] = None
    base_confidence: Optional[float] = None


class BidPolicyEngine:
    """
    Learning-based bid policy engine with adaptive confidence.
    """
    
    def __init__(self):
        self._confidence_history: Dict[str, float] = {}  # item_id -> EMA confidence
        
    def compute_next_bid(
        self,
        context: Dict[str, Any],
        rule: Dict[str, Any],
        rec_max_bid: float,
        base_confidence: float,
        cache_age: Optional[float] = None,
        seller_trust_score: Optional[float] = None
    ) -> BidDecision:
        """
        Compute next bid with adaptive confidence scoring.
        
        Args:
            context: Current auction context (price, item_id, etc.)
            rule: User bidding rule (max_bid, min_confidence, step, etc.)
            rec_max_bid: Recommended max bid from profit advisor
            base_confidence: Base confidence from valuation model
            cache_age: Age of cached valuation data (seconds)
            seller_trust_score: Seller trust score (0-1)
        
        Returns:
            BidDecision with adjusted confidence
        """
        current_price = context.get("current_price", 0)
        item_id = context.get("item_id", "unknown")
        auction_id = context.get("auction_id", "unknown")
        
        # Step 1: Adjust confidence based on cache freshness
        adjusted_confidence = self._adjust_confidence_for_cache(
            base_confidence,
            cache_age
        )
        
        # Step 2: Further adjust for seller trust
        if seller_trust_score is not None:
            adjusted_confidence *= seller_trust_score
        
        # Step 3: Apply EMA smoothing for stability
        adjusted_confidence = self._apply_ema_smoothing(
            item_id,
            adjusted_confidence
        )
        
        # Step 4: Check confidence threshold
        min_confidence = rule.get("min_confidence", 0.7)
        if adjusted_confidence < min_confidence:
            return BidDecision(
                ok=False,
                next_bid=None,
                reason="confidence_too_low",
                mode="hold",
                confidence=adjusted_confidence,
                cache_age=cache_age,
                adjusted_confidence=adjusted_confidence,
                seller_trust=seller_trust_score,
                base_confidence=base_confidence
            )
        
        # Step 5: Check budget constraints
        user_max_bid = rule.get("max_bid", float('inf'))
        if current_price >= user_max_bid:
            return BidDecision(
                ok=False,
                next_bid=None,
                reason="over_user_max",
                mode="deny",
                confidence=adjusted_confidence,
                cache_age=cache_age,
                adjusted_confidence=adjusted_confidence,
                seller_trust=seller_trust_score,
                base_confidence=base_confidence
            )
        
        if current_price >= rec_max_bid:
            return BidDecision(
                ok=False,
                next_bid=None,
                reason="over_rec_max",
                mode="deny",
                confidence=adjusted_confidence,
                cache_age=cache_age,
                adjusted_confidence=adjusted_confidence,
                seller_trust=seller_trust_score,
                base_confidence=base_confidence
            )
        
        # Step 6: Compute next bid with step
        step = rule.get("step", 50)
        proposed_bid = current_price + step
        
        # Ensure proposed bid doesn't exceed limits
        proposed_bid = min(proposed_bid, user_max_bid, rec_max_bid)
        
        # Step 7: Check stop-loss
        stop_loss_pct = rule.get("stop_loss_pct", 0)
        if stop_loss_pct > 0:
            stop_loss_price = rec_max_bid * (1 - stop_loss_pct / 100)
            if proposed_bid > stop_loss_price:
                return BidDecision(
                    ok=False,
                    next_bid=None,
                    reason="stop_loss_triggered",
                    mode="deny",
                    confidence=adjusted_confidence,
                    cache_age=cache_age,
                    adjusted_confidence=adjusted_confidence,
                    seller_trust=seller_trust_score,
                    base_confidence=base_confidence
                )
        
        # Step 8: Approve bid
        mode = rule.get("mode", "auto")
        
        return BidDecision(
            ok=True,
            next_bid=proposed_bid,
            reason="approved",
            mode=mode,
            confidence=adjusted_confidence,
            cache_age=cache_age,
            adjusted_confidence=adjusted_confidence,
            seller_trust=seller_trust_score,
            base_confidence=base_confidence
        )
    
    def _adjust_confidence_for_cache(
        self,
        base_confidence: float,
        cache_age: Optional[float]
    ) -> float:
        """
        Adjust confidence based on cache age.
        
        Formula: adjusted = base_conf * exp(-staleness_in_minutes / decay_factor)
        
        Examples:
        - Fresh data (0 min): weight = 1.0
        - 15 min old: weight = 0.61
        - 30 min old: weight = 0.37
        - 60 min old: weight = 0.14
        """
        if cache_age is None:
            return base_confidence
        
        staleness_minutes = cache_age / 60.0
        cache_freshness_weight = math.exp(
            -staleness_minutes / CACHE_FRESHNESS_DECAY_FACTOR
        )
        
        adjusted = base_confidence * cache_freshness_weight
        
        logger.debug(
            f"Cache age: {cache_age:.1f}s ({staleness_minutes:.1f}m), "
            f"weight: {cache_freshness_weight:.3f}, "
            f"confidence: {base_confidence:.3f} ? {adjusted:.3f}"
        )
        
        return adjusted
    
    def _apply_ema_smoothing(
        self,
        item_id: str,
        current_confidence: float
    ) -> float:
        """
        Apply Exponential Moving Average smoothing.
        
        Formula: EMA_t = alpha * current + (1 - alpha) * EMA_{t-1}
        
        This reduces confidence volatility and prevents over-reaction
        to single data points.
        """
        if item_id not in self._confidence_history:
            # First observation, no smoothing
            self._confidence_history[item_id] = current_confidence
            return current_confidence
        
        previous_ema = self._confidence_history[item_id]
        
        # Compute EMA
        ema_confidence = (
            EMA_ALPHA * current_confidence +
            (1 - EMA_ALPHA) * previous_ema
        )
        
        # Update history
        self._confidence_history[item_id] = ema_confidence
        
        logger.debug(
            f"EMA smoothing for {item_id}: "
            f"current={current_confidence:.3f}, "
            f"previous={previous_ema:.3f}, "
            f"EMA={ema_confidence:.3f}"
        )
        
        return ema_confidence
    
    def reset_confidence_history(self, item_id: Optional[str] = None) -> None:
        """Reset confidence history for item or all items."""
        if item_id:
            self._confidence_history.pop(item_id, None)
        else:
            self._confidence_history.clear()
    
    def get_confidence_history(self, item_id: str) -> Optional[float]:
        """Get EMA confidence history for item."""
        return self._confidence_history.get(item_id)


# Global policy engine instance
_policy_engine: Optional[BidPolicyEngine] = None


def init_policy_engine() -> BidPolicyEngine:
    """Initialize global policy engine."""
    global _policy_engine
    _policy_engine = BidPolicyEngine()
    return _policy_engine


def get_policy_engine() -> BidPolicyEngine:
    """Get global policy engine instance."""
    if _policy_engine is None:
        raise RuntimeError("Policy engine not initialized. Call init_policy_engine() first.")
    return _policy_engine


# Audit log helper
def log_bid_decision(
    decision: BidDecision,
    auction_id: str,
    item_id: str,
    context: Dict[str, Any]
) -> None:
    """
    Log bid decision with enhanced audit trail.
    """
    log_entry = {
        "timestamp": time.time(),
        "auction_id": auction_id,
        "item_id": item_id,
        "decision": decision.ok,
        "next_bid": decision.next_bid,
        "reason": decision.reason,
        "mode": decision.mode,
        "confidence": decision.confidence,
        "base_confidence": decision.base_confidence,
        "adjusted_confidence": decision.adjusted_confidence,
        "cache_age": decision.cache_age,
        "seller_trust": decision.seller_trust,
        "current_price": context.get("current_price"),
    }
    
    logger.info(f"BidDecision: {log_entry}")
    
    # In production, write to audit table or event bus
    # audit_service.log_decision(log_entry)
