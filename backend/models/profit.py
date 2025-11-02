"""
Profit Advisor models for Antika Auction Watcher.
Pre-auction intelligence and profit estimation.
"""
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Column, String, Relationship
from sqlalchemy import Index, Float


class AuctionItem(SQLModel, table=True):
    """
    Upcoming auction items for profit analysis.
    """
    __tablename__ = "auction_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    lot_id: str = Field(max_length=100, index=True)
    title: str = Field(max_length=500)
    category: str = Field(max_length=100, index=True)
    image_url: Optional[str] = Field(default=None, max_length=1000)
    
    # Auction details
    starting_price: float = Field(ge=0.0)
    auction_date: datetime = Field(index=True)
    source: str = Field(max_length=100)  # Platform/auction house
    
    # Team association
    team_id: int = Field(foreign_key="teams.id", index=True)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    market_references: list["MarketReference"] = Relationship(back_populates="auction_item")
    profit_estimates: list["ProfitEstimate"] = Relationship(back_populates="auction_item")
    
    __table_args__ = (
        Index("idx_auction_item_lot_id", "lot_id"),
        Index("idx_auction_item_category", "category"),
        Index("idx_auction_item_auction_date", "auction_date"),
        Index("idx_auction_item_team_id", "team_id"),
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "lot_id": "LOT-2025-1234",
                "title": "19th Century Silver Candleholder",
                "category": "silver",
                "starting_price": 800.0,
                "auction_date": "2025-11-10T14:00:00Z",
                "source": "Christie's Online",
                "team_id": 1
            }
        }


class MarketReference(SQLModel, table=True):
    """
    Market reference data from various sources.
    Used to calculate average market prices and liquidity.
    """
    __tablename__ = "market_references"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    auction_item_id: int = Field(foreign_key="auction_items.id", index=True)
    
    # Market data source
    source: str = Field(max_length=50, index=True)  # ebay, etsy, sahibinden, letgo
    
    # Market metrics
    avg_price: float = Field(ge=0.0)
    sample_size: int = Field(ge=0, default=0)
    liquidity_score: float = Field(ge=0.0, le=1.0)  # 0-1 scale
    
    # Timestamps
    last_checked: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationship
    auction_item: AuctionItem = Relationship(back_populates="market_references")
    
    __table_args__ = (
        Index("idx_market_ref_auction_item", "auction_item_id"),
        Index("idx_market_ref_source", "source"),
        Index("idx_market_ref_last_checked", "last_checked"),
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "auction_item_id": 1,
                "source": "ebay",
                "avg_price": 1150.0,
                "sample_size": 23,
                "liquidity_score": 0.87,
                "last_checked": "2025-11-02T12:00:00Z"
            }
        }


class ProfitEstimate(SQLModel, table=True):
    """
    AI-generated profit estimates for auction items.
    Includes recommended max bid and confidence scores.
    """
    __tablename__ = "profit_estimates"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    auction_item_id: int = Field(foreign_key="auction_items.id", index=True)
    
    # Valuation
    estimated_value: float = Field(ge=0.0)  # Market average
    recommended_max_bid: float = Field(ge=0.0)  # AI recommendation
    
    # Profit analysis
    profit_margin: float = Field(ge=-1.0)  # Can be negative if overpriced
    profit_amount: float  # Absolute profit in currency
    
    # Confidence & risk
    confidence: float = Field(ge=0.0, le=1.0)  # 0-1 scale
    risk_level: str = Field(max_length=20, default="medium")  # low, medium, high
    
    # Market analysis
    market_volatility: float = Field(ge=0.0, le=1.0, default=0.5)
    liquidity_avg: float = Field(ge=0.0, le=1.0, default=0.7)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    expires_at: Optional[datetime] = Field(default=None)  # When estimate becomes stale
    
    # Relationship
    auction_item: AuctionItem = Relationship(back_populates="profit_estimates")
    
    __table_args__ = (
        Index("idx_profit_estimate_auction_item", "auction_item_id"),
        Index("idx_profit_estimate_created_at", "created_at"),
        Index("idx_profit_estimate_confidence", "confidence"),
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "auction_item_id": 1,
                "estimated_value": 1160.0,
                "recommended_max_bid": 950.0,
                "profit_margin": 0.22,
                "profit_amount": 210.0,
                "confidence": 0.82,
                "risk_level": "low",
                "market_volatility": 0.25,
                "liquidity_avg": 0.87
            }
        }
