"""
Plan seeder for Antika Auction Watcher.
Seeds static plan data on application startup.
"""
import json
from typing import List
from sqlmodel import Session, select
from backend.models.team_models import Plan, PlanCode


# Static plan definitions
PLAN_DEFINITIONS = [
    {
        "code": PlanCode.FREE,
        "agent_limit": 3,
        "description": "Up to 3 AI watcher agents, no autobid",
        "features": json.dumps([
            "3 active agents",
            "Manual bidding only",
            "Basic analytics",
            "7-day data retention",
            "Community support"
        ]),
        "price_monthly": 0.0
    },
    {
        "code": PlanCode.PRO,
        "agent_limit": 25,
        "description": "Up to 25 watcher/bidder agents",
        "features": json.dumps([
            "25 active agents",
            "Automatic bidding",
            "Advanced analytics",
            "30-day data retention",
            "Learning insights",
            "Priority support",
            "Export to CSV"
        ]),
        "price_monthly": 49.99
    },
    {
        "code": PlanCode.ENTERPRISE,
        "agent_limit": 100,
        "description": "Up to 100 agents + advanced analysis",
        "features": json.dumps([
            "100 active agents",
            "Custom agent strategies",
            "Real-time market analysis",
            "Unlimited data retention",
            "API access",
            "White-label options",
            "Dedicated account manager",
            "SLA guarantee"
        ]),
        "price_monthly": 199.99
    }
]


def seed_plans(session: Session) -> List[Plan]:
    """
    Seed plan data into the database.
    Idempotent - updates existing plans if they exist.
    
    Args:
        session: Database session
        
    Returns:
        List of created/updated plans
    """
    plans = []
    
    for plan_def in PLAN_DEFINITIONS:
        # Check if plan exists
        statement = select(Plan).where(Plan.code == plan_def["code"])
        existing_plan = session.exec(statement).first()
        
        if existing_plan:
            # Update existing plan
            existing_plan.agent_limit = plan_def["agent_limit"]
            existing_plan.description = plan_def["description"]
            existing_plan.features = plan_def["features"]
            existing_plan.price_monthly = plan_def["price_monthly"]
            session.add(existing_plan)
            plans.append(existing_plan)
        else:
            # Create new plan
            new_plan = Plan(**plan_def)
            session.add(new_plan)
            plans.append(new_plan)
    
    session.commit()
    
    for plan in plans:
        session.refresh(plan)
    
    return plans


def get_plan_info(plan_code: str) -> dict:
    """
    Get static plan information without database query.
    Useful for quick lookups and validation.
    
    Args:
        plan_code: Plan code (FREE, PRO, ENTERPRISE)
        
    Returns:
        Plan information dictionary
    """
    for plan_def in PLAN_DEFINITIONS:
        if plan_def["code"] == plan_code:
            return plan_def
    
    # Default to FREE if not found
    return PLAN_DEFINITIONS[0]


def get_plan_limit(plan_code: str) -> int:
    """
    Get agent limit for a plan code.
    
    Args:
        plan_code: Plan code
        
    Returns:
        Agent limit (integer)
    """
    plan_info = get_plan_info(plan_code)
    return plan_info["agent_limit"]


def validate_plan_code(plan_code: str) -> bool:
    """
    Validate if a plan code exists.
    
    Args:
        plan_code: Plan code to validate
        
    Returns:
        True if valid, False otherwise
    """
    return any(p["code"] == plan_code for p in PLAN_DEFINITIONS)
