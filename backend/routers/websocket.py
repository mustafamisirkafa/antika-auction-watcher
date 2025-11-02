"""WebSocket routes for real-time updates."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.realtime.websocket_manager import WebSocketManager

router = APIRouter()

ws_manager = WebSocketManager()


@router.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str):
    """WebSocket endpoint for real-time updates."""
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
