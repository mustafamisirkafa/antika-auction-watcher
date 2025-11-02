"""
Valuation Reactor Service for AutoBid (Phase 10).
Fast valuation path using cached Profit Advisor estimates.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlmodel import Session, select

from backend.models.profit import ProfitEstimate, AuctionItem

logger = logging.getLogger(__name__)


class ValuationReactor:
    """
    Fast valuation reactor for AutoBid.
    
    SLA: ? 1.2s per valuation
    
    Strategy:
    1. Check for cached ProfitEstimate (Phase 9)
    2. If fresh (<24h), use it
    3. Otherwise, run fast valuation (simplified logic)
    """
    
    def __init__(self, db: Session, event_bus):
        self.db = db
        self.event_bus = event_bus
        self.cache_ttl_hours = 24
    
    async def react_to_price_update(
        self, auction_id: str, item_id: str, current_price: float
    ) -> Optional[Dict[str, Any]]:
        """
        React to price update with fast valuation.
        
        Args:
            auction_id: Auction ID
            item_id: Item/lot ID
            current_price: Current auction price
        
        Returns:
            Valuation result or None if unavailable
        """
        start_time = datetime.utcnow()
        
        try:
            # 1. Find auction item
            auction_item = self.db.exec(
                select(AuctionItem)
                .where(AuctionItem.lot_id == item_id)
            ).first()
            
            if not auction_item:
                logger.warning(f"Auction item not found: {item_id}")
                return None
            
            # 2. Check for cached ProfitEstimate
            estimate = await self._get_cached_estimate(auction_item.id)
            
            if estimate:
                # Use cached estimate
                result = {
                    "auction_id": auction_id,
                    "item_id": item_id,
                    "current_price": current_price,
                    "rec_max_bid": estimate.recommended_max_bid,
                    "estimated_value": estimate.estimated_value,
                    "confidence": estimate.confidence,
                    "risk_level": estimate.risk_level,
                    "profit_margin": estimate.profit_margin,
                    "source": "cached_advisor",
                    "ts": datetime.utcnow().isoformat()
                }
            else:
                # Fallback: fast valuation
                result = await self._fast_valuation(
                    auction_id, item_id, auction_item, current_price
                )
            
            # Calculate latency
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            result["latency_ms"] = round(latency_ms, 2)
            
            # Publish advisor ready event
            await self.event_bus.publish_advisor_ready(auction_id, item_id, result)
            
            logger.info(
                f"Valuation: {item_id} @ {current_price} ? max_bid={result['rec_max_bid']} "
                f"({latency_ms:.0f}ms)"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Valuation error for {item_id}: {e}")
            return None
    
    async def _get_cached_estimate(
        self, auction_item_id: int
    ) -> Optional[ProfitEstimate]:
        """Get cached profit estimate if fresh."""
        cutoff = datetime.utcnow() - timedelta(hours=self.cache_ttl_hours)
        
        estimate = self.db.exec(
            select(ProfitEstimate)
            .where(ProfitEstimate.auction_item_id == auction_item_id)
            .where(ProfitEstimate.created_at > cutoff)
            .order_by(ProfitEstimate.created_at.desc())
        ).first()
        
        return estimate
    
    async def _fast_valuation(
        self, auction_id: str, item_id: str, auction_item: AuctionItem, current_price: float
    ) -> Dict[str, Any]:
        """
        Fast valuation fallback (no Profit Advisor data).
        
        Simple heuristic:
        - rec_max_bid = starting_price * 1.3
        - confidence = 0.5 (medium)
        - risk_level = "medium"
        """
        # Simple heuristic valuation
        rec_max_bid = auction_item.starting_price * 1.3
        estimated_value = auction_item.starting_price * 1.5
        
        profit_margin = (estimated_value - rec_max_bid) / rec_max_bid if rec_max_bid > 0 else 0
        
        return {
            "auction_id": auction_id,
            "item_id": item_id,
            "current_price": current_price,
            "rec_max_bid": round(rec_max_bid, 2),
            "estimated_value": round(estimated_value, 2),
            "confidence": 0.5,
            "risk_level": "medium",
            "profit_margin": round(profit_margin, 4),
            "source": "fast_heuristic",
            "ts": datetime.utcnow().isoformat()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get reactor statistics."""
        # Count recent estimates in cache
        cutoff = datetime.utcnow() - timedelta(hours=self.cache_ttl_hours)
        cached_count = self.db.exec(
            select(ProfitEstimate)
            .where(ProfitEstimate.created_at > cutoff)
        ).all()
        
        return {
            "cache_ttl_hours": self.cache_ttl_hours,
            "cached_estimates": len(cached_count)
        }
