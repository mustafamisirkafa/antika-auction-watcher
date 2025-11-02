"""
AutoBid Control API Router for Phase 10.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from pydantic import BaseModel

from backend.db.database import get_session as get_db
from backend.routers.auth import get_current_user
from backend.middleware.team_context import get_team_context, TeamContext
from backend.models.team_models import MemberRole
from backend.db.models import User
from backend.services.plan_seeder import get_plan_limit

router = APIRouter(prefix="/api/v1/autobid", tags=["autobid"])


# === Pydantic Schemas ===

class AutoBidStartRequest(BaseModel):
    auction_id: str
    rule_id: Optional[int] = None


class AutoBidStopRequest(BaseModel):
    auction_id: str


# === Helpers ===

def check_agent_limit(team_context: TeamContext):
    """Check if team can use AutoBid (requires agent slots)."""
    plan_limit = get_plan_limit(team_context.team.plan_code)
    
    # AutoBid requires PRO+ (agent_limit >= 25)
    if plan_limit < 25:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "message": f"AutoBid requires PRO or ENTERPRISE plan. Your {team_context.team.plan_code} plan does not have access.",
                "current_plan": team_context.team.plan_code,
                "required_plan": "PRO",
                "upgrade_url": "/settings/plan",
                "feature": "autobid"
            }
        )


# === Endpoints ===

@router.post("/start", status_code=status.HTTP_200_OK)
async def start_autobid(
    request: AutoBidStartRequest,
    team_context: TeamContext = Depends(get_team_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start AutoBid for an auction.
    
    Requires:
    - ANALYST+ role
    - PRO/ENTERPRISE plan
    - Valid bid rule (optional)
    """
    # Check role
    if team_context.role not in [MemberRole.OWNER, MemberRole.ADMIN, MemberRole.ANALYST]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ANALYST, ADMIN, or OWNER can start AutoBid"
        )
    
    # Check plan
    check_agent_limit(team_context)
    
    # TODO: Check agent limit availability
    # active_agents = get_active_agent_count(team_context.team.id)
    # if active_agents >= plan_limit:
    #     raise HTTPException(402, "Agent limit reached")
    
    # Get bid rule if specified
    rule = None
    if request.rule_id:
        from backend.models.bid_rules import BidRule
        rule = db.get(BidRule, request.rule_id)
        
        if not rule or rule.team_id != team_context.team.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bid rule not found"
            )
        
        if rule.status != "enabled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bid rule is disabled"
            )
    
    # TODO: Enable AutoBid in engine
    # from backend.services.autobid_engine import get_autobid_engine
    # engine = get_autobid_engine()
    # await engine.enable_autobid(
    #     team_id=team_context.team.id,
    #     auction_id=request.auction_id,
    #     rules=rule.dict() if rule else None
    # )
    
    return {
        "status": "started",
        "auction_id": request.auction_id,
        "team_id": team_context.team.id,
        "rule_id": request.rule_id,
        "message": "AutoBid started successfully"
    }


@router.post("/stop", status_code=status.HTTP_200_OK)
async def stop_autobid(
    request: AutoBidStopRequest,
    team_context: TeamContext = Depends(get_team_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Stop AutoBid for an auction.
    
    Requires ANALYST+ role.
    """
    # Check role
    if team_context.role not in [MemberRole.OWNER, MemberRole.ADMIN, MemberRole.ANALYST]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only ANALYST, ADMIN, or OWNER can stop AutoBid"
        )
    
    # TODO: Disable AutoBid in engine
    # from backend.services.autobid_engine import get_autobid_engine
    # engine = get_autobid_engine()
    # await engine.disable_autobid(request.auction_id)
    
    return {
        "status": "stopped",
        "auction_id": request.auction_id,
        "team_id": team_context.team.id,
        "message": "AutoBid stopped successfully"
    }


@router.get("/status", status_code=status.HTTP_200_OK)
async def get_autobid_status(
    auction_id: Optional[str] = None,
    team_context: TeamContext = Depends(get_team_context),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get AutoBid status.
    
    If auction_id provided, returns status for that auction.
    Otherwise, returns list of all active AutoBids for team.
    """
    # TODO: Get status from engine
    # from backend.services.autobid_engine import get_autobid_engine
    # engine = get_autobid_engine()
    # status = engine.get_status(auction_id)
    
    # Mock response
    if auction_id:
        return {
            "auction_id": auction_id,
            "team_id": team_context.team.id,
            "status": "inactive",
            "message": "AutoBid not active for this auction"
        }
    else:
        return {
            "team_id": team_context.team.id,
            "active_auctions": [],
            "count": 0
        }
