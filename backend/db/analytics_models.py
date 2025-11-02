"""Analytics-specific database models."""
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Column, JSON
from sqlalchemy import Index


class BidOutcome(SQLModel, table=True):
    """Bid outcome tracking for learning loop."""
    
    __tablename__ = "bid_outcomes"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    bid_id: int = Field(foreign_key="bids.id", index=True)
    item_id: int = Field(foreign_key="items.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    
    # Valuation data
    estimated_value: float
    target_buy_price: float
    actual_bid_amount: float
    confidence_score: float
    
    # Outcome data
    won_auction: bool = Field(default=False)
    actual_resale_price: Optional[float] = Field(default=None)
    resale_date: Optional[datetime] = Field(default=None)
    
    # Profitability metrics
    gross_profit: Optional[float] = Field(default=None)
    profit_margin: Optional[float] = Field(default=None)
    roi: Optional[float] = Field(default=None)
    
    # Learning data
    valuation_accuracy: Optional[float] = Field(default=None)
    margin_effectiveness: Optional[float] = Field(default=None)
    
    # Metadata
    category: str = Field(max_length=100, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_outcome_bid_id", "bid_id"),
        Index("idx_outcome_item_id", "item_id"),
        Index("idx_outcome_category", "category"),
        Index("idx_outcome_created_at", "created_at"),
    )


class CategoryMetrics(SQLModel, table=True):
    """Aggregated metrics per category."""
    
    __tablename__ = "category_metrics"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    category: str = Field(unique=True, max_length=100, index=True)
    
    # Success metrics
    total_bids: int = Field(default=0)
    won_bids: int = Field(default=0)
    win_rate: float = Field(default=0.0)
    
    # Profitability metrics
    total_profit: float = Field(default=0.0)
    average_profit: float = Field(default=0.0)
    average_roi: float = Field(default=0.0)
    
    # Accuracy metrics
    average_valuation_accuracy: float = Field(default=0.0)
    confidence_correlation: float = Field(default=0.0)
    
    # Learning parameters
    recommended_safety_margin: float = Field(default=0.15)
    confidence_threshold: float = Field(default=0.6)
    
    # Metadata
    sample_size: int = Field(default=0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        Index("idx_category_metrics_category", "category"),
    )


class SystemMetrics(SQLModel, table=True):
    """System-wide performance metrics."""
    
    __tablename__ = "system_metrics"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    metric_type: str = Field(max_length=50, index=True)
    metric_name: str = Field(max_length=100)
    
    # Metric values
    value: float
    unit: str = Field(max_length=20)
    
    # Context
    metadata: dict = Field(default={}, sa_column=Column(JSON))
    
    # Timestamps
    recorded_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("idx_metrics_type", "metric_type"),
        Index("idx_metrics_recorded_at", "recorded_at"),
    )
