"""Bid outcome tracking for learning and analytics."""
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from sqlmodel import Session, select, func
from backend.db.analytics_models import BidOutcome, CategoryMetrics
from backend.db.models import Bid, Item


class OutcomeTracker:
    """
    Track bid outcomes and calculate profitability metrics.
    
    Provides data for:
    - Profitability analysis
    - Valuation accuracy tracking
    - Learning loop optimization
    - Category-wise performance
    """

    def __init__(self, session: Session):
        self.session = session

    async def record_bid_outcome(
        self,
        bid_id: int,
        won_auction: bool,
        actual_resale_price: Optional[float] = None
    ) -> BidOutcome:
        """
        Record the outcome of a bid.
        
        Args:
            bid_id: Bid ID
            won_auction: Whether auction was won
            actual_resale_price: Actual resale price (if resold)
            
        Returns:
            Created BidOutcome record
        """
        # Get bid details
        bid = self.session.get(Bid, bid_id)
        if not bid:
            raise ValueError(f"Bid {bid_id} not found")
        
        # Get item details
        item = self.session.get(Item, bid.item_id)
        if not item:
            raise ValueError(f"Item {bid.item_id} not found")
        
        # Calculate profitability metrics
        gross_profit = None
        profit_margin = None
        roi = None
        valuation_accuracy = None
        margin_effectiveness = None
        
        if won_auction and actual_resale_price:
            # Calculate profit
            gross_profit = actual_resale_price - bid.bid_amount
            profit_margin = gross_profit / actual_resale_price if actual_resale_price > 0 else 0
            roi = gross_profit / bid.bid_amount if bid.bid_amount > 0 else 0
            
            # Calculate valuation accuracy
            if item.estimated_value and item.estimated_value > 0:
                error = abs(item.estimated_value - actual_resale_price) / actual_resale_price
                valuation_accuracy = 1.0 - min(error, 1.0)
            
            # Calculate margin effectiveness
            if item.target_buy_price and item.target_buy_price > 0:
                expected_profit = actual_resale_price - item.target_buy_price
                margin_effectiveness = expected_profit / actual_resale_price if actual_resale_price > 0 else 0
        
        # Create outcome record
        outcome = BidOutcome(
            bid_id=bid_id,
            item_id=bid.item_id,
            user_id=bid.user_id,
            estimated_value=item.estimated_value or 0,
            target_buy_price=item.target_buy_price or 0,
            actual_bid_amount=bid.bid_amount,
            confidence_score=item.confidence_score or 0,
            won_auction=won_auction,
            actual_resale_price=actual_resale_price,
            resale_date=datetime.utcnow() if actual_resale_price else None,
            gross_profit=gross_profit,
            profit_margin=profit_margin,
            roi=roi,
            valuation_accuracy=valuation_accuracy,
            margin_effectiveness=margin_effectiveness,
            category=item.category
        )
        
        self.session.add(outcome)
        self.session.commit()
        self.session.refresh(outcome)
        
        # Update category metrics
        await self._update_category_metrics(item.category)
        
        return outcome

    async def get_outcome_by_bid(self, bid_id: int) -> Optional[BidOutcome]:
        """Get outcome for a specific bid."""
        statement = select(BidOutcome).where(BidOutcome.bid_id == bid_id)
        return self.session.exec(statement).first()

    async def get_category_performance(self, category: str) -> Dict:
        """
        Get performance metrics for a category.
        
        Args:
            category: Item category
            
        Returns:
            Dictionary with performance metrics
        """
        statement = select(BidOutcome).where(BidOutcome.category == category)
        outcomes = self.session.exec(statement).all()
        
        if not outcomes:
            return {
                'category': category,
                'total_bids': 0,
                'won_bids': 0,
                'win_rate': 0.0,
                'average_profit': 0.0,
                'average_roi': 0.0,
                'valuation_accuracy': 0.0
            }
        
        # Calculate metrics
        total_bids = len(outcomes)
        won_bids = sum(1 for o in outcomes if o.won_auction)
        
        profitable_outcomes = [o for o in outcomes if o.gross_profit is not None]
        total_profit = sum(o.gross_profit for o in profitable_outcomes)
        avg_profit = total_profit / len(profitable_outcomes) if profitable_outcomes else 0
        
        roi_outcomes = [o for o in outcomes if o.roi is not None]
        avg_roi = sum(o.roi for o in roi_outcomes) / len(roi_outcomes) if roi_outcomes else 0
        
        accuracy_outcomes = [o for o in outcomes if o.valuation_accuracy is not None]
        avg_accuracy = sum(o.valuation_accuracy for o in accuracy_outcomes) / len(accuracy_outcomes) if accuracy_outcomes else 0
        
        return {
            'category': category,
            'total_bids': total_bids,
            'won_bids': won_bids,
            'win_rate': won_bids / total_bids if total_bids > 0 else 0,
            'total_profit': total_profit,
            'average_profit': avg_profit,
            'average_roi': avg_roi,
            'valuation_accuracy': avg_accuracy,
            'sample_size': len(profitable_outcomes)
        }

    async def get_user_performance(self, user_id: int) -> Dict:
        """Get performance metrics for a user."""
        statement = select(BidOutcome).where(BidOutcome.user_id == user_id)
        outcomes = self.session.exec(statement).all()
        
        if not outcomes:
            return {
                'user_id': user_id,
                'total_bids': 0,
                'won_bids': 0,
                'total_profit': 0.0,
                'average_roi': 0.0
            }
        
        total_bids = len(outcomes)
        won_bids = sum(1 for o in outcomes if o.won_auction)
        
        profitable = [o for o in outcomes if o.gross_profit is not None]
        total_profit = sum(o.gross_profit for o in profitable)
        
        roi_outcomes = [o for o in outcomes if o.roi is not None]
        avg_roi = sum(o.roi for o in roi_outcomes) / len(roi_outcomes) if roi_outcomes else 0
        
        return {
            'user_id': user_id,
            'total_bids': total_bids,
            'won_bids': won_bids,
            'win_rate': won_bids / total_bids if total_bids > 0 else 0,
            'total_profit': total_profit,
            'average_roi': avg_roi
        }

    async def get_time_series_metrics(
        self,
        days: int = 30,
        category: Optional[str] = None
    ) -> List[Dict]:
        """Get time-series performance metrics."""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        statement = select(BidOutcome).where(BidOutcome.created_at >= start_date)
        
        if category:
            statement = statement.where(BidOutcome.category == category)
        
        outcomes = self.session.exec(statement).all()
        
        # Group by date
        daily_metrics = {}
        for outcome in outcomes:
            date_key = outcome.created_at.date()
            
            if date_key not in daily_metrics:
                daily_metrics[date_key] = {
                    'date': date_key.isoformat(),
                    'bids': 0,
                    'won': 0,
                    'profit': 0.0,
                    'accuracy': []
                }
            
            daily_metrics[date_key]['bids'] += 1
            if outcome.won_auction:
                daily_metrics[date_key]['won'] += 1
            if outcome.gross_profit:
                daily_metrics[date_key]['profit'] += outcome.gross_profit
            if outcome.valuation_accuracy:
                daily_metrics[date_key]['accuracy'].append(outcome.valuation_accuracy)
        
        # Calculate averages
        result = []
        for date_key in sorted(daily_metrics.keys()):
            metrics = daily_metrics[date_key]
            avg_accuracy = sum(metrics['accuracy']) / len(metrics['accuracy']) if metrics['accuracy'] else 0
            
            result.append({
                'date': metrics['date'],
                'total_bids': metrics['bids'],
                'won_bids': metrics['won'],
                'win_rate': metrics['won'] / metrics['bids'] if metrics['bids'] > 0 else 0,
                'total_profit': metrics['profit'],
                'average_accuracy': avg_accuracy
            })
        
        return result

    async def _update_category_metrics(self, category: str):
        """Update aggregated category metrics."""
        # Get or create category metrics
        statement = select(CategoryMetrics).where(CategoryMetrics.category == category)
        cat_metrics = self.session.exec(statement).first()
        
        if not cat_metrics:
            cat_metrics = CategoryMetrics(category=category)
            self.session.add(cat_metrics)
        
        # Get performance data
        performance = await self.get_category_performance(category)
        
        # Update metrics
        cat_metrics.total_bids = performance['total_bids']
        cat_metrics.won_bids = performance['won_bids']
        cat_metrics.win_rate = performance['win_rate']
        cat_metrics.total_profit = performance['total_profit']
        cat_metrics.average_profit = performance['average_profit']
        cat_metrics.average_roi = performance['average_roi']
        cat_metrics.average_valuation_accuracy = performance['valuation_accuracy']
        cat_metrics.sample_size = performance['sample_size']
        cat_metrics.last_updated = datetime.utcnow()
        
        self.session.commit()

    async def export_outcomes_csv(
        self,
        category: Optional[str] = None,
        start_date: Optional[datetime] = None
    ) -> str:
        """Export outcomes to CSV format."""
        statement = select(BidOutcome)
        
        if category:
            statement = statement.where(BidOutcome.category == category)
        
        if start_date:
            statement = statement.where(BidOutcome.created_at >= start_date)
        
        outcomes = self.session.exec(statement).all()
        
        # Build CSV
        csv_lines = [
            "bid_id,item_id,category,estimated_value,target_price,bid_amount,"
            "confidence,won,resale_price,profit,roi,accuracy,created_at"
        ]
        
        for outcome in outcomes:
            csv_lines.append(
                f"{outcome.bid_id},{outcome.item_id},{outcome.category},"
                f"{outcome.estimated_value},{outcome.target_buy_price},"
                f"{outcome.actual_bid_amount},{outcome.confidence_score},"
                f"{outcome.won_auction},{outcome.actual_resale_price or ''},"
                f"{outcome.gross_profit or ''},{outcome.roi or ''},"
                f"{outcome.valuation_accuracy or ''},{outcome.created_at.isoformat()}"
            )
        
        return "\n".join(csv_lines)
