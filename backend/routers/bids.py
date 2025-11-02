"""Bidding API routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session, select
from pydantic import BaseModel
from backend.db.database import get_session
from backend.db.models import Item, Bid, User
from backend.routers.auth import get_current_user
from backend.services.bidding import BiddingAgent
from backend.services.bidding.agent import BidMode, BidDecision
from backend.realtime.redis_manager import RedisManager
from backend.realtime.websocket_manager import WebSocketManager

router = APIRouter(prefix="/bids", tags=["Bids"])

# Initialize services
bidding_agent = BiddingAgent(mode=BidMode.SEMI_AUTO)
redis_manager = RedisManager()
ws_manager = WebSocketManager()


class BidRequest(BaseModel):
    """Bid request schema."""
    item_id: int
    mode: str = "semi_auto"  # auto, semi_auto, manual


class BidResponse(BaseModel):
    """Bid response schema."""
    id: int
    item_id: int
    user_id: int
    bid_amount: float
    bid_type: str
    decision_reason: str | None
    success: bool


class BidDecisionResponse(BaseModel):
    """Bid decision response schema."""
    decision: str
    reason: str
    suggested_bid_amount: float | None
    current_price: float
    target_buy_price: float


async def broadcast_bid(
    item_id: int,
    bid_amount: float,
    decision: str,
    reason: str,
    success: bool
):
    """Background task to broadcast bid via WebSocket and Redis."""
    try:
        await ws_manager.broadcast_bid(item_id, bid_amount, decision, reason, success)
        await redis_manager.publish_bid_event(item_id, bid_amount, decision, reason, success)
    except Exception:
        pass  # Don't fail the request if broadcast fails


@router.post("/decision", response_model=BidDecisionResponse)
async def get_bid_decision(
    bid_request: BidRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a bid decision recommendation for an item."""
    # Get item
    item = session.get(Item, bid_request.item_id)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Check if valuation exists
    if not item.target_buy_price or not item.confidence_score:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item must be valued first"
        )
    
    # Get bid decision
    decision, reason = bidding_agent.should_bid(
        item.id,
        item.current_price,
        item.target_buy_price,
        item.confidence_score
    )
    
    suggested_bid_amount = None
    if decision == BidDecision.BID:
        suggested_bid_amount = bidding_agent.calculate_bid_amount(
            item.current_price,
            item.target_buy_price
        )
    
    return {
        "decision": decision.value,
        "reason": reason,
        "suggested_bid_amount": suggested_bid_amount,
        "current_price": item.current_price,
        "target_buy_price": item.target_buy_price
    }


@router.post("/place", response_model=BidResponse, status_code=status.HTTP_201_CREATED)
async def place_bid(
    bid_request: BidRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Place a bid on an item."""
    # Get item
    item = session.get(Item, bid_request.item_id)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Check if valuation exists
    if not item.target_buy_price or not item.confidence_score:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item must be valued first"
        )
    
    # Get bid decision
    decision, reason = bidding_agent.should_bid(
        item.id,
        item.current_price,
        item.target_buy_price,
        item.confidence_score
    )
    
    if decision != BidDecision.BID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot place bid: {reason}"
        )
    
    # Calculate bid amount
    bid_amount = bidding_agent.calculate_bid_amount(
        item.current_price,
        item.target_buy_price
    )
    
    # Record bid
    bidding_agent.record_bid(item.id)
    
    # Create bid record
    bid = Bid(
        item_id=item.id,
        user_id=current_user.id,
        bid_amount=bid_amount,
        bid_type=bid_request.mode,
        decision_reason=reason,
        success=True  # Mock success for Phase 1
    )
    
    session.add(bid)
    session.commit()
    session.refresh(bid)
    
    # Broadcast to real-time clients
    background_tasks.add_task(
        broadcast_bid,
        item.id,
        bid_amount,
        decision.value,
        reason,
        True
    )
    
    return bid


@router.get("/item/{item_id}", response_model=List[BidResponse])
async def get_item_bids(
    item_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all bids for a specific item."""
    statement = select(Bid).where(Bid.item_id == item_id)
    bids = session.exec(statement).all()
    
    return bids


@router.get("/user/me", response_model=List[BidResponse])
async def get_my_bids(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get all bids placed by the current user."""
    statement = select(Bid).where(Bid.user_id == current_user.id)
    bids = session.exec(statement).all()
    
    return bids
