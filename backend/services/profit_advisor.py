"""
Profit Advisor Service for Antika Auction Watcher.
AI-powered profit estimation and bid recommendation.
"""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from sqlmodel import Session, select
import logging

from backend.models.profit import AuctionItem, MarketReference, ProfitEstimate
from backend.services.market_fetcher import market_fetcher

logger = logging.getLogger(__name__)


class ProfitAdvisorService:
    """
    Analyzes auction items and provides profit estimates.
    """
    
    def __init__(self, db_session: Session):
        """
        Initialize profit advisor service.
        
        Args:
            db_session: Database session
        """
        self.db = db_session
        self.market_fetcher = market_fetcher
        
        # Configuration
        self.roi_buffer = 0.15  # Target 15% ROI buffer
        self.confidence_weights = {
            "liquidity": 0.35,
            "volatility": 0.30,
            "sample_size": 0.20,
            "visual_match": 0.15  # Future: image similarity
        }
    
    async def analyze_item(
        self,
        auction_item: AuctionItem,
        force_refresh: bool = False
    ) -> ProfitEstimate:
        """
        Analyze a single auction item and generate profit estimate.
        
        Args:
            auction_item: Auction item to analyze
            force_refresh: Force refresh market data
            
        Returns:
            ProfitEstimate object
        """
        logger.info(f"Analyzing item {auction_item.id}: {auction_item.title}")
        
        # Check for existing recent estimate
        if not force_refresh:
            existing = self._get_recent_estimate(auction_item.id)
            if existing:
                logger.info(f"Using cached estimate for item {auction_item.id}")
                return existing
        
        # Fetch market data from all sources
        market_data_list = await self.market_fetcher.fetch_all_sources(
            auction_item.title,
            auction_item.category
        )
        
        if not market_data_list:
            logger.warning(f"No market data found for item {auction_item.id}")
            return self._create_low_confidence_estimate(auction_item)
        
        # Save market references
        await self._save_market_references(auction_item.id, market_data_list)
        
        # Aggregate market data
        aggregated = self.market_fetcher.aggregate_market_data(market_data_list)
        
        # Calculate profit metrics
        profit_metrics = self._calculate_profit_metrics(
            auction_item.starting_price,
            aggregated
        )
        
        # Calculate confidence score
        confidence = self._calculate_confidence(
            aggregated,
            len(market_data_list)
        )
        
        # Determine risk level
        risk_level = self._determine_risk_level(
            profit_metrics["profit_margin"],
            confidence,
            aggregated["avg_volatility_stability"]
        )
        
        # Create profit estimate
        estimate = ProfitEstimate(
            auction_item_id=auction_item.id,
            estimated_value=aggregated["avg_market_price"],
            recommended_max_bid=profit_metrics["recommended_max_bid"],
            profit_margin=profit_metrics["profit_margin"],
            profit_amount=profit_metrics["profit_amount"],
            confidence=confidence,
            risk_level=risk_level,
            market_volatility=1.0 - aggregated["avg_volatility_stability"],
            liquidity_avg=aggregated["avg_liquidity"],
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        # Save to database
        self.db.add(estimate)
        self.db.commit()
        self.db.refresh(estimate)
        
        logger.info(
            f"Created profit estimate for item {auction_item.id}: "
            f"recommend ${estimate.recommended_max_bid:.2f}, "
            f"profit margin {estimate.profit_margin:.1%}, "
            f"confidence {estimate.confidence:.2f}"
        )
        
        return estimate
    
    def _calculate_profit_metrics(
        self,
        starting_price: float,
        aggregated: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Calculate profit-related metrics.
        
        Args:
            starting_price: Item starting price
            aggregated: Aggregated market data
            
        Returns:
            Dictionary with profit metrics
        """
        market_avg = aggregated["avg_market_price"]
        
        # Recommended max bid (target ROI buffer)
        recommended_max_bid = market_avg * (1.0 - self.roi_buffer)
        
        # Ensure bid is above starting price (makes sense to bid)
        if recommended_max_bid < starting_price:
            recommended_max_bid = starting_price * 1.05  # 5% above starting
        
        # Profit margin calculation
        profit_amount = market_avg - recommended_max_bid
        profit_margin = (
            profit_amount / recommended_max_bid
            if recommended_max_bid > 0
            else 0.0
        )
        
        return {
            "recommended_max_bid": round(recommended_max_bid, 2),
            "profit_amount": round(profit_amount, 2),
            "profit_margin": round(profit_margin, 4)
        }
    
    def _calculate_confidence(
        self,
        aggregated: Dict[str, float],
        source_count: int
    ) -> float:
        """
        Calculate confidence score based on market data quality.
        
        Args:
            aggregated: Aggregated market data
            source_count: Number of sources
            
        Returns:
            Confidence score (0-1)
        """
        # Liquidity component
        liquidity_score = aggregated["avg_liquidity"]
        
        # Volatility component (stability is good)
        volatility_score = aggregated["avg_volatility_stability"]
        
        # Sample size component (normalize to 0-1)
        sample_score = min(aggregated["total_samples"] / 100, 1.0)
        
        # Visual match component (placeholder - future: image similarity)
        visual_score = 0.7  # Default moderate match
        
        # Weighted confidence
        confidence = (
            liquidity_score * self.confidence_weights["liquidity"] +
            volatility_score * self.confidence_weights["volatility"] +
            sample_score * self.confidence_weights["sample_size"] +
            visual_score * self.confidence_weights["visual_match"]
        )
        
        # Boost confidence if multiple sources agree
        if source_count >= 3:
            confidence = min(confidence * 1.1, 1.0)
        
        return round(confidence, 3)
    
    def _determine_risk_level(
        self,
        profit_margin: float,
        confidence: float,
        volatility_stability: float
    ) -> str:
        """
        Determine risk level based on metrics.
        
        Args:
            profit_margin: Expected profit margin
            confidence: Confidence score
            volatility_stability: Market stability
            
        Returns:
            Risk level (low, medium, high)
        """
        # High confidence + good margin + stable = low risk
        if confidence >= 0.8 and profit_margin >= 0.15 and volatility_stability >= 0.7:
            return "low"
        
        # Low confidence or negative margin = high risk
        if confidence < 0.6 or profit_margin < 0.05:
            return "high"
        
        # Everything else is medium
        return "medium"
    
    def _create_low_confidence_estimate(
        self,
        auction_item: AuctionItem
    ) -> ProfitEstimate:
        """
        Create a low-confidence estimate when no market data available.
        
        Args:
            auction_item: Auction item
            
        Returns:
            Low-confidence ProfitEstimate
        """
        # Conservative estimate: 10% above starting price
        estimated_value = auction_item.starting_price * 1.1
        recommended_max_bid = auction_item.starting_price * 1.05
        
        estimate = ProfitEstimate(
            auction_item_id=auction_item.id,
            estimated_value=estimated_value,
            recommended_max_bid=recommended_max_bid,
            profit_margin=0.05,
            profit_amount=estimated_value - recommended_max_bid,
            confidence=0.3,
            risk_level="high",
            market_volatility=0.8,
            liquidity_avg=0.3,
            expires_at=datetime.utcnow() + timedelta(hours=12)
        )
        
        self.db.add(estimate)
        self.db.commit()
        self.db.refresh(estimate)
        
        return estimate
    
    def _get_recent_estimate(
        self,
        auction_item_id: int,
        max_age_hours: int = 24
    ) -> Optional[ProfitEstimate]:
        """
        Get recent profit estimate if exists.
        
        Args:
            auction_item_id: Auction item ID
            max_age_hours: Maximum age in hours
            
        Returns:
            ProfitEstimate or None
        """
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        statement = select(ProfitEstimate).where(
            ProfitEstimate.auction_item_id == auction_item_id,
            ProfitEstimate.created_at >= cutoff
        ).order_by(ProfitEstimate.created_at.desc())
        
        return self.db.exec(statement).first()
    
    async def _save_market_references(
        self,
        auction_item_id: int,
        market_data_list: List[Dict[str, any]]
    ):
        """
        Save market references to database.
        
        Args:
            auction_item_id: Auction item ID
            market_data_list: List of market data
        """
        for data in market_data_list:
            reference = MarketReference(
                auction_item_id=auction_item_id,
                source=data["source"],
                avg_price=data["market_avg"],
                sample_size=data["sample_size"],
                liquidity_score=data["liquidity_score"],
                last_checked=datetime.utcnow()
            )
            self.db.add(reference)
        
        self.db.commit()
    
    async def analyze_team_items(
        self,
        team_id: int,
        upcoming_only: bool = True
    ) -> List[ProfitEstimate]:
        """
        Analyze all auction items for a team.
        
        Args:
            team_id: Team ID
            upcoming_only: Only analyze items with future auction dates
            
        Returns:
            List of ProfitEstimate objects
        """
        # Get auction items
        statement = select(AuctionItem).where(AuctionItem.team_id == team_id)
        
        if upcoming_only:
            statement = statement.where(
                AuctionItem.auction_date > datetime.utcnow()
            )
        
        items = self.db.exec(statement).all()
        
        logger.info(f"Analyzing {len(items)} items for team {team_id}")
        
        # Analyze items concurrently (in batches to avoid overload)
        estimates = []
        batch_size = 5
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_estimates = await asyncio.gather(*[
                self.analyze_item(item)
                for item in batch
            ])
            estimates.extend(batch_estimates)
        
        logger.info(f"Completed analysis of {len(estimates)} items for team {team_id}")
        
        return estimates
    
    async def run_all_teams(self):
        """
        Run profit analysis for all teams (nightly job).
        """
        # Get all teams with upcoming auction items
        statement = select(AuctionItem.team_id).distinct()
        team_ids = self.db.exec(statement).all()
        
        logger.info(f"Running profit analysis for {len(team_ids)} teams")
        
        for team_id in team_ids:
            try:
                await self.analyze_team_items(team_id)
            except Exception as e:
                logger.error(f"Failed to analyze items for team {team_id}: {e}", exc_info=True)
        
        logger.info("Completed nightly profit analysis for all teams")
    
    def get_team_estimates(
        self,
        team_id: int,
        min_confidence: Optional[float] = None,
        max_risk: Optional[str] = None
    ) -> List[ProfitEstimate]:
        """
        Get profit estimates for a team with optional filtering.
        
        Args:
            team_id: Team ID
            min_confidence: Minimum confidence threshold
            max_risk: Maximum risk level (low, medium, high)
            
        Returns:
            List of ProfitEstimate objects
        """
        # Join with auction items to filter by team
        statement = (
            select(ProfitEstimate)
            .join(AuctionItem)
            .where(AuctionItem.team_id == team_id)
            .order_by(ProfitEstimate.created_at.desc())
        )
        
        estimates = self.db.exec(statement).all()
        
        # Apply filters
        if min_confidence is not None:
            estimates = [e for e in estimates if e.confidence >= min_confidence]
        
        if max_risk:
            risk_order = {"low": 0, "medium": 1, "high": 2}
            max_risk_level = risk_order.get(max_risk, 2)
            estimates = [
                e for e in estimates
                if risk_order.get(e.risk_level, 2) <= max_risk_level
            ]
        
        return list(estimates)
