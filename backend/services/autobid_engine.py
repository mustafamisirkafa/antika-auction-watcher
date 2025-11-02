"""
AutoBid Engine - Main orchestrator for Phase 10.
End-to-end reaction: price update ? valuation ? policy ? bid dispatch.
Target SLA: ? 3.0s
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlmodel import Session

from backend.services.event_bus import EventBus
from backend.services.price_detector import PriceDetector
from backend.services.valuation_reactor import ValuationReactor
from backend.services.bid_policy import BidPolicy
from backend.services.bid_dispatcher import BidDispatcher

logger = logging.getLogger(__name__)


class AutoBidEngine:
    """
    AutoBid Engine orchestrator.
    
    Pipeline:
    1. Listen to price_update events
    2. Call ValuationReactor
    3. Call BidPolicy
    4. Publish bid.request (if allowed)
    5. BidDispatcher executes
    
    Target end-to-end: ? 3.0s
    """
    
    def __init__(
        self,
        db: Session,
        event_bus: EventBus,
        redis_client,
        price_detector: PriceDetector,
        valuation_reactor: ValuationReactor,
        bid_policy: BidPolicy,
        bid_dispatcher: BidDispatcher
    ):
        self.db = db
        self.event_bus = event_bus
        self.redis = redis_client
        self.price_detector = price_detector
        self.valuation_reactor = valuation_reactor
        self.bid_policy = bid_policy
        self.bid_dispatcher = bid_dispatcher
        
        # Active auctions: auction_id -> {team_id, status, ...}
        self.active_auctions: Dict[str, Dict[str, Any]] = {}
    
    async def start(self):
        """Start AutoBid engine."""
        # Subscribe to price updates
        await self.event_bus.subscribe(
            "auction.price_update:*",
            self._handle_price_update
        )
        
        # Subscribe to bid requests
        await self.event_bus.subscribe(
            "bid.request",
            self._handle_bid_request
        )
        
        logger.info("AutoBid Engine started")
    
    async def enable_autobid(
        self, team_id: int, auction_id: str, rules: Optional[Dict[str, Any]] = None
    ):
        """Enable AutoBid for an auction."""
        if auction_id in self.active_auctions:
            logger.warning(f"AutoBid already active for {auction_id}")
            return
        
        self.active_auctions[auction_id] = {
            "team_id": team_id,
            "status": "active",
            "rules": rules,
            "started_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"AutoBid enabled: {auction_id} (team={team_id})")
    
    async def disable_autobid(self, auction_id: str):
        """Disable AutoBid for an auction."""
        if auction_id in self.active_auctions:
            del self.active_auctions[auction_id]
            logger.info(f"AutoBid disabled: {auction_id}")
    
    def is_active(self, auction_id: str) -> bool:
        """Check if AutoBid is active for auction."""
        return auction_id in self.active_auctions
    
    async def _handle_price_update(self, channel: str, payload: Dict[str, Any]):
        """
        Handle price update event.
        
        Pipeline:
        1. Check if AutoBid is active
        2. Valuation reactor
        3. Bid policy evaluation
        4. Publish bid request (if ok)
        """
        start_time = datetime.utcnow()
        
        auction_id = payload.get("auction_id")
        item_id = payload.get("item_id")
        price = payload.get("price")
        
        if not auction_id or not self.is_active(auction_id):
            return
        
        auction_config = self.active_auctions[auction_id]
        team_id = auction_config["team_id"]
        user_rules = auction_config.get("rules")
        
        try:
            # Step 1: Valuation (SLA: 1.2s)
            valuation = await self.valuation_reactor.react_to_price_update(
                auction_id, item_id, price
            )
            
            if not valuation:
                logger.warning(f"Valuation unavailable for {item_id}")
                return
            
            # Step 2: Policy evaluation
            decision = await self.bid_policy.evaluate_bid_decision(
                team_id, auction_id, item_id, price, valuation, user_rules
            )
            
            # Publish autobid decision event
            decision_event = {
                "auction_id": auction_id,
                "item_id": item_id,
                "team_id": team_id,
                "current_price": price,
                **decision,
                "ts": datetime.utcnow().isoformat()
            }
            await self.event_bus.publish_autobid_decision(decision_event)
            
            # Step 3: Dispatch bid if ok
            if decision["ok"] and decision["mode"] == "auto":
                # Acquire lock to prevent race conditions
                if await self.bid_dispatcher.acquire_lock(auction_id):
                    try:
                        await self.event_bus.publish_bid_request({
                            "team_id": team_id,
                            "auction_id": auction_id,
                            "item_id": item_id,
                            "bid_amount": decision["next_bid"],
                            "mode": decision["mode"]
                        })
                    finally:
                        await self.bid_dispatcher.release_lock(auction_id)
            
            # Calculate total latency
            total_latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.info(
                f"AutoBid pipeline: {auction_id}/{item_id} @ {price} ? "
                f"{decision['status']} ({total_latency_ms:.0f}ms)"
            )
            
            # Check SLA
            if total_latency_ms > 3000:
                logger.warning(f"SLA exceeded: {total_latency_ms:.0f}ms > 3000ms")
        
        except Exception as e:
            logger.error(f"AutoBid pipeline error: {e}")
    
    async def _handle_bid_request(self, channel: str, payload: Dict[str, Any]):
        """Handle bid request from policy."""
        team_id = payload.get("team_id")
        auction_id = payload.get("auction_id")
        item_id = payload.get("item_id")
        bid_amount = payload.get("bid_amount")
        mode = payload.get("mode", "shadow")
        
        try:
            # Dispatch bid
            result = await self.bid_dispatcher.dispatch_bid(
                team_id, auction_id, item_id, bid_amount, mode
            )
            
            # Record bid for budget tracking
            if result["result"] in ["accepted", "simulated"]:
                await self.bid_policy.record_bid(team_id, auction_id, bid_amount)
            
            logger.info(f"Bid result: {result['result']} for {item_id} @ {bid_amount}")
        
        except Exception as e:
            logger.error(f"Bid dispatch error: {e}")
    
    def get_status(self, auction_id: Optional[str] = None) -> Dict[str, Any]:
        """Get AutoBid status."""
        if auction_id:
            return self.active_auctions.get(auction_id, {"status": "inactive"})
        else:
            return {
                "active_auctions": list(self.active_auctions.keys()),
                "count": len(self.active_auctions)
            }
