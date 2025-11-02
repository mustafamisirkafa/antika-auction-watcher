"""
Bid Rules API Router for AutoBid (Phase 10).
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel

from backend.db.database import get_session as get_db
from backend.routers.auth import get_current_user
from backend.middleware.team_context import get_team_context, TeamContext, require_role
from backend.models.bid_rules import BidRule
from backend.models.team_models import MemberRole
from backend.db.models import User

router = APIRouter(prefix="/api/v1/bid-rules", tags=["autobid"])


# === Pydantic Schemas ===

class BidRuleCreate(BaseModel):
    name: str
    category: Optional[str] = None
    max_bid: float
    min_confidence: float = 0.6
    step: float = 25.0
    stop_loss_pct: float = 0.1
    allow_high_risk: bool = False
    max_volatility: float = 0.5
    mode: str = "shadow"  # "shadow" or "auto"


class BidRuleUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    max_bid: Optional[float] = None
    min_confidence: Optional[float] = None
    step: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    allow_high_risk: Optional[bool] = None
    max_volatility: Optional[float] = None
    mode: Optional[str] = None
    status: Optional[str] = None


# === Endpoints ===

@router.get("")
async def list_bid_rules(
    team_context: TeamContext = Depends(get_team_context),
    db: Session = Depends(get_db),
    category: Optional[str] = None,
    status: Optional[str] = None
):
    """List all bid rules for team."""
    query = select(BidRule).where(BidRule.team_id == team_context.team.id)
    
    if category:
        query = query.where(BidRule.category == category)
    
    if status:
        query = query.where(BidRule.status == status)
    
    rules = db.exec(query.order_by(BidRule.created_at.desc())).all()
    
    return rules


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_bid_rule(
    rule_data: BidRuleCreate,
    team_context: TeamContext = Depends(get_team_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new bid rule (requires ANALYST+ role)."""
    # Check role
    if team_context.role not in [MemberRole.OWNER, MemberRole.ADMIN, MemberRole.ANALYST]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ANALYST, ADMIN, or OWNER can create bid rules"
        )
    
    # Validate mode
    if rule_data.mode not in ["shadow", "auto"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mode must be 'shadow' or 'auto'"
        )
    
    # Create rule
    rule = BidRule(
        team_id=team_context.team.id,
        name=rule_data.name,
        category=rule_data.category,
        max_bid=rule_data.max_bid,
        min_confidence=rule_data.min_confidence,
        step=rule_data.step,
        stop_loss_pct=rule_data.stop_loss_pct,
        allow_high_risk=rule_data.allow_high_risk,
        max_volatility=rule_data.max_volatility,
        mode=rule_data.mode,
        created_by=current_user.id
    )
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return rule


@router.get("/{rule_id}")
async def get_bid_rule(
    rule_id: int,
    team_context: TeamContext = Depends(get_team_context),
    db: Session = Depends(get_db)
):
    """Get bid rule by ID."""
    rule = db.get(BidRule, rule_id)
    
    if not rule or rule.team_id != team_context.team.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bid rule not found"
        )
    
    return rule


@router.patch("/{rule_id}")
async def update_bid_rule(
    rule_id: int,
    rule_data: BidRuleUpdate,
    team_context: TeamContext = Depends(get_team_context),
    db: Session = Depends(get_db)
):
    """Update bid rule (requires ANALYST+ role)."""
    # Check role
    if team_context.role not in [MemberRole.OWNER, MemberRole.ADMIN, MemberRole.ANALYST]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ANALYST, ADMIN, or OWNER can update bid rules"
        )
    
    # Get rule
    rule = db.get(BidRule, rule_id)
    
    if not rule or rule.team_id != team_context.team.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bid rule not found"
        )
    
    # Update fields
    update_data = rule_data.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(rule, key, value)
    
    rule.updated_at = datetime.utcnow()
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bid_rule(
    rule_id: int,
    team_context: TeamContext = Depends(get_team_context),
    db: Session = Depends(get_db)
):
    """Delete bid rule (requires ADMIN+ role)."""
    # Check role
    if team_context.role not in [MemberRole.OWNER, MemberRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ADMIN or OWNER can delete bid rules"
        )
    
    # Get rule
    rule = db.get(BidRule, rule_id)
    
    if not rule or rule.team_id != team_context.team.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bid rule not found"
        )
    
    db.delete(rule)
    db.commit()
    
    return None
