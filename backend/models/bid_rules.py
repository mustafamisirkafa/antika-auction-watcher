"""
Bid Rules Models for AutoBid (Phase 10).
"""
from typing import Optional, Literal
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

from backend.models.team_models import Team


class BidRule(SQLModel, table=True):
    """
    User-defined bidding rules for AutoBid.
    
    Controls when and how AutoBid places bids.
    """
    __tablename__ = "bid_rules"
    
    id: int = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="teams.id", index=True)
    
    # Rule identification
    name: str = Field(max_length=200)
    category: Optional[str] = Field(default=None, max_length=100, index=True)
    
    # Bid limits
    max_bid: float = Field(ge=0)  # Maximum bid amount
    min_confidence: float = Field(default=0.6, ge=0, le=1)  # Min confidence score
    step: float = Field(default=25.0, ge=1)  # Bid increment step
    stop_loss_pct: float = Field(default=0.1, ge=0, le=1)  # Stop-loss percentage
    
    # Risk settings
    allow_high_risk: bool = Field(default=False)
    max_volatility: float = Field(default=0.5, ge=0, le=1)
    
    # Mode
    mode: Literal["shadow", "auto"] = Field(default="shadow")
    status: Literal["enabled", "disabled"] = Field(default="enabled", index=True)
    
    # Metadata
    created_by: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    team: Team = Relationship()


class AutoBidAudit(SQLModel, table=True):
    """
    Audit log for AutoBid decisions and actions.
    """
    __tablename__ = "autobid_audit"
    
    id: int = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="teams.id", index=True)
    auction_id: str = Field(max_length=100, index=True)
    item_id: str = Field(max_length=100, index=True)
    
    # Event details
    event_type: Literal["decision", "bid", "result"] = Field(index=True)
    
    # Decision info
    current_price: Optional[float] = None
    rec_max_bid: Optional[float] = None
    next_bid: Optional[float] = None
    confidence: Optional[float] = None
    risk_level: Optional[str] = None
    
    # Policy decision
    decision_ok: bool
    decision_reason: str = Field(max_length=500)
    blocked_by: Optional[str] = Field(default=None, max_length=100)
    
    # Bid execution
    bid_amount: Optional[float] = None
    bid_result: Optional[Literal["accepted", "rejected", "timeout", "error", "simulated"]] = None
    
    # Rule applied
    rule_id: Optional[int] = Field(default=None, foreign_key="bid_rules.id")
    mode: Literal["shadow", "auto"] = Field(default="shadow")
    
    # Performance
    latency_ms: Optional[float] = None
    
    # Timestamp
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
