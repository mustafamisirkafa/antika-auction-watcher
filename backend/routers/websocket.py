"""WebSocket routes for real-time updates."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.realtime.websocket_manager import WebSocketManager
from typing import Dict, Optional

router = APIRouter()

ws_manager = WebSocketManager()


@router.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str):
    """
    WebSocket endpoint for real-time updates.
    
    Channels:
    - auctions: Live auction updates (bids, valuations, advisor recommendations)
    - admin: Admin notifications
    - notifications: User-specific notifications
    """
    await ws_manager.connect(websocket, channel)
    
    try:
        while True:
            # Keep connection alive and receive messages
            data = await websocket.receive_text()
            
            # Echo back or handle specific client messages
            await ws_manager.send_personal_message(
                {"type": "ack", "message": "Message received"},
                websocket
            )
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel)


# ============================================================================
# Broadcast Helper Functions
# ============================================================================

async def broadcast_advisor_update(
    item_id: str,
    recommendation: str,
    confidence: float,
    suggested_max_bid: Optional[float],
    risk_level: str,
    reasoning: list
):
    """
    Broadcast AI advisor recommendation update to all auction channel subscribers
    
    Args:
        item_id: Item identifier
        recommendation: Recommendation level (strong_buy, buy, watch, skip, avoid)
        confidence: Confidence score (0.0 to 1.0)
        suggested_max_bid: Suggested maximum bid amount
        risk_level: Risk assessment (low, medium, high, very_high)
        reasoning: List of reasoning points
    """
    await ws_manager.broadcast({
        "event": "advisor_update",
        "item_id": item_id,
        "recommendation": recommendation,
        "confidence": confidence,
        "suggested_max_bid": suggested_max_bid,
        "risk_level": risk_level,
        "reasoning": reasoning[:3] if len(reasoning) > 3 else reasoning  # First 3 points
    }, "auctions")


async def broadcast_bid_update(
    item_id: str,
    current_price: float,
    bidder_id: str,
    timestamp: str
):
    """Broadcast bid update to auction channel"""
    await ws_manager.broadcast({
        "event": "bid_update",
        "item_id": item_id,
        "current_price": current_price,
        "bidder_id": bidder_id,
        "timestamp": timestamp
    }, "auctions")


async def broadcast_valuation_update(
    item_id: str,
    estimated_value: float,
    confidence: float,
    timestamp: str
):
    """Broadcast valuation update to auction channel"""
    await ws_manager.broadcast({
        "event": "valuation_update",
        "item_id": item_id,
        "estimated_value": estimated_value,
        "confidence": confidence,
        "timestamp": timestamp
    }, "auctions")
