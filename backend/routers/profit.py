"""
Profit Advisor API for Antika Auction Watcher.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlmodel import Session, select
from pydantic import BaseModel
from datetime import datetime

from backend.models.profit import AuctionItem, ProfitEstimate, MarketReference
from backend.services.profit_advisor import ProfitAdvisorService
from backend.middleware.team_context import TeamContext, get_team_context
from backend.db.database import get_session as get_db
from backend.routers.auth import get_current_user
from backend.models.team_models import Team
from backend.services.plan_seeder import get_plan_limit

router = APIRouter(prefix="/profit", tags=["profit"])


# Request/Response Models

class AuctionItemCreate(BaseModel):
    """Request model for creating auction item."""
    lot_id: str
    title: str
    category: str
    image_url: Optional[str] = None
    starting_price: float
    auction_date: datetime
    source: str


class AuctionItemResponse(BaseModel):
    """Response model for auction item."""
    id: int
    lot_id: str
    title: str
    category: str
    image_url: Optional[str]
    starting_price: float
    auction_date: datetime
    source: str
    team_id: int
    created_at: datetime


class MarketReferenceResponse(BaseModel):
    """Response model for market reference."""
    id: int
    source: str
    avg_price: float
    sample_size: int
    liquidity_score: float
    last_checked: datetime


class ProfitEstimateResponse(BaseModel):
    """Response model for profit estimate."""
    id: int
    auction_item_id: int
    estimated_value: float
    recommended_max_bid: float
    profit_margin: float
    profit_amount: float
    confidence: float
    risk_level: str
    market_volatility: float
    liquidity_avg: float
    created_at: datetime
    expires_at: Optional[datetime]
    
    # Include auction item details
    auction_item: Optional[AuctionItemResponse] = None


class AnalyzeRequest(BaseModel):
    """Request model for analysis trigger."""
    auction_item_ids: Optional[List[int]] = None  # If None, analyze all
    force_refresh: bool = False


class AnalyzeResponse(BaseModel):
    """Response model for analysis trigger."""
    analyzed_count: int
    estimates: List[ProfitEstimateResponse]


# Helper Functions

def check_profit_advisor_access(team_context: TeamContext) -> None:
    """
    Check if team has access to profit advisor (PRO/ENTERPRISE only).
    
    Args:
        team_context: Team context
        
    Raises:
        HTTPException: If access denied
    """
    plan_limit = get_plan_limit(team_context.team.plan_code)
    
    # Profit advisor requires PRO or ENTERPRISE (agent_limit >= 25)
    if plan_limit < 25:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "message": f"Profit Advisor requires PRO or ENTERPRISE plan. Your {team_context.team.plan_code} plan does not have access.",
                "current_plan": team_context.team.plan_code,
                "required_plan": "PRO",
                "upgrade_url": "/settings/plan",
                "feature": "profit_advisor"
            }
        )


# Endpoints

@router.post("/items", response_model=AuctionItemResponse, status_code=status.HTTP_201_CREATED)
async def create_auction_item(
    item_data: AuctionItemCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    team_context: TeamContext = Depends(get_team_context)
):
    """
    Create a new auction item for profit analysis.
    Requires PRO or ENTERPRISE plan.
    """
    # Check access
    check_profit_advisor_access(team_context)
    
    # Check permissions
    if not team_context.can_manage_agents():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to create auction items"
        )
    
    # Create auction item
    auction_item = AuctionItem(
        lot_id=item_data.lot_id,
        title=item_data.title,
        category=item_data.category,
        image_url=item_data.image_url,
        starting_price=item_data.starting_price,
        auction_date=item_data.auction_date,
        source=item_data.source,
        team_id=team_context.team_id
    )
    
    db.add(auction_item)
    db.commit()
    db.refresh(auction_item)
    
    return AuctionItemResponse(
        id=auction_item.id,
        lot_id=auction_item.lot_id,
        title=auction_item.title,
        category=auction_item.category,
        image_url=auction_item.image_url,
        starting_price=auction_item.starting_price,
        auction_date=auction_item.auction_date,
        source=auction_item.source,
        team_id=auction_item.team_id,
        created_at=auction_item.created_at
    )


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_items(
    analyze_request: AnalyzeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    team_context: TeamContext = Depends(get_team_context)
):
    """
    Trigger profit analysis for auction items.
    Requires PRO or ENTERPRISE plan.
    """
    # Check access
    check_profit_advisor_access(team_context)
    
    # Check permissions
    if not team_context.can_manage_agents():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to trigger analysis"
        )
    
    # Get auction items to analyze
    if analyze_request.auction_item_ids:
        statement = select(AuctionItem).where(
            AuctionItem.id.in_(analyze_request.auction_item_ids),
            AuctionItem.team_id == team_context.team_id
        )
        items = db.exec(statement).all()
    else:
        # Analyze all upcoming items for the team
        statement = select(AuctionItem).where(
            AuctionItem.team_id == team_context.team_id,
            AuctionItem.auction_date > datetime.utcnow()
        )
        items = db.exec(statement).all()
    
    if not items:
        return AnalyzeResponse(analyzed_count=0, estimates=[])
    
    # Create profit advisor service
    advisor = ProfitAdvisorService(db)
    
    # Analyze items
    import asyncio
    estimates = await asyncio.gather(*[
        advisor.analyze_item(item, force_refresh=analyze_request.force_refresh)
        for item in items
    ])
    
    # Build response
    estimate_responses = []
    for estimate in estimates:
        # Get auction item
        auction_item = db.get(AuctionItem, estimate.auction_item_id)
        
        estimate_responses.append(ProfitEstimateResponse(
            id=estimate.id,
            auction_item_id=estimate.auction_item_id,
            estimated_value=estimate.estimated_value,
            recommended_max_bid=estimate.recommended_max_bid,
            profit_margin=estimate.profit_margin,
            profit_amount=estimate.profit_amount,
            confidence=estimate.confidence,
            risk_level=estimate.risk_level,
            market_volatility=estimate.market_volatility,
            liquidity_avg=estimate.liquidity_avg,
            created_at=estimate.created_at,
            expires_at=estimate.expires_at,
            auction_item=AuctionItemResponse(
                id=auction_item.id,
                lot_id=auction_item.lot_id,
                title=auction_item.title,
                category=auction_item.category,
                image_url=auction_item.image_url,
                starting_price=auction_item.starting_price,
                auction_date=auction_item.auction_date,
                source=auction_item.source,
                team_id=auction_item.team_id,
                created_at=auction_item.created_at
            ) if auction_item else None
        ))
    
    return AnalyzeResponse(
        analyzed_count=len(estimates),
        estimates=estimate_responses
    )


@router.get("/{team_id}", response_model=List[ProfitEstimateResponse])
async def get_team_estimates(
    team_id: int,
    min_confidence: Optional[float] = None,
    max_risk: Optional[str] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Get profit estimates for a team.
    Requires PRO or ENTERPRISE plan.
    """
    # Validate team membership
    request.headers.__dict__["_list"] = [
        (b"x-team-id", str(team_id).encode())
    ]
    team_context = await get_team_context(request, db, current_user.id, require_team=True)
    
    # Check access
    check_profit_advisor_access(team_context)
    
    # Get estimates
    advisor = ProfitAdvisorService(db)
    estimates = advisor.get_team_estimates(
        team_id,
        min_confidence=min_confidence,
        max_risk=max_risk
    )
    
    # Build response
    estimate_responses = []
    for estimate in estimates:
        # Get auction item
        auction_item = db.get(AuctionItem, estimate.auction_item_id)
        
        estimate_responses.append(ProfitEstimateResponse(
            id=estimate.id,
            auction_item_id=estimate.auction_item_id,
            estimated_value=estimate.estimated_value,
            recommended_max_bid=estimate.recommended_max_bid,
            profit_margin=estimate.profit_margin,
            profit_amount=estimate.profit_amount,
            confidence=estimate.confidence,
            risk_level=estimate.risk_level,
            market_volatility=estimate.market_volatility,
            liquidity_avg=estimate.liquidity_avg,
            created_at=estimate.created_at,
            expires_at=estimate.expires_at,
            auction_item=AuctionItemResponse(
                id=auction_item.id,
                lot_id=auction_item.lot_id,
                title=auction_item.title,
                category=auction_item.category,
                image_url=auction_item.image_url,
                starting_price=auction_item.starting_price,
                auction_date=auction_item.auction_date,
                source=auction_item.source,
                team_id=auction_item.team_id,
                created_at=auction_item.created_at
            ) if auction_item else None
        ))
    
    return estimate_responses


