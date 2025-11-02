"""WebSocket connection manager for real-time updates."""
from typing import Dict, Set
from fastapi import WebSocket


class WebSocketManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        # Store active connections by channel
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str = "default"):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        
        self.active_connections[channel].add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str = "default"):
        """Remove a WebSocket connection."""
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
            
            # Clean up empty channels
            if not self.active_connections[channel]:
                del self.active_connections[channel]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket."""
        await websocket.send_json(message)

    async def broadcast(self, message: dict, channel: str = "default"):
        """Broadcast a message to all connections in a channel."""
        if channel not in self.active_connections:
            return
        
        # Create a copy to avoid modification during iteration
        connections = self.active_connections[channel].copy()
        
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Remove disconnected clients
                self.disconnect(connection, channel)

    async def broadcast_valuation(
        self,
        item_id: int,
        estimated_value: float,
        target_buy_price: float,
        confidence_score: float
    ):
        """Broadcast valuation update to all connected clients."""
        message = {
            "type": "valuation",
            "item_id": item_id,
            "estimated_value": estimated_value,
            "target_buy_price": target_buy_price,
            "confidence_score": confidence_score
        }
        await self.broadcast(message, "valuations")

    async def broadcast_bid(
        self,
        item_id: int,
        bid_amount: float,
        decision: str,
        reason: str,
        success: bool
    ):
        """Broadcast bid event to all connected clients."""
        message = {
            "type": "bid",
            "item_id": item_id,
            "bid_amount": bid_amount,
            "decision": decision,
            "reason": reason,
            "success": success
        }
        await self.broadcast(message, "bids")

    async def broadcast_item_update(
        self,
        item_id: int,
        current_price: float,
        status: str
    ):
        """Broadcast item update to all connected clients."""
        message = {
            "type": "item_update",
            "item_id": item_id,
            "current_price": current_price,
            "status": status
        }
        await self.broadcast(message, "items")

    def get_connection_count(self, channel: str = None) -> int:
        """Get number of active connections."""
        if channel:
            return len(self.active_connections.get(channel, set()))
        
        return sum(len(conns) for conns in self.active_connections.values())
