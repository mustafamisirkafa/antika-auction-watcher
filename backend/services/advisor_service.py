"""
AI Auction Advisor Service - Multi-sense recommendation engine
Provides intelligent bidding suggestions based on pattern, market, behavior, and risk analysis
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import statistics
import asyncio


class RecommendationLevel(str, Enum):
    """Recommendation strength levels"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    WATCH = "watch"
    SKIP = "skip"
    AVOID = "avoid"


class RiskLevel(str, Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class SenseScore:
    """Individual sense analysis score"""
    score: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    reasoning: str
    factors: Dict[str, float]


@dataclass
class AdvisorRecommendation:
    """Complete advisor recommendation"""
    item_id: str
    recommendation: RecommendationLevel
    confidence: float  # 0.0 to 1.0
    suggested_max_bid: Optional[float]
    reasoning: List[str]
    risk_level: RiskLevel
    
    # Individual sense scores
    pattern_sense: SenseScore
    market_sense: SenseScore
    behavior_sense: SenseScore
    risk_sense: SenseScore
    
    # Metadata
    timestamp: datetime
    expires_at: datetime


class PatternSense:
    """
    Analyzes historical patterns for similar items
    Uses past auction outcomes to predict success probability
    """
    
    @staticmethod
    async def analyze(
        item_data: Dict,
        historical_data: List[Dict],
        valuation_data: Optional[Dict] = None
    ) -> SenseScore:
        """
        Analyze historical patterns for similar items
        
        Args:
            item_data: Current item details (category, price, features)
            historical_data: Past auction results for similar items
            valuation_data: AI valuation if available
            
        Returns:
            SenseScore with pattern analysis
        """
        factors = {}
        
        # Filter similar items by category
        category = item_data.get("category", "")
        similar_items = [
            h for h in historical_data
            if h.get("category") == category
        ]
        
        if not similar_items:
            return SenseScore(
                score=0.5,
                confidence=0.3,
                reasoning="Insufficient historical data for pattern analysis",
                factors={"data_availability": 0.3}
            )
        
        # Calculate win rate for similar items
        won_items = [h for h in similar_items if h.get("won", False)]
        win_rate = len(won_items) / len(similar_items)
        factors["win_rate"] = win_rate
        
        # Calculate average profitability
        profitable_items = [
            h for h in won_items
            if h.get("profitability", 0) > 0
        ]
        profitability_rate = len(profitable_items) / len(won_items) if won_items else 0
        factors["profitability_rate"] = profitability_rate
        
        # Analyze price trends
        if len(similar_items) >= 3:
            recent_prices = [h.get("final_price", 0) for h in similar_items[-10:]]
            avg_price = statistics.mean(recent_prices)
            current_price = item_data.get("current_price", 0)
            
            if avg_price > 0:
                price_ratio = current_price / avg_price
                factors["price_ratio"] = price_ratio
                
                # Lower current price vs average is better
                if price_ratio < 0.8:
                    factors["price_advantage"] = 1.0
                elif price_ratio < 1.0:
                    factors["price_advantage"] = 0.7
                else:
                    factors["price_advantage"] = 0.3
        
        # Check valuation alignment
        if valuation_data:
            estimated_value = valuation_data.get("estimated_value", 0)
            current_price = item_data.get("current_price", 0)
            valuation_confidence = valuation_data.get("confidence", 0.5)
            
            if estimated_value > 0:
                value_ratio = current_price / estimated_value
                factors["valuation_alignment"] = valuation_confidence
                
                if value_ratio < 0.7:
                    factors["undervalued"] = 1.0
                elif value_ratio < 0.9:
                    factors["undervalued"] = 0.7
                else:
                    factors["undervalued"] = 0.3
        
        # Calculate overall score
        score = statistics.mean([
            win_rate,
            profitability_rate,
            factors.get("price_advantage", 0.5),
            factors.get("undervalued", 0.5)
        ])
        
        # Calculate confidence based on data availability
        confidence = min(1.0, len(similar_items) / 20) * 0.7 + 0.3
        
        reasoning = f"Analyzed {len(similar_items)} similar {category} items. "
        reasoning += f"Historical win rate: {win_rate:.0%}, "
        reasoning += f"profitability rate: {profitability_rate:.0%}."
        
        return SenseScore(
            score=score,
            confidence=confidence,
            reasoning=reasoning,
            factors=factors
        )


class MarketSense:
    """
    Analyzes current market conditions and competition
    Considers active bidders, time remaining, and market trends
    """
    
    @staticmethod
    async def analyze(
        item_data: Dict,
        market_data: Dict,
        active_bidders: List[Dict]
    ) -> SenseScore:
        """
        Analyze current market conditions
        
        Args:
            item_data: Current item details
            market_data: Overall market statistics
            active_bidders: List of active bidders on this item
            
        Returns:
            SenseScore with market analysis
        """
        factors = {}
        
        # Analyze competition level
        bidder_count = len(active_bidders)
        factors["bidder_count"] = bidder_count
        
        if bidder_count == 0:
            factors["competition"] = 1.0  # No competition
        elif bidder_count <= 2:
            factors["competition"] = 0.8
        elif bidder_count <= 5:
            factors["competition"] = 0.5
        else:
            factors["competition"] = 0.2
        
        # Analyze bidder aggressiveness
        if active_bidders:
            avg_bids = statistics.mean([
                b.get("bid_count", 0) for b in active_bidders
            ])
            factors["bidder_aggressiveness"] = min(1.0, avg_bids / 10)
            
            # Check for power bidders
            power_bidders = [
                b for b in active_bidders
                if b.get("win_rate", 0) > 0.7
            ]
            factors["power_bidder_present"] = 1.0 if power_bidders else 0.0
        
        # Time-based factors
        time_remaining = item_data.get("time_remaining_seconds", 0)
        factors["time_remaining"] = time_remaining
        
        if time_remaining < 300:  # Less than 5 minutes
            factors["urgency"] = 0.9
            factors["sniping_opportunity"] = 0.8
        elif time_remaining < 3600:  # Less than 1 hour
            factors["urgency"] = 0.5
            factors["sniping_opportunity"] = 0.4
        else:
            factors["urgency"] = 0.2
            factors["sniping_opportunity"] = 0.1
        
        # Market trend analysis
        category = item_data.get("category", "")
        category_stats = market_data.get("categories", {}).get(category, {})
        
        if category_stats:
            demand_trend = category_stats.get("demand_trend", 0)  # -1 to 1
            factors["category_demand"] = (demand_trend + 1) / 2  # Normalize to 0-1
            
            avg_competition = category_stats.get("avg_bidders", 3)
            if bidder_count < avg_competition:
                factors["below_avg_competition"] = 0.8
            else:
                factors["below_avg_competition"] = 0.3
        
        # Calculate overall score
        competition_score = factors.get("competition", 0.5)
        timing_score = (1 - factors.get("urgency", 0.5)) * 0.5 + 0.5
        market_trend_score = factors.get("category_demand", 0.5)
        
        score = statistics.mean([
            competition_score,
            timing_score,
            market_trend_score
        ])
        
        # Adjust for power bidders
        if factors.get("power_bidder_present", 0) > 0:
            score *= 0.7  # Reduce score if power bidders present
        
        confidence = 0.8 if category_stats else 0.5
        
        reasoning = f"Competition level: {bidder_count} bidders. "
        if time_remaining < 3600:
            reasoning += f"Auction ending soon ({time_remaining // 60} min remaining). "
        if factors.get("power_bidder_present"):
            reasoning += "Warning: Experienced bidders present. "
        
        return SenseScore(
            score=score,
            confidence=confidence,
            reasoning=reasoning,
            factors=factors
        )


class BehaviorSense:
    """
    Analyzes user's past behavior and preferences
    Learns from user's bidding patterns and feedback
    """
    
    @staticmethod
    async def analyze(
        item_data: Dict,
        user_history: List[Dict],
        user_preferences: Dict
    ) -> SenseScore:
        """
        Analyze based on user behavior and preferences
        
        Args:
            item_data: Current item details
            user_history: User's past auction activities
            user_preferences: User's stated preferences
            
        Returns:
            SenseScore with behavior analysis
        """
        factors = {}
        
        category = item_data.get("category", "")
        
        # Analyze category preference
        category_activities = [
            h for h in user_history
            if h.get("category") == category
        ]
        
        if category_activities:
            factors["category_familiarity"] = min(1.0, len(category_activities) / 10)
            
            # Calculate success rate in this category
            won_in_category = [
                h for h in category_activities
                if h.get("won", False)
            ]
            category_win_rate = len(won_in_category) / len(category_activities)
            factors["category_success_rate"] = category_win_rate
        else:
            factors["category_familiarity"] = 0.0
            factors["category_success_rate"] = 0.5
        
        # Analyze price range preference
        if user_history:
            user_bid_amounts = [h.get("bid_amount", 0) for h in user_history]
            avg_user_bid = statistics.mean(user_bid_amounts)
            current_price = item_data.get("current_price", 0)
            
            if current_price <= avg_user_bid * 1.2:
                factors["price_comfort"] = 0.9
            elif current_price <= avg_user_bid * 2:
                factors["price_comfort"] = 0.6
            else:
                factors["price_comfort"] = 0.3
        
        # Check explicit preferences
        preferred_categories = user_preferences.get("preferred_categories", [])
        if category in preferred_categories:
            factors["explicit_preference"] = 1.0
        else:
            factors["explicit_preference"] = 0.5
        
        max_budget = user_preferences.get("max_budget_per_item", float("inf"))
        current_price = item_data.get("current_price", 0)
        
        if current_price <= max_budget * 0.5:
            factors["budget_fit"] = 1.0
        elif current_price <= max_budget:
            factors["budget_fit"] = 0.7
        else:
            factors["budget_fit"] = 0.1
        
        # Analyze feedback history
        feedback_history = [
            h for h in user_history
            if "feedback" in h
        ]
        
        if feedback_history:
            positive_feedback = [
                f for f in feedback_history
                if f.get("feedback") in ["helpful", "accurate"]
            ]
            feedback_accuracy = len(positive_feedback) / len(feedback_history)
            factors["advisor_trust"] = feedback_accuracy
        else:
            factors["advisor_trust"] = 0.7  # Default trust
        
        # Calculate overall score
        score = statistics.mean([
            factors.get("category_success_rate", 0.5),
            factors.get("price_comfort", 0.5),
            factors.get("explicit_preference", 0.5),
            factors.get("budget_fit", 0.5)
        ])
        
        confidence = min(1.0, len(user_history) / 30) * 0.5 + 0.5
        
        reasoning = f"Based on your activity: "
        if factors.get("category_familiarity", 0) > 0.5:
            reasoning += f"{category} is familiar to you. "
        if factors.get("price_comfort", 0) > 0.7:
            reasoning += "Price within your typical range. "
        if factors.get("budget_fit", 0) < 0.5:
            reasoning += "Warning: Above your stated budget. "
        
        return SenseScore(
            score=score,
            confidence=confidence,
            reasoning=reasoning,
            factors=factors
        )


class RiskSense:
    """
    Assesses potential risks and downsides
    Evaluates authenticity, seller reliability, and market volatility
    """
    
    @staticmethod
    async def analyze(
        item_data: Dict,
        seller_data: Dict,
        valuation_data: Optional[Dict] = None
    ) -> SenseScore:
        """
        Analyze risk factors
        
        Args:
            item_data: Current item details
            seller_data: Seller reputation and history
            valuation_data: AI valuation if available
            
        Returns:
            SenseScore with risk analysis (higher score = lower risk)
        """
        factors = {}
        risk_flags = []
        
        # Seller reputation analysis
        seller_rating = seller_data.get("rating", 0)
        seller_sales = seller_data.get("total_sales", 0)
        seller_disputes = seller_data.get("disputes", 0)
        
        factors["seller_rating"] = seller_rating
        
        if seller_rating >= 4.5 and seller_sales > 50:
            factors["seller_trustworthiness"] = 0.9
        elif seller_rating >= 4.0 and seller_sales > 20:
            factors["seller_trustworthiness"] = 0.7
        elif seller_rating >= 3.5:
            factors["seller_trustworthiness"] = 0.5
        else:
            factors["seller_trustworthiness"] = 0.2
            risk_flags.append("Low seller rating")
        
        if seller_disputes > seller_sales * 0.1:
            factors["dispute_risk"] = 0.3
            risk_flags.append("High dispute rate")
        else:
            factors["dispute_risk"] = 0.9
        
        # Authenticity risk (based on valuation confidence)
        if valuation_data:
            val_confidence = valuation_data.get("confidence", 0.5)
            factors["authenticity_confidence"] = val_confidence
            
            if val_confidence < 0.5:
                risk_flags.append("Low authenticity confidence")
        else:
            factors["authenticity_confidence"] = 0.5
        
        # Price volatility risk
        current_price = item_data.get("current_price", 0)
        estimated_value = valuation_data.get("estimated_value", current_price) if valuation_data else current_price
        
        if estimated_value > 0:
            price_deviation = abs(current_price - estimated_value) / estimated_value
            factors["price_volatility"] = price_deviation
            
            if price_deviation > 0.5:
                risk_flags.append("High price volatility")
                factors["volatility_risk"] = 0.3
            elif price_deviation > 0.3:
                factors["volatility_risk"] = 0.6
            else:
                factors["volatility_risk"] = 0.9
        else:
            factors["volatility_risk"] = 0.5
        
        # Item condition risk
        condition = item_data.get("condition", "").lower()
        if "new" in condition or "mint" in condition:
            factors["condition_risk"] = 0.9
        elif "good" in condition or "very good" in condition:
            factors["condition_risk"] = 0.7
        elif "fair" in condition or "used" in condition:
            factors["condition_risk"] = 0.5
            risk_flags.append("Item condition fair/used")
        else:
            factors["condition_risk"] = 0.3
            risk_flags.append("Unknown or poor condition")
        
        # Return policy risk
        has_return_policy = seller_data.get("has_return_policy", False)
        factors["return_policy"] = 1.0 if has_return_policy else 0.3
        
        if not has_return_policy:
            risk_flags.append("No return policy")
        
        # Calculate overall risk score (higher = safer)
        score = statistics.mean([
            factors["seller_trustworthiness"],
            factors["dispute_risk"],
            factors.get("authenticity_confidence", 0.5),
            factors["volatility_risk"],
            factors["condition_risk"],
            factors["return_policy"]
        ])
        
        confidence = 0.8
        
        reasoning = "Risk assessment: "
        if score > 0.7:
            reasoning += "Low risk. "
        elif score > 0.5:
            reasoning += "Moderate risk. "
        else:
            reasoning += "High risk. "
        
        if risk_flags:
            reasoning += "Concerns: " + ", ".join(risk_flags) + ". "
        else:
            reasoning += "No major concerns identified. "
        
        return SenseScore(
            score=score,
            confidence=confidence,
            reasoning=reasoning,
            factors=factors
        )


class AdvisorService:
    """
    Main AI Advisor Service
    Coordinates all sense modules to provide comprehensive recommendations
    """
    
    def __init__(self):
        self.pattern_sense = PatternSense()
        self.market_sense = MarketSense()
        self.behavior_sense = BehaviorSense()
        self.risk_sense = RiskSense()
    
    async def get_recommendation(
        self,
        item_id: str,
        item_data: Dict,
        historical_data: List[Dict],
        market_data: Dict,
        active_bidders: List[Dict],
        user_history: List[Dict],
        user_preferences: Dict,
        seller_data: Dict,
        valuation_data: Optional[Dict] = None
    ) -> AdvisorRecommendation:
        """
        Generate comprehensive recommendation for an item
        
        Returns:
            AdvisorRecommendation with all sense scores and final recommendation
        """
        # Run all sense analyses in parallel
        pattern_score, market_score, behavior_score, risk_score = await asyncio.gather(
            self.pattern_sense.analyze(item_data, historical_data, valuation_data),
            self.market_sense.analyze(item_data, market_data, active_bidders),
            self.behavior_sense.analyze(item_data, user_history, user_preferences),
            self.risk_sense.analyze(item_data, seller_data, valuation_data)
        )
        
        # Calculate weighted overall score
        weights = {
            "pattern": 0.30,
            "market": 0.25,
            "behavior": 0.20,
            "risk": 0.25
        }
        
        overall_score = (
            pattern_score.score * weights["pattern"] +
            market_score.score * weights["market"] +
            behavior_score.score * weights["behavior"] +
            risk_score.score * weights["risk"]
        )
        
        # Calculate overall confidence
        overall_confidence = statistics.mean([
            pattern_score.confidence,
            market_score.confidence,
            behavior_score.confidence,
            risk_score.confidence
        ])
        
        # Determine recommendation level
        recommendation = self._determine_recommendation(
            overall_score,
            risk_score.score,
            pattern_score.score
        )
        
        # Determine risk level
        risk_level = self._determine_risk_level(risk_score.score, overall_score)
        
        # Calculate suggested max bid
        suggested_max_bid = self._calculate_max_bid(
            item_data,
            valuation_data,
            overall_score,
            risk_score.score
        )
        
        # Generate reasoning
        reasoning = self._generate_reasoning(
            recommendation,
            pattern_score,
            market_score,
            behavior_score,
            risk_score,
            overall_score
        )
        
        return AdvisorRecommendation(
            item_id=item_id,
            recommendation=recommendation,
            confidence=overall_confidence,
            suggested_max_bid=suggested_max_bid,
            reasoning=reasoning,
            risk_level=risk_level,
            pattern_sense=pattern_score,
            market_sense=market_score,
            behavior_sense=behavior_score,
            risk_sense=risk_score,
            timestamp=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=30)
        )
    
    def _determine_recommendation(
        self,
        overall_score: float,
        risk_score: float,
        pattern_score: float
    ) -> RecommendationLevel:
        """Determine recommendation level based on scores"""
        # Don't recommend if risk is too high
        if risk_score < 0.4:
            return RecommendationLevel.AVOID
        
        # Strong buy: high overall score, good risk, good pattern
        if overall_score > 0.75 and risk_score > 0.6 and pattern_score > 0.7:
            return RecommendationLevel.STRONG_BUY
        
        # Buy: good overall score and acceptable risk
        if overall_score > 0.6 and risk_score > 0.5:
            return RecommendationLevel.BUY
        
        # Watch: moderate score or needs more data
        if overall_score > 0.45:
            return RecommendationLevel.WATCH
        
        # Skip: low score
        if overall_score > 0.3:
            return RecommendationLevel.SKIP
        
        return RecommendationLevel.AVOID
    
    def _determine_risk_level(self, risk_score: float, overall_score: float) -> RiskLevel:
        """Determine risk level"""
        if risk_score > 0.7 and overall_score > 0.6:
            return RiskLevel.LOW
        elif risk_score > 0.5:
            return RiskLevel.MEDIUM
        elif risk_score > 0.3:
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH
    
    def _calculate_max_bid(
        self,
        item_data: Dict,
        valuation_data: Optional[Dict],
        overall_score: float,
        risk_score: float
    ) -> Optional[float]:
        """Calculate suggested maximum bid"""
        if not valuation_data:
            return None
        
        estimated_value = valuation_data.get("estimated_value", 0)
        if estimated_value <= 0:
            return None
        
        # Base max bid on valuation and scores
        safety_margin = 0.85  # Start conservative
        
        # Adjust based on overall score
        if overall_score > 0.75:
            safety_margin = 0.95
        elif overall_score > 0.6:
            safety_margin = 0.90
        
        # Reduce further based on risk
        if risk_score < 0.5:
            safety_margin *= 0.85
        elif risk_score < 0.7:
            safety_margin *= 0.95
        
        max_bid = estimated_value * safety_margin
        
        # Round to reasonable amount
        if max_bid < 100:
            max_bid = round(max_bid, 2)
        elif max_bid < 1000:
            max_bid = round(max_bid / 5) * 5
        else:
            max_bid = round(max_bid / 10) * 10
        
        return max_bid
    
    def _generate_reasoning(
        self,
        recommendation: RecommendationLevel,
        pattern_score: SenseScore,
        market_score: SenseScore,
        behavior_score: SenseScore,
        risk_score: SenseScore,
        overall_score: float
    ) -> List[str]:
        """Generate human-readable reasoning"""
        reasoning = []
        
        # Main recommendation
        if recommendation == RecommendationLevel.STRONG_BUY:
            reasoning.append("?? Strong Buy: Excellent opportunity with high confidence")
        elif recommendation == RecommendationLevel.BUY:
            reasoning.append("? Buy: Good opportunity, recommended to bid")
        elif recommendation == RecommendationLevel.WATCH:
            reasoning.append("?? Watch: Interesting but wait for better timing")
        elif recommendation == RecommendationLevel.SKIP:
            reasoning.append("?? Skip: Not recommended at current conditions")
        else:
            reasoning.append("? Avoid: High risk, do not bid")
        
        # Add key insights from each sense
        if pattern_score.score > 0.7:
            reasoning.append(f"?? Pattern: {pattern_score.reasoning}")
        elif pattern_score.score < 0.4:
            reasoning.append(f"?? Pattern: {pattern_score.reasoning}")
        
        if market_score.score > 0.7:
            reasoning.append(f"?? Market: {market_score.reasoning}")
        elif market_score.score < 0.4:
            reasoning.append(f"?? Market: {market_score.reasoning}")
        
        if behavior_score.score > 0.7:
            reasoning.append(f"?? Behavior: {behavior_score.reasoning}")
        elif behavior_score.score < 0.4:
            reasoning.append(f"?? Behavior: {behavior_score.reasoning}")
        
        if risk_score.score > 0.7:
            reasoning.append(f"? Risk: {risk_score.reasoning}")
        else:
            reasoning.append(f"?? Risk: {risk_score.reasoning}")
        
        return reasoning
    
    async def analyze_batch(
        self,
        items: List[Dict],
        shared_context: Dict
    ) -> List[AdvisorRecommendation]:
        """
        Analyze multiple items in batch
        
        Args:
            items: List of items to analyze
            shared_context: Shared data (user history, preferences, market data)
            
        Returns:
            List of recommendations
        """
        tasks = [
            self.get_recommendation(
                item_id=item["id"],
                item_data=item["data"],
                historical_data=shared_context.get("historical_data", []),
                market_data=shared_context.get("market_data", {}),
                active_bidders=item.get("active_bidders", []),
                user_history=shared_context.get("user_history", []),
                user_preferences=shared_context.get("user_preferences", {}),
                seller_data=item.get("seller_data", {}),
                valuation_data=item.get("valuation_data")
            )
            for item in items
        ]
        
        return await asyncio.gather(*tasks)