@router.get("/item/{item_id}", response_model=ProfitEstimateResponse)
async def get_item_estimate(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    team_context: TeamContext = Depends(get_team_context)
):
    """
    Get profit estimate for a specific auction item.
    Requires PRO or ENTERPRISE plan.
    """
    # Check access
    check_profit_advisor_access(team_context)
    
    # Get auction item
    auction_item = db.get(AuctionItem, item_id)
    if not auction_item:
        raise HTTPException(status_code=404, detail="Auction item not found")
    
    # Verify team ownership
    if auction_item.team_id != team_context.team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Item does not belong to your team"
        )
    
    # Get latest estimate
    statement = select(ProfitEstimate).where(
        ProfitEstimate.auction_item_id == item_id
    ).order_by(ProfitEstimate.created_at.desc())
    
    estimate = db.exec(statement).first()
    
    if not estimate:
        raise HTTPException(status_code=404, detail="No profit estimate found")
    
    return ProfitEstimateResponse(
        id=estimate.id,
        auction_item_id=estimate.auction_item_id,
        estimated_value=estimate.estimated_value,
        recommended_max_bid=estimate.recommended_max_bid,
        profit_margin=estimate.profit_margin,
        profit_amount=estimate.profit_amount,
        confidence=estimate.confidence,
        risk_level=estimate.risk_level,
        market_volatility=estimate.market_volatility,
        liquidity_avg=estimate.liquidity_avg,
        created_at=estimate.created_at,
        expires_at=estimate.expires_at,
        auction_item=AuctionItemResponse(
            id=auction_item.id,
            lot_id=auction_item.lot_id,
            title=auction_item.title,
            category=auction_item.category,
            image_url=auction_item.image_url,
            starting_price=auction_item.starting_price,
            auction_date=auction_item.auction_date,
            source=auction_item.source,
            team_id=auction_item.team_id,
            created_at=auction_item.created_at
        )
    )


@router.get("/market-references/{item_id}", response_model=List[MarketReferenceResponse])
async def get_market_references(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    team_context: TeamContext = Depends(get_team_context)
):
    """
    Get market references for an auction item.
    Requires PRO or ENTERPRISE plan.
    """
    # Check access
    check_profit_advisor_access(team_context)
    
    # Get auction item
    auction_item = db.get(AuctionItem, item_id)
    if not auction_item:
        raise HTTPException(status_code=404, detail="Auction item not found")
    
    # Verify team ownership
    if auction_item.team_id != team_context.team_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Item does not belong to your team"
        )
    
    # Get market references
    statement = select(MarketReference).where(
        MarketReference.auction_item_id == item_id
    ).order_by(MarketReference.last_checked.desc())
    
    references = db.exec(statement).all()
    
    return [
        MarketReferenceResponse(
            id=ref.id,
            source=ref.source,
            avg_price=ref.avg_price,
            sample_size=ref.sample_size,
            liquidity_score=ref.liquidity_score,
            last_checked=ref.last_checked
        )
        for ref in references
    ]
