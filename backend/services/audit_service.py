"""
Audit Service for AutoBid (Phase 10).
Logs all AutoBid decisions and actions.
"""
import logging
from typing import Dict, Any, Optional, Literal
from datetime import datetime, timedelta
from sqlmodel import Session, select

from backend.models.bid_rules import AutoBidAudit

logger = logging.getLogger(__name__)


class AuditService:
    """
    Audit service for AutoBid tracking.
    
    Records:
    - Decision events (policy evaluation)
    - Bid events (dispatch)
    - Result events (accepted/rejected/timeout)
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_decision(
        self,
        team_id: int,
        auction_id: str,
        item_id: str,
        decision: Dict[str, Any],
        valuation: Dict[str, Any],
        rule_id: Optional[int] = None,
        latency_ms: Optional[float] = None
    ):
        """Log AutoBid decision event."""
        audit = AutoBidAudit(
            team_id=team_id,
            auction_id=auction_id,
            item_id=item_id,
            event_type="decision",
            current_price=valuation.get("current_price"),
            rec_max_bid=valuation.get("rec_max_bid"),
            next_bid=decision.get("next_bid"),
            confidence=valuation.get("confidence"),
            risk_level=valuation.get("risk_level"),
            decision_ok=decision.get("ok", False),
            decision_reason=decision.get("reason", ""),
            blocked_by=decision.get("blocked_by"),
            rule_id=rule_id,
            mode=decision.get("mode", "shadow"),
            latency_ms=latency_ms
        )
        
        self.db.add(audit)
        self.db.commit()
        
        logger.debug(f"Audit: decision logged for {item_id}")
    
    def log_bid(
        self,
        team_id: int,
        auction_id: str,
        item_id: str,
        bid_amount: float,
        rule_id: Optional[int] = None,
        mode: Literal["shadow", "auto"] = "shadow"
    ):
        """Log bid dispatch event."""
        audit = AutoBidAudit(
            team_id=team_id,
            auction_id=auction_id,
            item_id=item_id,
            event_type="bid",
            bid_amount=bid_amount,
            decision_ok=True,
            decision_reason="Bid dispatched",
            rule_id=rule_id,
            mode=mode
        )
        
        self.db.add(audit)
        self.db.commit()
        
        logger.debug(f"Audit: bid logged for {item_id} @ {bid_amount}")
    
    def log_result(
        self,
        team_id: int,
        auction_id: str,
        item_id: str,
        bid_amount: float,
        result: Literal["accepted", "rejected", "timeout", "error", "simulated"],
        latency_ms: Optional[float] = None,
        rule_id: Optional[int] = None,
        mode: Literal["shadow", "auto"] = "shadow"
    ):
        """Log bid result event."""
        audit = AutoBidAudit(
            team_id=team_id,
            auction_id=auction_id,
            item_id=item_id,
            event_type="result",
            bid_amount=bid_amount,
            bid_result=result,
            decision_ok=result in ["accepted", "simulated"],
            decision_reason=f"Bid {result}",
            rule_id=rule_id,
            mode=mode,
            latency_ms=latency_ms
        )
        
        self.db.add(audit)
        self.db.commit()
        
        logger.debug(f"Audit: result logged for {item_id} ? {result}")
    
    def get_audit_log(
        self,
        team_id: int,
        auction_id: Optional[str] = None,
        item_id: Optional[str] = None,
        event_type: Optional[Literal["decision", "bid", "result"]] = None,
        limit: int = 100
    ):
        """Get audit log entries."""
        query = select(AutoBidAudit).where(AutoBidAudit.team_id == team_id)
        
        if auction_id:
            query = query.where(AutoBidAudit.auction_id == auction_id)
        
        if item_id:
            query = query.where(AutoBidAudit.item_id == item_id)
        
        if event_type:
            query = query.where(AutoBidAudit.event_type == event_type)
        
        query = query.order_by(AutoBidAudit.ts.desc()).limit(limit)
        
        return self.db.exec(query).all()
    
    def get_stats(
        self, team_id: int, hours: int = 24
    ) -> Dict[str, Any]:
        """Get AutoBid statistics for team."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        # Count events
        query = select(AutoBidAudit).where(
            AutoBidAudit.team_id == team_id,
            AutoBidAudit.ts > cutoff
        )
        
        all_events = self.db.exec(query).all()
        
        decisions = [e for e in all_events if e.event_type == "decision"]
        bids = [e for e in all_events if e.event_type == "bid"]
        results = [e for e in all_events if e.event_type == "result"]
        
        # Calculate success rate
        accepted = [r for r in results if r.bid_result == "accepted"]
        success_rate = len(accepted) / len(results) if results else 0.0
        
        # Average latency
        latencies = [e.latency_ms for e in all_events if e.latency_ms is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        
        return {
            "period_hours": hours,
            "total_events": len(all_events),
            "decisions": len(decisions),
            "bids": len(bids),
            "results": len(results),
            "success_rate": round(success_rate, 3),
            "avg_latency_ms": round(avg_latency, 2),
            "accepted_bids": len(accepted)
        }
    
    def cleanup_old_logs(self, days: int = 30):
        """Clean up old audit logs."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        deleted = self.db.exec(
            select(AutoBidAudit).where(AutoBidAudit.ts < cutoff)
        ).all()
        
        for log in deleted:
            self.db.delete(log)
        
        self.db.commit()
        
        logger.info(f"Cleaned up {len(deleted)} old audit logs")
        return len(deleted)
