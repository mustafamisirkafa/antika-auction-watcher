"""
AI Advisor API Router
Provides endpoints for auction bidding recommendations
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from backend.services.advisor_service import (
    AdvisorService,
    AdvisorRecommendation,
    RecommendationLevel,
    RiskLevel
)

router = APIRouter(prefix="/advisor", tags=["advisor"])

# Initialize service
advisor_service = AdvisorService()


# ============================================================================
# Request/Response Models
# ============================================================================

class SenseScoreResponse(BaseModel):
    """Individual sense score response"""
    score: float = Field(..., ge=0.0, le=1.0, description="Score from 0 to 1")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence from 0 to 1")
    reasoning: str = Field(..., description="Human-readable reasoning")
    factors: dict = Field(default_factory=dict, description="Individual factors")


class AdvisorResponse(BaseModel):
    """Complete advisor recommendation response"""
    item_id: str
    recommendation: RecommendationLevel
    confidence: float = Field(..., ge=0.0, le=1.0)
    suggested_max_bid: Optional[float] = Field(None, description="Suggested maximum bid amount")
    reasoning: List[str] = Field(..., description="List of reasoning points")
    risk_level: RiskLevel
    
    # Individual sense scores
    pattern_sense: SenseScoreResponse
    market_sense: SenseScoreResponse
    behavior_sense: SenseScoreResponse
    risk_sense: SenseScoreResponse
    
    # Metadata
    timestamp: datetime
    expires_at: datetime
    
    class Config:
        use_enum_values = True


class BatchAnalysisRequest(BaseModel):
    """Request for batch analysis"""
    item_ids: List[str] = Field(..., min_items=1, max_items=50)
    user_id: Optional[str] = None
    include_details: bool = Field(default=True, description="Include full sense details")


class BatchAnalysisResponse(BaseModel):
    """Response for batch analysis"""
    recommendations: List[AdvisorResponse]
    total_analyzed: int
    processing_time_ms: float


class FeedbackRequest(BaseModel):
    """User feedback on recommendation"""
    item_id: str
    recommendation_id: str
    user_id: Optional[str] = None
    feedback_type: str = Field(..., description="helpful, not_helpful, inaccurate, accurate")
    recommendation_level: Optional[str] = None
    confidence: Optional[float] = None
    suggested_max_bid: Optional[float] = None
    comment: Optional[str] = None
    actual_outcome: Optional[dict] = Field(None, description="What actually happened")


# ============================================================================
# Helper Functions
# ============================================================================

async def get_mock_data(item_id: str) -> dict:
    """
    Get mock data for demonstration
    In production, this would fetch from database
    """
    return {
        "item_data": {
            "id": item_id,
            "category": "ceramics",
            "current_price": 450.0,
            "time_remaining_seconds": 1800,
            "condition": "very good",
            "title": "Vintage Iznik Ceramic Plate"
        },
        "historical_data": [
            {"category": "ceramics", "final_price": 520, "won": True, "profitability": 0.15},
            {"category": "ceramics", "final_price": 480, "won": True, "profitability": 0.20},
            {"category": "ceramics", "final_price": 550, "won": False, "profitability": 0},
            {"category": "ceramics", "final_price": 490, "won": True, "profitability": 0.18},
        ],
        "market_data": {
            "categories": {
                "ceramics": {
                    "demand_trend": 0.3,
                    "avg_bidders": 4
                }
            }
        },
        "active_bidders": [
            {"id": "bidder1", "bid_count": 3, "win_rate": 0.6},
            {"id": "bidder2", "bid_count": 1, "win_rate": 0.3}
        ],
        "user_history": [
            {"category": "ceramics", "bid_amount": 400, "won": True, "feedback": "helpful"},
            {"category": "ceramics", "bid_amount": 550, "won": False},
            {"category": "antiques", "bid_amount": 300, "won": True, "feedback": "accurate"},
        ],
        "user_preferences": {
            "preferred_categories": ["ceramics", "antiques"],
            "max_budget_per_item": 1000
        },
        "seller_data": {
            "rating": 4.7,
            "total_sales": 156,
            "disputes": 3,
            "has_return_policy": True
        },
        "valuation_data": {
            "estimated_value": 600,
            "confidence": 0.82,
            "source": "ai_valuation"
        }
    }


def convert_to_response(recommendation: AdvisorRecommendation) -> AdvisorResponse:
    """Convert service recommendation to API response"""
    return AdvisorResponse(
        item_id=recommendation.item_id,
        recommendation=recommendation.recommendation,
        confidence=recommendation.confidence,
        suggested_max_bid=recommendation.suggested_max_bid,
        reasoning=recommendation.reasoning,
        risk_level=recommendation.risk_level,
        pattern_sense=SenseScoreResponse(
            score=recommendation.pattern_sense.score,
            confidence=recommendation.pattern_sense.confidence,
            reasoning=recommendation.pattern_sense.reasoning,
            factors=recommendation.pattern_sense.factors
        ),
        market_sense=SenseScoreResponse(
            score=recommendation.market_sense.score,
            confidence=recommendation.market_sense.confidence,
            reasoning=recommendation.market_sense.reasoning,
            factors=recommendation.market_sense.factors
        ),
        behavior_sense=SenseScoreResponse(
            score=recommendation.behavior_sense.score,
            confidence=recommendation.behavior_sense.confidence,
            reasoning=recommendation.behavior_sense.reasoning,
            factors=recommendation.behavior_sense.factors
        ),
        risk_sense=SenseScoreResponse(
            score=recommendation.risk_sense.score,
            confidence=recommendation.risk_sense.confidence,
            reasoning=recommendation.risk_sense.reasoning,
            factors=recommendation.risk_sense.factors
        ),
        timestamp=recommendation.timestamp,
        expires_at=recommendation.expires_at
    )


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/suggest/{item_id}", response_model=AdvisorResponse)
async def get_suggestion(item_id: str):
    """
    Get AI recommendation for a specific item
    
    Args:
        item_id: Item identifier
        
    Returns:
        Comprehensive recommendation with all sense scores
        
    Example:
        GET /api/v1/advisor/suggest/item123
    """
    try:
        # Fetch data (mock for now)
        data = await get_mock_data(item_id)
        
        # Get recommendation
        recommendation = await advisor_service.get_recommendation(
            item_id=item_id,
            item_data=data["item_data"],
            historical_data=data["historical_data"],
            market_data=data["market_data"],
            active_bidders=data["active_bidders"],
            user_history=data["user_history"],
            user_preferences=data["user_preferences"],
            seller_data=data["seller_data"],
            valuation_data=data["valuation_data"]
        )
        
        return convert_to_response(recommendation)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendation: {str(e)}"
        )


@router.post("/analyze_batch", response_model=BatchAnalysisResponse)
async def analyze_batch(request: BatchAnalysisRequest):
    """
    Analyze multiple items in batch
    
    Args:
        request: Batch analysis request with item IDs
        
    Returns:
        List of recommendations for all items
        
    Example:
        POST /api/v1/advisor/analyze_batch
        {
            "item_ids": ["item1", "item2", "item3"],
            "user_id": "user123",
            "include_details": true
        }
    """
    start_time = datetime.utcnow()
    
    try:
        # Prepare batch data
        items = []
        for item_id in request.item_ids:
            data = await get_mock_data(item_id)
            items.append({
                "id": item_id,
                "data": data["item_data"],
                "active_bidders": data["active_bidders"],
                "seller_data": data["seller_data"],
                "valuation_data": data["valuation_data"]
            })
        
        # Shared context for all items
        first_data = await get_mock_data(request.item_ids[0])
        shared_context = {
            "historical_data": first_data["historical_data"],
            "market_data": first_data["market_data"],
            "user_history": first_data["user_history"],
            "user_preferences": first_data["user_preferences"]
        }
        
        # Get batch recommendations
        recommendations = await advisor_service.analyze_batch(items, shared_context)
        
        # Convert to responses
        responses = [convert_to_response(rec) for rec in recommendations]
        
        # Calculate processing time
        end_time = datetime.utcnow()
        processing_time_ms = (end_time - start_time).total_seconds() * 1000
        
        return BatchAnalysisResponse(
            recommendations=responses,
            total_analyzed=len(responses),
            processing_time_ms=processing_time_ms
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch analysis failed: {str(e)}"
        )


@router.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    Submit feedback on a recommendation
    
    Args:
        feedback: User feedback data
        
    Returns:
        Confirmation of feedback receipt
        
    Example:
        POST /api/v1/advisor/feedback
        {
            "item_id": "item123",
            "recommendation_id": "rec456",
            "feedback_type": "helpful",
            "comment": "Great advice, won the auction!",
            "actual_outcome": {"won": true, "final_price": 550}
        }
    """
    try:
        from backend.services.feedback_collector import FeedbackCollector, FeedbackType
        
        # Initialize collector
        collector = FeedbackCollector()
        await collector.initialize()
        
        # Add feedback
        entry = await collector.add_feedback(
            item_id=feedback.item_id,
            recommendation_id=feedback.recommendation_id,
            user_id=feedback.user_id or "anonymous",
            feedback_type=FeedbackType(feedback.feedback_type),
            recommendation_level=feedback.recommendation_level or "unknown",
            confidence=feedback.confidence or 0.5,
            suggested_max_bid=feedback.suggested_max_bid,
            comment=feedback.comment,
            actual_outcome=feedback.actual_outcome
        )
        
        return {
            "status": "success",
            "message": "Feedback received and will be used to improve recommendations",
            "feedback_id": entry.feedback_id,
            "timestamp": entry.timestamp
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/stats")
async def get_advisor_stats():
    """
    Get advisor performance statistics
    
    Returns:
        Statistics about advisor recommendations and accuracy
        
    Example:
        GET /api/v1/advisor/stats
    """
    # Mock statistics for demonstration
    return {
        "total_recommendations": 1247,
        "accuracy_rate": 0.78,
        "avg_confidence": 0.73,
        "recommendations_by_level": {
            "strong_buy": 156,
            "buy": 423,
            "watch": 512,
            "skip": 124,
            "avoid": 32
        },
        "user_satisfaction": {
            "helpful": 892,
            "not_helpful": 143,
            "accurate": 756,
            "inaccurate": 98
        },
        "avg_processing_time_ms": 45,
        "last_updated": datetime.utcnow()
    }


@router.get("/explanation")
async def get_explanation():
    """
    Get explanation of how the advisor works
    
    Returns:
        Detailed explanation of AI logic and sense modules
        
    Example:
        GET /api/v1/advisor/explanation
    """
    return {
        "advisor_version": "1.0.0",
        "senses": [
            {
                "name": "PatternSense",
                "weight": 0.30,
                "description": "Analyzes historical patterns for similar items",
                "factors": [
                    "Win rate for similar items",
                    "Profitability rate",
                    "Price trends",
                    "Valuation alignment"
                ]
            },
            {
                "name": "MarketSense",
                "weight": 0.25,
                "description": "Analyzes current market conditions and competition",
                "factors": [
                    "Competition level (number of bidders)",
                    "Bidder aggressiveness",
                    "Time remaining",
                    "Category demand trends"
                ]
            },
            {
                "name": "BehaviorSense",
                "weight": 0.20,
                "description": "Learns from your bidding patterns and preferences",
                "factors": [
                    "Category familiarity",
                    "Success rate in category",
                    "Price range comfort",
                    "Budget fit"
                ]
            },
            {
                "name": "RiskSense",
                "weight": 0.25,
                "description": "Assesses potential risks and downsides",
                "factors": [
                    "Seller trustworthiness",
                    "Authenticity confidence",
                    "Price volatility",
                    "Item condition"
                ]
            }
        ],
        "recommendation_levels": {
            "strong_buy": "Excellent opportunity with high confidence",
            "buy": "Good opportunity, recommended to bid",
            "watch": "Interesting but wait for better timing",
            "skip": "Not recommended at current conditions",
            "avoid": "High risk, do not bid"
        },
        "risk_levels": {
            "low": "Minimal risk, safe to bid",
            "medium": "Some risk, proceed with caution",
            "high": "Significant risk, consider carefully",
            "very_high": "Extreme risk, avoid unless necessary"
        }
    }


@router.get("/feedback/summary")
async def get_feedback_summary(days: int = 30):
    """
    Get feedback summary statistics
    
    Args:
        days: Number of days to include (default: 30)
        
    Returns:
        Feedback summary with accuracy and helpfulness metrics
        
    Example:
        GET /api/v1/advisor/feedback/summary?days=30
    """
    try:
        from backend.services.feedback_collector import FeedbackCollector
        from datetime import timedelta
        
        collector = FeedbackCollector()
        await collector.initialize()
        
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        summary = await collector.get_summary(start_date, end_date)
        
        return summary.to_dict()
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get feedback summary: {str(e)}"
        )


@router.get("/learning/progress")
async def get_learning_progress():
    """
    Get learning progress and weight adjustments
    
    Returns:
        Learning progress metrics and current weights
        
    Example:
        GET /api/v1/advisor/learning/progress
    """
    try:
        from backend.services.feedback_collector import FeedbackCollector
        from backend.services.feedback_learner import FeedbackLearner
        
        collector = FeedbackCollector()
        await collector.initialize()
        
        learner = FeedbackLearner(collector)
        await learner.initialize()
        
        progress = await learner.get_learning_progress()
        
        return progress
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get learning progress: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for advisor service
    
    Returns:
        Service health status
    """
    return {
        "status": "healthy",
        "service": "advisor",
        "version": "1.0.0",
        "timestamp": datetime.utcnow()
    }
