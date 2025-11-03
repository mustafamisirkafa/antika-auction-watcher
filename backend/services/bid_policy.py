"""
Bid Policy Service for AutoBid (Phase 10).
Composes bidding decisions based on rules, budgets, and risk caps.
"""
import logging
from typing import Dict, Any, Optional, Literal
from datetime import datetime
from sqlmodel import Session, select

logger = logging.getLogger(__name__)


BidMode = Literal["shadow", "auto"]
DecisionStatus = Literal["ok", "blocked", "skip"]


class BidPolicy:
    """
    Bid policy engine for AutoBid.
    
    Enforces:
    - User bidding rules (max bid, min confidence, step)
    - Budget caps (daily, per-auction)
    - Stop-loss rules
    - Risk thresholds
    """
    
    def __init__(self, db: Session, redis_client):
        self.db = db
        self.redis = redis_client
    
    async def evaluate_bid_decision(
        self,
        team_id: int,
        auction_id: str,
        item_id: str,
        current_price: float,
        valuation: Dict[str, Any],
        user_rules: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate whether to place a bid.
        
        Args:
            team_id: Team ID
            auction_id: Auction ID
            item_id: Item/lot ID
            current_price: Current auction price
            valuation: Valuation result from ValuationReactor
            user_rules: User bidding rules (optional)
        
        Returns:
            Decision dict: {
                "ok": bool,
                "next_bid": float,
                "reason": str,
                "mode": "shadow" | "auto",
                "blocked_by": str (if blocked)
            }
        """
        rec_max_bid = valuation.get("rec_max_bid", 0)
        confidence = valuation.get("confidence", 0)
        risk_level = valuation.get("risk_level", "high")
        
        # Default rules if not provided
        if user_rules is None:
            user_rules = await self._get_default_rules(team_id, item_id)
        
        mode = user_rules.get("mode", "shadow")
        max_bid = user_rules.get("max_bid", rec_max_bid)
        min_confidence = user_rules.get("min_confidence", 0.6)
        step = user_rules.get("step", 25)
        stop_loss_pct = user_rules.get("stop_loss_pct", 0.1)
        
        # Calculate next bid (current + step)
        next_bid = self._calculate_next_bid(current_price, step)
        
        # === Evaluation checks ===
        
        # 1. Check confidence threshold
        if confidence < min_confidence:
            return {
                "ok": False,
                "status": "blocked",
                "reason": f"Confidence {confidence:.2f} < {min_confidence}",
                "blocked_by": "min_confidence",
                "mode": mode
            }
        
        # 2. Check max bid limit
        if next_bid > max_bid:
            return {
                "ok": False,
                "status": "blocked",
                "reason": f"Next bid {next_bid} > max {max_bid}",
                "blocked_by": "max_bid",
                "mode": mode
            }
        
        # 3. Check recommended max bid
        if next_bid > rec_max_bid:
            return {
                "ok": False,
                "status": "blocked",
                "reason": f"Next bid {next_bid} > AI rec {rec_max_bid}",
                "blocked_by": "rec_max_bid",
                "mode": mode
            }
        
        # 4. Check stop-loss
        if self._check_stop_loss(current_price, rec_max_bid, stop_loss_pct):
            return {
                "ok": False,
                "status": "blocked",
                "reason": f"Stop-loss triggered at {stop_loss_pct*100}%",
                "blocked_by": "stop_loss",
                "mode": mode
            }
        
        # 5. Check daily budget cap
        budget_ok, budget_reason = await self._check_budget_cap(team_id, auction_id, next_bid)
        if not budget_ok:
            return {
                "ok": False,
                "status": "blocked",
                "reason": budget_reason,
                "blocked_by": "budget_cap",
                "mode": mode
            }
        
        # 6. Check risk level
        if risk_level == "high" and user_rules.get("allow_high_risk", False) is False:
            return {
                "ok": False,
                "status": "blocked",
                "reason": f"Risk level {risk_level} not allowed",
                "blocked_by": "risk_level",
                "mode": mode
            }
        
        # All checks passed
        return {
            "ok": True,
            "status": "ok",
            "next_bid": next_bid,
            "reason": "All checks passed",
            "mode": mode,
            "confidence": confidence,
            "risk_level": risk_level,
            "rec_max_bid": rec_max_bid
        }
    
    def _calculate_next_bid(self, current_price: float, step: float) -> float:
        """Calculate next bid amount."""
        return round(current_price + step, 2)
    
    def _check_stop_loss(
        self, current_price: float, rec_max_bid: float, stop_loss_pct: float
    ) -> bool:
        """Check if stop-loss is triggered."""
        if rec_max_bid <= 0:
            return False
        
        loss = (current_price - rec_max_bid) / rec_max_bid
        return loss > stop_loss_pct
    
    async def _check_budget_cap(
        self, team_id: int, auction_id: str, next_bid: float
    ) -> tuple[bool, str]:
        """
        Check budget caps.
        
        Returns:
            (ok, reason)
        """
        # Daily budget cap
        daily_key = f"budget:daily:{team_id}:{datetime.utcnow().date()}"
        daily_spent = await self.redis.get(daily_key)
        daily_spent = float(daily_spent) if daily_spent else 0.0
        
        # TODO: Get team's daily budget limit from plan/settings
        daily_limit = 10000.0  # Default 10,000 TL
        
        if daily_spent + next_bid > daily_limit:
            return False, f"Daily budget exceeded ({daily_spent + next_bid:.0f} > {daily_limit:.0f})"
        
        # Auction-specific cap
        auction_key = f"budget:auction:{team_id}:{auction_id}"
        auction_spent = await self.redis.get(auction_key)
        auction_spent = float(auction_spent) if auction_spent else 0.0
        
        auction_limit = 5000.0  # Default 5,000 TL per auction
        
        if auction_spent + next_bid > auction_limit:
            return False, f"Auction budget exceeded ({auction_spent + next_bid:.0f} > {auction_limit:.0f})"
        
        return True, "Budget OK"
    
    async def record_bid(self, team_id: int, auction_id: str, bid_amount: float):
        """Record bid for budget tracking."""
        # Update daily budget
        daily_key = f"budget:daily:{team_id}:{datetime.utcnow().date()}"
        await self.redis.incrbyfloat(daily_key, bid_amount)
        await self.redis.expire(daily_key, 86400)  # 24 hours
        
        # Update auction budget
        auction_key = f"budget:auction:{team_id}:{auction_id}"
        await self.redis.incrbyfloat(auction_key, bid_amount)
        await self.redis.expire(auction_key, 7200)  # 2 hours
    
    async def _get_default_rules(self, team_id: int, item_id: str) -> Dict[str, Any]:
        """Get default bidding rules."""
        # TODO: Query BidRule model for team's rules
        return {
            "mode": "shadow",
            "max_bid": 2000.0,
            "min_confidence": 0.6,
            "step": 25.0,
            "stop_loss_pct": 0.1,
            "allow_high_risk": False
        }
