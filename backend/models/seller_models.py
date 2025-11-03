"""
Seller Intelligence Models (Phase 12).
"""
from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel


class SellerProfile(SQLModel, table=True):
    """
    Seller behavioral profile.
    
    Stores aggregated analytics for marketplace sellers.
    """
    __tablename__ = "seller_profiles"
    
    id: int = Field(default=None, primary_key=True)
    seller_id: str = Field(max_length=200, index=True)
    source: str = Field(max_length=50, index=True)  # ebay, etsy, etc.
    
    # Pricing metrics
    avg_start_price: float = Field(default=0.0, ge=0)
    avg_final_price: float = Field(default=0.0, ge=0)
    discount_rate: float = Field(default=0.0, ge=0, le=1)  # Average discount %
    price_variance: float = Field(default=0.0, ge=0)  # Coefficient of variation
    
    # Behavioral metrics
    sale_speed: float = Field(default=0.0, ge=0)  # Avg days to sale
    trend_alignment: float = Field(default=0.5, ge=0, le=1)  # Market trend correlation
    activity_score: float = Field(default=0.0, ge=0, le=1)  # Listing frequency
    
    # Trust & reliability
    reliability_score: float = Field(default=0.0, ge=0, le=1)
    trust_score: float = Field(default=0.5, ge=0, le=1)
    
    # Statistics
    listing_count: int = Field(default=0, ge=0)
    successful_sales: int = Field(default=0, ge=0)
    
    # Metadata
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow, index=True)
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SellerTrend(SQLModel, table=True):
    """
    Seller trend data (7-day rolling window).
    
    Stores daily snapshots for trend analysis.
    """
    __tablename__ = "seller_trends"
    
    id: int = Field(default=None, primary_key=True)
    seller_profile_id: int = Field(foreign_key="seller_profiles.id", index=True)
    
    # Daily metrics
    date: datetime = Field(index=True)
    avg_price: float = Field(default=0.0)
    listing_count: int = Field(default=0)
    discount_rate: float = Field(default=0.0)
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
