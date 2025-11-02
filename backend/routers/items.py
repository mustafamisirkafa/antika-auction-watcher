"""Items API routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel
from backend.db.database import get_session
from backend.db.models import Item, User
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/items", tags=["Items"])


class ItemCreate(BaseModel):
    """Item creation schema."""
    title: str
    description: str | None = None
    category: str
    image_url: str | None = None
    seller_name: str
    auction_platform: str = "instagram"
    live_room_id: str | None = None
    current_price: float = 0.0


class ItemResponse(BaseModel):
    """Item response schema."""
    id: int
    title: str
    description: str | None
    category: str
    image_url: str | None
    seller_name: str
    auction_platform: str
    live_room_id: str | None
    current_price: float
    estimated_value: float | None
    target_buy_price: float | None
    confidence_score: float | None
    status: str


@router.post("/", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_data: ItemCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a new auction item."""
    new_item = Item(**item_data.model_dump())
    
    session.add(new_item)
    session.commit()
    session.refresh(new_item)
    
    return new_item


@router.get("/", response_model=List[ItemResponse])
async def list_items(
    status_filter: str | None = None,
    category: str | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """List all items with optional filters."""
    statement = select(Item)
    
    if status_filter:
        statement = statement.where(Item.status == status_filter)
    
    if category:
        statement = statement.where(Item.category == category)
    
    items = session.exec(statement).all()
    return items


@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(
    item_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get a specific item by ID."""
    item = session.get(Item, item_id)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return item


@router.patch("/{item_id}", response_model=ItemResponse)
async def update_item(
    item_id: int,
    current_price: float | None = None,
    status_update: str | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update item price or status."""
    item = session.get(Item, item_id)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    if current_price is not None:
        item.current_price = current_price
    
    if status_update:
        item.status = status_update
    
    session.add(item)
    session.commit()
    session.refresh(item)
    
    return item
