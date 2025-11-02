"""
Price Detector Service for AutoBid (Phase 10).
Normalizes and deduplicates price update events from stream/OCR feed.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class PriceDetector:
    """
    Detects and normalizes price updates from auction streams.
    
    Features:
    - Debouncing (300ms)
    - Duplicate filtering
    - Sequence numbering
    - Price validation
    """
    
    def __init__(self, event_bus, debounce_ms: int = 300):
        self.event_bus = event_bus
        self.debounce_ms = debounce_ms
        
        # Debounce state: auction_id:item_id -> (price, timestamp, task)
        self.pending: Dict[str, tuple] = {}
        
        # Last seen: auction_id:item_id -> (price, sequence)
        self.last_seen: Dict[str, tuple] = defaultdict(lambda: (None, 0))
    
    async def process_raw_price_event(self, raw_event: Dict[str, Any]):
        """
        Process raw price event from OCR/stream.
        
        Args:
            raw_event: {
                "auction_id": "A1",
                "item_id": "L14",
                "price": 950.0,
                "source": "ocr|stream",
                "timestamp": ...
            }
        """
        auction_id = raw_event.get("auction_id")
        item_id = raw_event.get("item_id")
        price = raw_event.get("price")
        
        if not auction_id or not item_id or price is None:
            logger.warning(f"Invalid price event: {raw_event}")
            return
        
        # Validate price
        try:
            price = float(price)
            if price < 0:
                logger.warning(f"Negative price: {price}")
                return
        except (ValueError, TypeError):
            logger.warning(f"Invalid price value: {price}")
            return
        
        key = f"{auction_id}:{item_id}"
        
        # Check for duplicate
        last_price, last_seq = self.last_seen[key]
        if last_price == price:
            logger.debug(f"Duplicate price ignored: {key} @ {price}")
            return
        
        # Cancel existing debounce task if any
        if key in self.pending:
            _, _, task = self.pending[key]
            if task and not task.done():
                task.cancel()
        
        # Create debounced emit task
        task = asyncio.create_task(
            self._debounced_emit(auction_id, item_id, price, last_seq + 1)
        )
        
        self.pending[key] = (price, datetime.utcnow(), task)
    
    async def _debounced_emit(
        self, auction_id: str, item_id: str, price: float, seq: int
    ):
        """Emit price update after debounce delay."""
        try:
            # Wait for debounce period
            await asyncio.sleep(self.debounce_ms / 1000.0)
            
            key = f"{auction_id}:{item_id}"
            
            # Update last seen
            self.last_seen[key] = (price, seq)
            
            # Create normalized event
            normalized_event = {
                "auction_id": auction_id,
                "item_id": item_id,
                "price": price,
                "sequence": seq,
                "ts": datetime.utcnow().isoformat()
            }
            
            # Publish to event bus
            await self.event_bus.publish_price_update(auction_id, item_id, price)
            
            logger.info(
                f"Price update: {auction_id}/{item_id} @ {price} (seq={seq})"
            )
            
            # Clean up pending
            if key in self.pending:
                del self.pending[key]
        
        except asyncio.CancelledError:
            logger.debug(f"Debounce cancelled: {auction_id}/{item_id}")
        except Exception as e:
            logger.error(f"Error emitting price update: {e}")
    
    async def simulate_price_stream(
        self, auction_id: str, item_id: str, prices: list, interval_ms: int = 500
    ):
        """
        Simulate price stream for testing.
        
        Args:
            auction_id: Auction ID
            item_id: Item/lot ID
            prices: List of prices to emit
            interval_ms: Interval between prices
        """
        logger.info(f"Starting price simulation: {auction_id}/{item_id}")
        
        for price in prices:
            await self.process_raw_price_event({
                "auction_id": auction_id,
                "item_id": item_id,
                "price": price,
                "source": "simulation",
                "timestamp": datetime.utcnow().isoformat()
            })
            
            await asyncio.sleep(interval_ms / 1000.0)
        
        logger.info(f"Price simulation complete: {auction_id}/{item_id}")
    
    def get_current_price(self, auction_id: str, item_id: str) -> Optional[float]:
        """Get last known price for item."""
        key = f"{auction_id}:{item_id}"
        price, _ = self.last_seen.get(key, (None, 0))
        return price
    
    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        return {
            "pending_count": len(self.pending),
            "tracked_items": len(self.last_seen),
            "debounce_ms": self.debounce_ms
        }
