"""Bidding agent with decision rules."""
from datetime import datetime, timedelta
from typing import Optional, Dict
from enum import Enum


class BidMode(str, Enum):
    """Bidding modes."""
    AUTO = "auto"
    SEMI_AUTO = "semi_auto"
    MANUAL = "manual"


class BidDecision(str, Enum):
    """Bid decision outcomes."""
    BID = "bid"
    WAIT = "wait"
    SKIP = "skip"


class BiddingAgent:
    """
    Bidding agent that makes decisions based on valuation and rules.
    Semi-auto mode requires user confirmation before bidding.
    """

    def __init__(self, mode: BidMode = BidMode.SEMI_AUTO):
        self.mode = mode
        self.recent_bids: Dict[int, datetime] = {}
        self.duplicate_prevention_window = 30  # seconds

    def should_bid(
        self,
        item_id: int,
        current_price: float,
        target_buy_price: float,
        confidence_score: float,
        min_confidence: float = 0.6
    ) -> tuple[BidDecision, str]:
        """
        Decide whether to bid on an item.
        
        Args:
            item_id: Item identifier
            current_price: Current auction price
            target_buy_price: Target buy price from valuation
            confidence_score: Confidence in valuation
            min_confidence: Minimum confidence threshold
            
        Returns:
            Tuple of (decision, reason)
        """
        # Rule 1: Check duplicate bid prevention
        if self._is_recent_bid(item_id):
            return BidDecision.SKIP, "Duplicate bid prevention - bid placed recently"
        
        # Rule 2: Check confidence threshold
        if confidence_score < min_confidence:
            return (
                BidDecision.SKIP,
                f"Low confidence ({confidence_score:.2f} < {min_confidence})"
            )
        
        # Rule 3: Check if current price is below target
        if current_price > target_buy_price:
            return (
                BidDecision.SKIP,
                f"Price too high (${current_price} > ${target_buy_price})"
            )
        
        # Rule 4: Check margin safety
        margin = (target_buy_price - current_price) / target_buy_price
        if margin < 0.05:  # Less than 5% margin
            return (
                BidDecision.WAIT,
                f"Margin too thin ({margin*100:.1f}%)"
            )
        
        # Rule 5: Calculate bid confidence
        price_ratio = current_price / target_buy_price
        bid_confidence = confidence_score * (1.0 - price_ratio)
        
        if bid_confidence > 0.7:
            return BidDecision.BID, f"High confidence bid ({bid_confidence:.2f})"
        elif bid_confidence > 0.5:
            return BidDecision.BID, f"Moderate confidence bid ({bid_confidence:.2f})"
        else:
            return BidDecision.WAIT, f"Low bid confidence ({bid_confidence:.2f})"

    def calculate_bid_amount(
        self,
        current_price: float,
        target_buy_price: float,
        bid_increment: float = 10.0
    ) -> float:
        """
        Calculate the bid amount.
        
        Args:
            current_price: Current auction price
            target_buy_price: Target buy price
            bid_increment: Minimum bid increment
            
        Returns:
            Suggested bid amount
        """
        # Start with minimum increment
        suggested_bid = current_price + bid_increment
        
        # Don't exceed target price
        if suggested_bid > target_buy_price:
            suggested_bid = target_buy_price
        
        return round(suggested_bid, 2)

    def record_bid(self, item_id: int):
        """Record a bid to prevent duplicates."""
        self.recent_bids[item_id] = datetime.utcnow()
        self._cleanup_old_bids()

    def _is_recent_bid(self, item_id: int) -> bool:
        """Check if a bid was placed recently."""
        if item_id not in self.recent_bids:
            return False
        
        last_bid_time = self.recent_bids[item_id]
        elapsed = (datetime.utcnow() - last_bid_time).total_seconds()
        
        return elapsed < self.duplicate_prevention_window

    def _cleanup_old_bids(self):
        """Remove old bid records."""
        cutoff = datetime.utcnow() - timedelta(seconds=self.duplicate_prevention_window * 2)
        self.recent_bids = {
            item_id: bid_time
            for item_id, bid_time in self.recent_bids.items()
            if bid_time > cutoff
        }

    def requires_confirmation(self) -> bool:
        """Check if mode requires user confirmation."""
        return self.mode == BidMode.SEMI_AUTO
