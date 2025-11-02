"""
Tests for AI Advisor Service
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from backend.services.advisor_service import (
    AdvisorService,
    PatternSense,
    MarketSense,
    BehaviorSense,
    RiskSense,
    RecommendationLevel,
    RiskLevel,
    SenseScore
)


# ============================================================================
# PatternSense Tests
# ============================================================================

@pytest.mark.asyncio
async def test_pattern_sense_with_good_history():
    """Test pattern analysis with favorable historical data"""
    item_data = {
        "category": "ceramics",
        "current_price": 400,
    }
    
    historical_data = [
        {"category": "ceramics", "final_price": 500, "won": True, "profitability": 0.20},
        {"category": "ceramics", "final_price": 480, "won": True, "profitability": 0.15},
        {"category": "ceramics", "final_price": 520, "won": True, "profitability": 0.25},
    ]
    
    result = await PatternSense.analyze(item_data, historical_data)
    
    assert isinstance(result, SenseScore)
    assert 0 <= result.score <= 1
    assert 0 <= result.confidence <= 1
    assert "win_rate" in result.factors
    assert result.factors["win_rate"] == 1.0  # All wins


@pytest.mark.asyncio
async def test_pattern_sense_with_no_data():
    """Test pattern analysis with insufficient data"""
    item_data = {"category": "ceramics"}
    historical_data = []
    
    result = await PatternSense.analyze(item_data, historical_data)
    
    assert result.score == 0.5
    assert result.confidence == 0.3
    assert "Insufficient historical data" in result.reasoning


@pytest.mark.asyncio
async def test_pattern_sense_with_valuation():
    """Test pattern analysis with AI valuation data"""
    item_data = {
        "category": "ceramics",
        "current_price": 400,
    }
    
    historical_data = [
        {"category": "ceramics", "final_price": 500, "won": True, "profitability": 0.15},
    ]
    
    valuation_data = {
        "estimated_value": 600,
        "confidence": 0.85
    }
    
    result = await PatternSense.analyze(item_data, historical_data, valuation_data)
    
    assert "undervalued" in result.factors
    assert result.factors["undervalued"] == 1.0  # Highly undervalued


# ============================================================================
# MarketSense Tests
# ============================================================================

@pytest.mark.asyncio
async def test_market_sense_low_competition():
    """Test market analysis with low competition"""
    item_data = {"time_remaining_seconds": 3600}
    market_data = {"categories": {}}
    active_bidders = []  # No competition
    
    result = await MarketSense.analyze(item_data, market_data, active_bidders)
    
    assert result.factors["competition"] == 1.0
    assert result.factors["bidder_count"] == 0


@pytest.mark.asyncio
async def test_market_sense_high_competition():
    """Test market analysis with high competition"""
    item_data = {"time_remaining_seconds": 3600}
    market_data = {"categories": {}}
    active_bidders = [
        {"bid_count": 5, "win_rate": 0.8},
        {"bid_count": 3, "win_rate": 0.7},
        {"bid_count": 4, "win_rate": 0.75},
        {"bid_count": 6, "win_rate": 0.9},
        {"bid_count": 2, "win_rate": 0.6},
        {"bid_count": 3, "win_rate": 0.65},
    ]
    
    result = await MarketSense.analyze(item_data, market_data, active_bidders)
    
    assert result.factors["competition"] == 0.2  # High competition
    assert result.factors["bidder_count"] == 6


@pytest.mark.asyncio
async def test_market_sense_urgency():
    """Test market analysis with time urgency"""
    item_data = {"time_remaining_seconds": 250}  # Less than 5 minutes
    market_data = {"categories": {}}
    active_bidders = []
    
    result = await MarketSense.analyze(item_data, market_data, active_bidders)
    
    assert result.factors["urgency"] == 0.9
    assert result.factors["sniping_opportunity"] == 0.8


@pytest.mark.asyncio
async def test_market_sense_power_bidder():
    """Test detection of power bidders"""
    item_data = {"time_remaining_seconds": 3600}
    market_data = {"categories": {}}
    active_bidders = [
        {"bid_count": 10, "win_rate": 0.85},  # Power bidder
    ]
    
    result = await MarketSense.analyze(item_data, market_data, active_bidders)
    
    assert result.factors["power_bidder_present"] == 1.0
    assert "Experienced bidders present" in result.reasoning


# ============================================================================
# BehaviorSense Tests
# ============================================================================

@pytest.mark.asyncio
async def test_behavior_sense_familiar_category():
    """Test behavior analysis with familiar category"""
    item_data = {"category": "ceramics", "current_price": 400}
    
    user_history = [
        {"category": "ceramics", "bid_amount": 350, "won": True},
        {"category": "ceramics", "bid_amount": 420, "won": True},
        {"category": "ceramics", "bid_amount": 380, "won": False},
    ]
    
    user_preferences = {
        "preferred_categories": ["ceramics"],
        "max_budget_per_item": 1000
    }
    
    result = await BehaviorSense.analyze(item_data, user_history, user_preferences)
    
    assert result.factors["category_familiarity"] > 0
    assert result.factors["explicit_preference"] == 1.0
    assert result.factors["category_success_rate"] > 0.5


@pytest.mark.asyncio
async def test_behavior_sense_over_budget():
    """Test behavior analysis when item is over budget"""
    item_data = {"category": "ceramics", "current_price": 1500}
    user_history = []
    user_preferences = {"preferred_categories": [], "max_budget_per_item": 1000}
    
    result = await BehaviorSense.analyze(item_data, user_history, user_preferences)
    
    assert result.factors["budget_fit"] == 0.1
    assert "Above your stated budget" in result.reasoning


@pytest.mark.asyncio
async def test_behavior_sense_price_comfort():
    """Test price comfort zone analysis"""
    item_data = {"category": "ceramics", "current_price": 400}
    
    user_history = [
        {"category": "ceramics", "bid_amount": 350, "won": True},
        {"category": "antiques", "bid_amount": 420, "won": True},
        {"category": "ceramics", "bid_amount": 380, "won": False},
    ]
    
    user_preferences = {"preferred_categories": [], "max_budget_per_item": 1000}
    
    result = await BehaviorSense.analyze(item_data, user_history, user_preferences)
    
    assert "price_comfort" in result.factors
    assert result.factors["price_comfort"] > 0.5


# ============================================================================
# RiskSense Tests
# ============================================================================

@pytest.mark.asyncio
async def test_risk_sense_trusted_seller():
    """Test risk analysis with trusted seller"""
    item_data = {"condition": "very good"}
    
    seller_data = {
        "rating": 4.8,
        "total_sales": 200,
        "disputes": 2,
        "has_return_policy": True
    }
    
    result = await RiskSense.analyze(item_data, seller_data)
    
    assert result.factors["seller_trustworthiness"] == 0.9
    assert result.factors["dispute_risk"] == 0.9
    assert result.score > 0.7


@pytest.mark.asyncio
async def test_risk_sense_untrusted_seller():
    """Test risk analysis with untrusted seller"""
    item_data = {"condition": "fair"}
    
    seller_data = {
        "rating": 3.2,
        "total_sales": 10,
        "disputes": 3,
        "has_return_policy": False
    }
    
    result = await RiskSense.analyze(item_data, seller_data)
    
    assert result.factors["seller_trustworthiness"] < 0.5
    assert result.factors["return_policy"] == 0.3
    assert "Low seller rating" in str(result.factors) or "No return policy" in result.reasoning


@pytest.mark.asyncio
async def test_risk_sense_condition_analysis():
    """Test condition risk assessment"""
    item_data = {"condition": "mint"}
    seller_data = {"rating": 4.5, "total_sales": 100, "disputes": 1, "has_return_policy": True}
    
    result = await RiskSense.analyze(item_data, seller_data)
    
    assert result.factors["condition_risk"] == 0.9


# ============================================================================
# AdvisorService Tests
# ============================================================================

@pytest.fixture
def sample_data():
    """Sample data for advisor tests"""
    return {
        "item_id": "item123",
        "item_data": {
            "id": "item123",
            "category": "ceramics",
            "current_price": 450,
            "time_remaining_seconds": 1800,
            "condition": "very good"
        },
        "historical_data": [
            {"category": "ceramics", "final_price": 520, "won": True, "profitability": 0.15},
            {"category": "ceramics", "final_price": 480, "won": True, "profitability": 0.20},
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
        ],
        "user_history": [
            {"category": "ceramics", "bid_amount": 400, "won": True, "feedback": "helpful"},
        ],
        "user_preferences": {
            "preferred_categories": ["ceramics"],
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
            "confidence": 0.82
        }
    }


@pytest.mark.asyncio
async def test_advisor_service_recommendation(sample_data):
    """Test complete advisor recommendation"""
    advisor = AdvisorService()
    
    recommendation = await advisor.get_recommendation(**sample_data)
    
    assert recommendation.item_id == "item123"
    assert recommendation.recommendation in [
        RecommendationLevel.STRONG_BUY,
        RecommendationLevel.BUY,
        RecommendationLevel.WATCH,
        RecommendationLevel.SKIP,
        RecommendationLevel.AVOID
    ]
    assert 0 <= recommendation.confidence <= 1
    assert recommendation.risk_level in [
        RiskLevel.LOW,
        RiskLevel.MEDIUM,
        RiskLevel.HIGH,
        RiskLevel.VERY_HIGH
    ]
    assert len(recommendation.reasoning) > 0


@pytest.mark.asyncio
async def test_advisor_service_suggested_max_bid(sample_data):
    """Test suggested max bid calculation"""
    advisor = AdvisorService()
    
    recommendation = await advisor.get_recommendation(**sample_data)
    
    assert recommendation.suggested_max_bid is not None
    assert recommendation.suggested_max_bid > 0
    # Should be less than or equal to estimated value
    assert recommendation.suggested_max_bid <= sample_data["valuation_data"]["estimated_value"]


@pytest.mark.asyncio
async def test_advisor_service_strong_buy():
    """Test conditions for strong buy recommendation"""
    advisor = AdvisorService()
    
    # Create ideal conditions
    data = {
        "item_id": "item_ideal",
        "item_data": {
            "category": "ceramics",
            "current_price": 300,
            "time_remaining_seconds": 1800,
            "condition": "mint"
        },
        "historical_data": [
            {"category": "ceramics", "final_price": 500, "won": True, "profitability": 0.30},
            {"category": "ceramics", "final_price": 520, "won": True, "profitability": 0.35},
            {"category": "ceramics", "final_price": 480, "won": True, "profitability": 0.28},
        ],
        "market_data": {"categories": {"ceramics": {"demand_trend": 0.5, "avg_bidders": 2}}},
        "active_bidders": [],  # No competition
        "user_history": [
            {"category": "ceramics", "bid_amount": 350, "won": True, "feedback": "helpful"},
            {"category": "ceramics", "bid_amount": 320, "won": True, "feedback": "accurate"},
        ],
        "user_preferences": {
            "preferred_categories": ["ceramics"],
            "max_budget_per_item": 1000
        },
        "seller_data": {
            "rating": 4.9,
            "total_sales": 500,
            "disputes": 1,
            "has_return_policy": True
        },
        "valuation_data": {
            "estimated_value": 700,
            "confidence": 0.92
        }
    }
    
    recommendation = await advisor.get_recommendation(**data)
    
    # With ideal conditions, should get strong buy or buy
    assert recommendation.recommendation in [RecommendationLevel.STRONG_BUY, RecommendationLevel.BUY]
    assert recommendation.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]


@pytest.mark.asyncio
async def test_advisor_service_avoid():
    """Test conditions for avoid recommendation"""
    advisor = AdvisorService()
    
    # Create risky conditions
    data = {
        "item_id": "item_risky",
        "item_data": {
            "category": "ceramics",
            "current_price": 800,
            "time_remaining_seconds": 100,
            "condition": "poor"
        },
        "historical_data": [
            {"category": "ceramics", "final_price": 500, "won": False, "profitability": 0},
        ],
        "market_data": {"categories": {}},
        "active_bidders": [
            {"id": "bidder1", "bid_count": 10, "win_rate": 0.9},
            {"id": "bidder2", "bid_count": 8, "win_rate": 0.85},
            {"id": "bidder3", "bid_count": 12, "win_rate": 0.88},
        ],
        "user_history": [],
        "user_preferences": {
            "preferred_categories": [],
            "max_budget_per_item": 500
        },
        "seller_data": {
            "rating": 2.8,
            "total_sales": 5,
            "disputes": 3,
            "has_return_policy": False
        },
        "valuation_data": {
            "estimated_value": 400,
            "confidence": 0.35
        }
    }
    
    recommendation = await advisor.get_recommendation(**data)
    
    # With risky conditions, should avoid or skip
    assert recommendation.recommendation in [RecommendationLevel.AVOID, RecommendationLevel.SKIP]


@pytest.mark.asyncio
async def test_advisor_service_batch_analysis(sample_data):
    """Test batch analysis of multiple items"""
    advisor = AdvisorService()
    
    items = [
        {
            "id": f"item{i}",
            "data": sample_data["item_data"].copy(),
            "active_bidders": sample_data["active_bidders"],
            "seller_data": sample_data["seller_data"],
            "valuation_data": sample_data["valuation_data"]
        }
        for i in range(3)
    ]
    
    shared_context = {
        "historical_data": sample_data["historical_data"],
        "market_data": sample_data["market_data"],
        "user_history": sample_data["user_history"],
        "user_preferences": sample_data["user_preferences"]
    }
    
    recommendations = await advisor.analyze_batch(items, shared_context)
    
    assert len(recommendations) == 3
    for rec in recommendations:
        assert rec.recommendation is not None
        assert rec.confidence > 0


@pytest.mark.asyncio
async def test_advisor_sense_scores(sample_data):
    """Test all sense scores are present and valid"""
    advisor = AdvisorService()
    
    recommendation = await advisor.get_recommendation(**sample_data)
    
    # Check all sense scores exist
    assert recommendation.pattern_sense is not None
    assert recommendation.market_sense is not None
    assert recommendation.behavior_sense is not None
    assert recommendation.risk_sense is not None
    
    # Check all scores are in valid range
    for sense in [
        recommendation.pattern_sense,
        recommendation.market_sense,
        recommendation.behavior_sense,
        recommendation.risk_sense
    ]:
        assert 0 <= sense.score <= 1
        assert 0 <= sense.confidence <= 1
        assert len(sense.reasoning) > 0
        assert isinstance(sense.factors, dict)


@pytest.mark.asyncio
async def test_advisor_recommendation_expiry():
    """Test recommendation has expiry timestamp"""
    advisor = AdvisorService()
    
    data = {
        "item_id": "item_test",
        "item_data": {"category": "ceramics", "current_price": 400, "time_remaining_seconds": 1800},
        "historical_data": [],
        "market_data": {"categories": {}},
        "active_bidders": [],
        "user_history": [],
        "user_preferences": {"preferred_categories": [], "max_budget_per_item": 1000},
        "seller_data": {"rating": 4.5, "total_sales": 100, "disputes": 2, "has_return_policy": True},
        "valuation_data": None
    }
    
    recommendation = await advisor.get_recommendation(**data)
    
    assert recommendation.timestamp is not None
    assert recommendation.expires_at is not None
    assert recommendation.expires_at > recommendation.timestamp
    
    # Should expire in about 30 minutes
    time_diff = recommendation.expires_at - recommendation.timestamp
    assert timedelta(minutes=29) <= time_diff <= timedelta(minutes=31)
