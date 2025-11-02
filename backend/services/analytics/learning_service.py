"""Learning service for margin optimization and confidence tuning."""
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlmodel import Session, select
from backend.db.analytics_models import BidOutcome, CategoryMetrics
from backend.services.valuation.real_estimator import RealValuationEstimator


class LearningService:
    """
    Machine learning service for continuous improvement.
    
    Features:
    - Category-wise margin optimization
    - Confidence score calibration
    - Safety margin adjustment
    - Historical performance analysis
    """

    def __init__(self, session: Session):
        self.session = session
        self.estimator = RealValuationEstimator()
        
        # Learning parameters
        self.min_sample_size = 10  # Minimum outcomes needed for learning
        self.learning_rate = 0.1   # How quickly to adjust parameters

    async def train_category_model(self, category: str) -> Dict:
        """
        Train/update model for a specific category.
        
        Args:
            category: Item category
            
        Returns:
            Dictionary with updated parameters
        """
        # Get outcomes for this category
        statement = select(BidOutcome).where(
            BidOutcome.category == category,
            BidOutcome.won_auction == True,
            BidOutcome.actual_resale_price.isnot(None)
        )
        outcomes = self.session.exec(statement).all()
        
        if len(outcomes) < self.min_sample_size:
            return {
                'category': category,
                'status': 'insufficient_data',
                'sample_size': len(outcomes),
                'required': self.min_sample_size
            }
        
        # Calculate optimal safety margin
        optimal_margin = await self._calculate_optimal_margin(outcomes)
        
        # Calculate optimal confidence threshold
        optimal_confidence = await self._calculate_optimal_confidence(outcomes)
        
        # Calculate source weights for this category
        source_weights = await self._calculate_source_weights(outcomes, category)
        
        # Update category metrics
        await self._update_category_learning_params(
            category,
            optimal_margin,
            optimal_confidence
        )
        
        # Update estimator parameters
        self.estimator.update_category_accuracy(
            category,
            await self._calculate_category_accuracy(outcomes)
        )
        
        return {
            'category': category,
            'status': 'trained',
            'sample_size': len(outcomes),
            'optimal_margin': optimal_margin,
            'optimal_confidence': optimal_confidence,
            'source_weights': source_weights
        }

    async def _calculate_optimal_margin(self, outcomes: List[BidOutcome]) -> float:
        """
        Calculate optimal safety margin based on historical outcomes.
        
        Strategy:
        - Maximize profit while minimizing losses
        - Balance between being too conservative and too aggressive
        """
        # Calculate margins that would have been optimal for each outcome
        optimal_margins = []
        
        for outcome in outcomes:
            if outcome.actual_resale_price and outcome.target_buy_price > 0:
                # Optimal margin would have been:
                # (resale_price - target_price) / resale_price
                ideal_margin = (outcome.actual_resale_price - outcome.target_buy_price) / outcome.actual_resale_price
                
                # Only consider positive margins (profitable)
                if ideal_margin > 0:
                    optimal_margins.append(ideal_margin)
        
        if not optimal_margins:
            return 0.15  # Default margin
        
        # Use median of optimal margins (robust to outliers)
        import statistics
        median_margin = statistics.median(optimal_margins)
        
        # Add safety buffer (10% of median)
        safe_margin = median_margin * 1.1
        
        # Clamp to reasonable range
        return max(0.05, min(safe_margin, 0.40))

    async def _calculate_optimal_confidence(self, outcomes: List[BidOutcome]) -> float:
        """Calculate optimal confidence threshold."""
        # Analyze profitability by confidence level
        confidence_buckets = {
            'high': {'wins': 0, 'total': 0, 'profit': 0.0},
            'medium': {'wins': 0, 'total': 0, 'profit': 0.0},
            'low': {'wins': 0, 'total': 0, 'profit': 0.0}
        }
        
        for outcome in outcomes:
            # Categorize by confidence
            if outcome.confidence_score >= 0.7:
                bucket = 'high'
            elif outcome.confidence_score >= 0.5:
                bucket = 'medium'
            else:
                bucket = 'low'
            
            confidence_buckets[bucket]['total'] += 1
            
            if outcome.gross_profit and outcome.gross_profit > 0:
                confidence_buckets[bucket]['wins'] += 1
                confidence_buckets[bucket]['profit'] += outcome.gross_profit
        
        # Find threshold with best win rate
        best_threshold = 0.6  # Default
        best_win_rate = 0.0
        
        for threshold, label in [(0.7, 'high'), (0.5, 'medium')]:
            bucket = confidence_buckets[label]
            if bucket['total'] > 0:
                win_rate = bucket['wins'] / bucket['total']
                if win_rate > best_win_rate:
                    best_win_rate = win_rate
                    best_threshold = threshold
        
        return best_threshold

    async def _calculate_source_weights(
        self,
        outcomes: List[BidOutcome],
        category: str
    ) -> Dict[str, float]:
        """Calculate category-specific source reliability weights."""
        # This would analyze which sources gave most accurate valuations
        # for this specific category
        
        # For now, return default weights
        # In production, would analyze valuation_accuracy by source
        return {
            'ebay': 1.0,
            'etsy': 0.85,
            'sahibinden': 0.7
        }

    async def _calculate_category_accuracy(self, outcomes: List[BidOutcome]) -> float:
        """Calculate overall accuracy for category."""
        accuracies = [o.valuation_accuracy for o in outcomes if o.valuation_accuracy]
        
        if not accuracies:
            return 0.5
        
        import statistics
        return statistics.mean(accuracies)

    async def _update_category_learning_params(
        self,
        category: str,
        optimal_margin: float,
        optimal_confidence: float
    ):
        """Update category metrics with learning parameters."""
        statement = select(CategoryMetrics).where(CategoryMetrics.category == category)
        cat_metrics = self.session.exec(statement).first()
        
        if not cat_metrics:
            cat_metrics = CategoryMetrics(category=category)
            self.session.add(cat_metrics)
        
        # Update with learning rate (gradual adjustment)
        current_margin = cat_metrics.recommended_safety_margin
        cat_metrics.recommended_safety_margin = (
            current_margin * (1 - self.learning_rate) +
            optimal_margin * self.learning_rate
        )
        
        current_conf = cat_metrics.confidence_threshold
        cat_metrics.confidence_threshold = (
            current_conf * (1 - self.learning_rate) +
            optimal_confidence * self.learning_rate
        )
        
        self.session.commit()

    async def retrain_all_categories(self) -> Dict[str, Dict]:
        """Retrain models for all categories with sufficient data."""
        # Get all categories with outcomes
        statement = select(BidOutcome.category).distinct()
        categories = [row[0] for row in self.session.exec(statement).all()]
        
        results = {}
        for category in categories:
            results[category] = await self.train_category_model(category)
        
        return results

    async def get_learning_recommendations(self, category: str) -> Dict:
        """
        Get AI recommendations for a category.
        
        Args:
            category: Item category
            
        Returns:
            Dictionary with recommendations
        """
        statement = select(CategoryMetrics).where(CategoryMetrics.category == category)
        metrics = self.session.exec(statement).first()
        
        if not metrics or metrics.sample_size < self.min_sample_size:
            return {
                'category': category,
                'has_recommendations': False,
                'reason': 'insufficient_data',
                'sample_size': metrics.sample_size if metrics else 0
            }
        
        recommendations = {
            'category': category,
            'has_recommendations': True,
            'recommended_safety_margin': metrics.recommended_safety_margin,
            'recommended_confidence_threshold': metrics.confidence_threshold,
            'expected_win_rate': metrics.win_rate,
            'expected_roi': metrics.average_roi,
            'data_quality': self._assess_data_quality(metrics)
        }
        
        # Add specific recommendations
        if metrics.win_rate < 0.5:
            recommendations['warnings'] = ['Low win rate - consider increasing confidence threshold']
        
        if metrics.average_roi < 0.1:
            recommendations['warnings'] = recommendations.get('warnings', [])
            recommendations['warnings'].append('Low ROI - consider adjusting safety margin')
        
        return recommendations

    def _assess_data_quality(self, metrics: CategoryMetrics) -> str:
        """Assess quality of learning data."""
        if metrics.sample_size >= 100:
            return 'excellent'
        elif metrics.sample_size >= 50:
            return 'good'
        elif metrics.sample_size >= 20:
            return 'fair'
        else:
            return 'poor'

    async def schedule_retraining(self) -> Dict:
        """
        Schedule periodic retraining of all models.
        
        This should be called daily or weekly via a cron job.
        
        Returns:
            Summary of retraining results
        """
        results = await self.retrain_all_categories()
        
        summary = {
            'retrained_at': datetime.utcnow().isoformat(),
            'total_categories': len(results),
            'successful': sum(1 for r in results.values() if r['status'] == 'trained'),
            'insufficient_data': sum(1 for r in results.values() if r['status'] == 'insufficient_data'),
            'details': results
        }
        
        return summary

    async def get_model_performance_report(self) -> Dict:
        """Generate comprehensive performance report."""
        # Get all category metrics
        statement = select(CategoryMetrics)
        all_metrics = self.session.exec(statement).all()
        
        if not all_metrics:
            return {
                'status': 'no_data',
                'categories_tracked': 0
            }
        
        # Calculate aggregate stats
        total_bids = sum(m.total_bids for m in all_metrics)
        total_won = sum(m.won_bids for m in all_metrics)
        total_profit = sum(m.total_profit for m in all_metrics)
        
        avg_accuracy = sum(m.average_valuation_accuracy * m.sample_size for m in all_metrics) / sum(m.sample_size for m in all_metrics) if sum(m.sample_size for m in all_metrics) > 0 else 0
        
        # Find best and worst performing categories
        best_roi = max(all_metrics, key=lambda m: m.average_roi) if all_metrics else None
        worst_roi = min(all_metrics, key=lambda m: m.average_roi) if all_metrics else None
        
        return {
            'status': 'success',
            'categories_tracked': len(all_metrics),
            'aggregate_stats': {
                'total_bids': total_bids,
                'total_won': total_won,
                'overall_win_rate': total_won / total_bids if total_bids > 0 else 0,
                'total_profit': total_profit,
                'average_accuracy': avg_accuracy
            },
            'best_category': {
                'name': best_roi.category if best_roi else None,
                'roi': best_roi.average_roi if best_roi else 0
            },
            'worst_category': {
                'name': worst_roi.category if worst_roi else None,
                'roi': worst_roi.average_roi if worst_roi else 0
            }
        }
