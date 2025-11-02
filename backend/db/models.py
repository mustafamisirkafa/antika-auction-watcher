"""Database models using SQLModel."""
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Column, String, JSON
from sqlalchemy import Index


class User(SQLModel, table=True):
    """User model for authentication."""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    username: str = Field(unique=True, index=True, max_length=100)
    hashed_password: str = Field(max_length=255)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_username", "username"),
    )


class Item(SQLModel, table=True):
    """Item being auctioned."""

    __tablename__ = "items"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=500)
    description: Optional[str] = Field(default=None)
    category: str = Field(max_length=100, index=True)
    image_url: Optional[str] = Field(default=None)
    seller_name: str = Field(max_length=255)
    auction_platform: str = Field(default="instagram", max_length=50)
    live_room_id: Optional[str] = Field(default=None, max_length=255)
    current_price: float = Field(default=0.0)
    estimated_value: Optional[float] = Field(default=None)
    target_buy_price: Optional[float] = Field(default=None)
    confidence_score: Optional[float] = Field(default=None)
    status: str = Field(default="active", max_length=50)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("idx_item_category", "category"),
        Index("idx_item_status", "status"),
        Index("idx_item_created_at", "created_at"),
    )


class Valuation(SQLModel, table=True):
    """Valuation record for items."""

    __tablename__ = "valuations"

    id: Optional[int] = Field(default=None, primary_key=True)
    item_id: int = Field(foreign_key="items.id", index=True)
    source: str = Field(max_length=50)  # ebay, etsy, sahibinden
    estimated_price: float
    confidence: float = Field(ge=0.0, le=1.0)
    comparables: dict = Field(default={}, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("idx_valuation_item_id", "item_id"),
        Index("idx_valuation_source", "source"),
    )


class Bid(SQLModel, table=True):
    """Bid records."""

    __tablename__ = "bids"

    id: Optional[int] = Field(default=None, primary_key=True)
    item_id: int = Field(foreign_key="items.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    bid_amount: float
    bid_type: str = Field(max_length=20)  # auto, semi-auto, manual
    decision_reason: Optional[str] = Field(default=None)
    success: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("idx_bid_item_id", "item_id"),
        Index("idx_bid_user_id", "user_id"),
        Index("idx_bid_created_at", "created_at"),
    )


class InstagramCredential(SQLModel, table=True):
    """Encrypted Instagram credentials."""

    __tablename__ = "instagram_credentials"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True, index=True)
    encrypted_username: str = Field(max_length=500)
    encrypted_password: str = Field(max_length=500)
    is_verified: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("idx_instagram_user_id", "user_id"),
    )
