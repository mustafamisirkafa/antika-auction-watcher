"""Valuation estimation engine."""
import statistics
from typing import List, Dict, Tuple
from backend.services.valuation.adapters import (
    MockEbayAdapter,
    MockEtsyAdapter,
    MockSahibindenAdapter
)


class ValuationEstimator:
    """Valuation estimator that aggregates data from multiple sources."""

    def __init__(self):
        self.adapters = [
            MockEbayAdapter(),
            MockEtsyAdapter(),
            MockSahibindenAdapter()
        ]
        # Learning parameters (will be updated based on outcomes)
        self.safety_margin = 0.15  # 15% safety margin by default

    async def estimate_value(
        self,
        item_title: str,
        category: str
    ) -> Tuple[float, float, float, List[Dict]]:
        """
        Estimate item value by aggregating data from multiple sources.
        
        Returns:
            Tuple of (estimated_value, target_buy_price, confidence_score, all_comparables)
        """
        all_comparables = []
        
        # Gather data from all adapters
        for adapter in self.adapters:
            comparables = await adapter.search_comparables(item_title, category)
            
            for comp in comparables:
                comp["source"] = adapter.get_source_name()
                all_comparables.append(comp)
        
        if not all_comparables:
            return 0.0, 0.0, 0.0, []
        
        # Calculate estimated value
        estimated_value = self._calculate_estimated_value(all_comparables)
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence(all_comparables)
        
        # Calculate target buy price with safety margin
        target_buy_price = self._calculate_target_price(
            estimated_value,
            confidence_score
        )
        
        return (
            round(estimated_value, 2),
            round(target_buy_price, 2),
            round(confidence_score, 2),
            all_comparables
        )

    def _calculate_estimated_value(self, comparables: List[Dict]) -> float:
        """Calculate estimated value using weighted average."""
        prices = [comp["price"] for comp in comparables]
        
        if not prices:
            return 0.0
        
        # Use median as base estimate (more robust to outliers)
        median_price = statistics.median(prices)
        
        # Weight sold items higher (for sources that track this)
        weighted_prices = []
        for comp in comparables:
            price = comp["price"]
            weight = 1.5 if comp.get("sold", False) else 1.0
            weighted_prices.extend([price] * int(weight))
        
        weighted_mean = statistics.mean(weighted_prices) if weighted_prices else median_price
        
        # Combine median and weighted mean
        estimated_value = (median_price * 0.6) + (weighted_mean * 0.4)
        
        return estimated_value

    def _calculate_confidence(self, comparables: List[Dict]) -> float:
        """Calculate confidence score based on data quality."""
        if not comparables:
            return 0.0
        
        prices = [comp["price"] for comp in comparables]
        
        # Factor 1: Number of comparables (more = better)
        count_score = min(len(comparables) / 10.0, 1.0)
        
        # Factor 2: Price consistency (lower std dev = better)
        if len(prices) > 1:
            mean_price = statistics.mean(prices)
            std_dev = statistics.stdev(prices)
            cv = std_dev / mean_price if mean_price > 0 else 1.0
            consistency_score = max(1.0 - cv, 0.0)
        else:
            consistency_score = 0.5
        
        # Factor 3: Source diversity
        sources = set(comp["source"] for comp in comparables)
        diversity_score = len(sources) / len(self.adapters)
        
        # Weighted confidence score
        confidence = (
            count_score * 0.4 +
            consistency_score * 0.4 +
            diversity_score * 0.2
        )
        
        return min(confidence, 1.0)

    def _calculate_target_price(
        self,
        estimated_value: float,
        confidence_score: float
    ) -> float:
        """Calculate target buy price with safety margin."""
        # Adjust safety margin based on confidence
        # Lower confidence = higher safety margin
        adjusted_margin = self.safety_margin + (1.0 - confidence_score) * 0.1
        adjusted_margin = min(adjusted_margin, 0.35)  # Cap at 35%
        
        target_price = estimated_value * (1.0 - adjusted_margin)
        return target_price

    def update_learning_parameters(
        self,
        actual_resale_price: float,
        estimated_value: float,
        target_buy_price: float
    ):
        """Update learning parameters based on outcome."""
        # Calculate actual profit margin
        if target_buy_price > 0:
            actual_margin = (actual_resale_price - target_buy_price) / target_buy_price
            
            # If we're consistently over-conservative, reduce safety margin
            if actual_margin > 0.5:
                self.safety_margin = max(self.safety_margin - 0.01, 0.05)
            # If we're losing money, increase safety margin
            elif actual_margin < 0:
                self.safety_margin = min(self.safety_margin + 0.02, 0.40)
