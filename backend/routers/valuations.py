"""Valuation API routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session, select
from pydantic import BaseModel
from backend.db.database import get_session
from backend.db.models import Item, Valuation, User
from backend.routers.auth import get_current_user
from backend.services.valuation import ValuationEstimator
from backend.realtime.redis_manager import RedisManager
from backend.realtime.websocket_manager import WebSocketManager

router = APIRouter(prefix="/valuations", tags=["Valuations"])

# Initialize services
valuation_estimator = ValuationEstimator()
redis_manager = RedisManager()
ws_manager = WebSocketManager()


class ValuationRequest(BaseModel):
    """Valuation request schema."""
    item_id: int


class ValuationResponse(BaseModel):
    """Valuation response schema."""
    id: int
    item_id: int
    source: str
    estimated_price: float
    confidence: float


async def broadcast_valuation(
    item_id: int,
    estimated_value: float,
    target_buy_price: float,
    confidence_score: float
):
    """Background task to broadcast valuation via WebSocket and Redis."""
    try:
        await ws_manager.broadcast_valuation(
            item_id, estimated_value, target_buy_price, confidence_score
        )
        await redis_manager.publish_valuation_event(
            item_id, estimated_value, target_buy_price, confidence_score
        )
    except Exception:
        pass  # Don't fail the request if broadcast fails


@router.post("/estimate", status_code=status.HTTP_201_CREATED)
async def estimate_item_value(
    valuation_request: ValuationRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Estimate the value of an item using multiple sources."""
    # Get item
    item = session.get(Item, valuation_request.item_id)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Run valuation
    estimated_value, target_buy_price, confidence_score, comparables = (
        await valuation_estimator.estimate_value(item.title, item.category)
    )
    
    # Update item with valuation results
    item.estimated_value = estimated_value
    item.target_buy_price = target_buy_price
    item.confidence_score = confidence_score
    
    session.add(item)
    
    # Save individual valuations from each source
    source_valuations = {}
    for comp in comparables:
        source = comp["source"]
        if source not in source_valuations:
            source_valuations[source] = []
        source_valuations[source].append(comp)
    
    valuation_records = []
    for source, comps in source_valuations.items():
        avg_price = sum(c["price"] for c in comps) / len(comps)
        
        valuation = Valuation(
            item_id=item.id,
            source=source,
            estimated_price=avg_price,
            confidence=confidence_score,
            comparables={"data": comps[:5]}  # Store top 5 comparables
        )
        session.add(valuation)
        valuation_records.append(valuation)
    
    session.commit()
    
    # Broadcast to real-time clients
    background_tasks.add_task(
        broadcast_valuation,
        item.id,
        estimated_value,
        target_buy_price,
        confidence_score
    )
    
    return {
        "item_id": item.id,
        "estimated_value": estimated_value,
        "target_buy_price": target_buy_price,
        "confidence_score": confidence_score,
        "sources": len(source_valuations),
        "comparables_count": len(comparables)
    }


@router.get("/item/{item_id}", response_model=List[ValuationResponse])
async def get_item_valuations(
    item_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all valuations for a specific item."""
    statement = select(Valuation).where(Valuation.item_id == item_id)
    valuations = session.exec(statement).all()
    
    return valuations
