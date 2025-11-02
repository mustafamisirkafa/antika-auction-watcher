"""
Plan Management API for Antika Auction Watcher.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from pydantic import BaseModel
import json

from backend.models.team_models import Plan

router = APIRouter(prefix="/plans", tags=["plans"])


# Response Models

class PlanResponse(BaseModel):
    """Response model for plan."""
    code: str
    agent_limit: int
    description: str
    features: List[str]
    price_monthly: float
    
    @classmethod
    def from_plan(cls, plan: Plan):
        """Create response from Plan model."""
        return cls(
            code=plan.code,
            agent_limit=plan.agent_limit,
            description=plan.description,
            features=json.loads(plan.features) if plan.features else [],
            price_monthly=plan.price_monthly or 0.0
        )


class PlanComparison(BaseModel):
    """Plan comparison model."""
    free: PlanResponse
    pro: PlanResponse
    enterprise: PlanResponse


# Endpoints

@router.get("", response_model=List[PlanResponse])
async def list_plans(db: Session = Depends(get_db)):
    """
    List all available plans.
    Public endpoint - no authentication required.
    """
    statement = select(Plan).order_by(Plan.agent_limit)
    plans = db.exec(statement).all()
    
    return [PlanResponse.from_plan(plan) for plan in plans]


@router.get("/compare", response_model=PlanComparison)
async def compare_plans(db: Session = Depends(get_db)):
    """
    Get plan comparison data.
    Public endpoint for pricing page.
    """
    plans = {}
    
    for code in ["FREE", "PRO", "ENTERPRISE"]:
        statement = select(Plan).where(Plan.code == code)
        plan = db.exec(statement).first()
        if plan:
            plans[code.lower()] = PlanResponse.from_plan(plan)
    
    return PlanComparison(**plans)


@router.get("/{plan_code}", response_model=PlanResponse)
async def get_plan(plan_code: str, db: Session = Depends(get_db)):
    """
    Get specific plan details.
    Public endpoint.
    """
    statement = select(Plan).where(Plan.code == plan_code.upper())
    plan = db.exec(statement).first()
    
    if not plan:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return PlanResponse.from_plan(plan)


# Import dependency
from backend.db.database import get_session as get_db
