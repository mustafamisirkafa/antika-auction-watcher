"""Enhanced valuation estimator using real marketplace APIs."""
import statistics
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from backend.services.marketplace.adapter_factory import adapter_factory
from backend.services.marketplace.base_adapter import MarketplaceAdapter


class RealValuationEstimator:
    """
    Enhanced valuation estimator using real marketplace data.
    
    Features:
    - Integration with real APIs (eBay, Etsy, Sahibinden)
    - Category-specific valuation logic
    - Source reliability scoring
    - Historical accuracy tracking
    - Outlier detection
    """

    def __init__(self):
        # Source reliability scores (0.0 to 1.0)
        # Based on data quality and completeness
        self.source_weights = {
            'ebay': 1.0,      # Most reliable (sold items data)
            'etsy': 0.85,     # Good for handmade/vintage
            'sahibinden': 0.7  # Local market, less standardized
        }
        
        # Category-specific adjustment factors
        self.category_factors = {
            'antiques': {
                'premium': 1.2,      # Antiques often worth more than listings
                'volatility': 0.3     # High price variance
            },
            'jewelry': {
                'premium': 1.15,
                'volatility': 0.25
            },
            'collectibles': {
                'premium': 1.1,
                'volatility': 0.35
            },
            'art': {
                'premium': 1.3,
                'volatility': 0.4
            },
            'furniture': {
                'premium': 0.9,
                'volatility': 0.2
            },
            'books': {
                'premium': 0.85,
                'volatility': 0.15
            },
            'default': {
                'premium': 1.0,
                'volatility': 0.25
            }
        }
        
        # Learning parameters
        self.safety_margin = 0.15
        self.historical_accuracy: Dict[str, float] = {}

    async def estimate_value(
        self,
        item_title: str,
        category: str,
        max_comparables: int = 20
    ) -> Tuple[float, float, float, List[Dict]]:
        """
        Estimate item value using real marketplace data.
        
        Args:
            item_title: Item title/description
            category: Item category
            max_comparables: Maximum comparables to fetch per source
            
        Returns:
            Tuple of (estimated_value, target_buy_price, confidence_score, comparables)
        """
        # Initialize adapter factory
        await adapter_factory.initialize()
        
        # Get only healthy adapters
        adapters = await adapter_factory.get_healthy_adapters()
        
        if not adapters:
            # Fallback to all adapters if no healthy ones
            adapters = await adapter_factory.get_all_adapters()
        
        all_comparables = []
        
        # Fetch data from each adapter
        for adapter in adapters:
            try:
                comparables = await adapter.search_comparables(
                    item_title,
                    category,
                    max_results=max_comparables
                )
                
                # Add source weight to each comparable
                for comp in comparables:
                    comp['weight'] = self.source_weights.get(
                        adapter.get_source_name(),
                        0.5
                    )
                
                all_comparables.extend(comparables)
                
            except Exception as e:
                # Log error but continue with other sources
                continue
        
        if not all_comparables:
            return 0.0, 0.0, 0.0, []
        
        # Calculate estimated value with category-specific logic
        estimated_value = self._calculate_estimated_value_v2(
            all_comparables,
            category
        )
        
        # Calculate enhanced confidence score
        confidence_score = self._calculate_confidence_v2(
            all_comparables,
            category
        )
        
        # Calculate target buy price with dynamic margin
        target_buy_price = self._calculate_target_price_v2(
            estimated_value,
            confidence_score,
            category
        )
        
        return (
            round(estimated_value, 2),
            round(target_buy_price, 2),
            round(confidence_score, 3),
            all_comparables
        )

    def _calculate_estimated_value_v2(
        self,
        comparables: List[Dict],
        category: str
    ) -> float:
        """
        Calculate estimated value with enhanced logic.
        
        Uses:
        - Weighted average based on source reliability
        - Category-specific adjustments
        - Outlier removal
        - Sold item prioritization
        """
        if not comparables:
            return 0.0
        
        # Extract prices
        prices = [comp['price'] for comp in comparables if comp['price'] > 0]
        
        if not prices:
            return 0.0
        
        # Remove outliers using IQR method
        prices_clean = self._remove_outliers(prices)
        
        if not prices_clean:
            prices_clean = prices  # Use all if outlier removal left nothing
        
        # Calculate weighted average
        weighted_sum = 0.0
        total_weight = 0.0
        
        for comp in comparables:
            if comp['price'] <= 0:
                continue
            
            if comp['price'] not in prices_clean:
                continue  # Skip outliers
            
            # Base weight from source
            weight = comp.get('weight', 0.5)
            
            # Increase weight for sold items (eBay)
            if comp.get('sold', False):
                weight *= 1.5
            
            # Increase weight for items with high engagement (Etsy)
            if comp.get('reviews', 0) > 50:
                weight *= 1.2
            
            # Recent items get higher weight (Sahibinden)
            if 'date_posted' in comp:
                # Could parse date and adjust weight
                pass
            
            weighted_sum += comp['price'] * weight
            total_weight += weight
        
        if total_weight == 0:
            base_estimate = statistics.median(prices_clean)
        else:
            base_estimate = weighted_sum / total_weight
        
        # Apply category-specific premium
        category_info = self.category_factors.get(
            category.lower(),
            self.category_factors['default']
        )
        
        estimated_value = base_estimate * category_info['premium']
        
        return estimated_value

    def _calculate_confidence_v2(
        self,
        comparables: List[Dict],
        category: str
    ) -> float:
        """
        Calculate enhanced confidence score.
        
        Factors:
        - Number of comparables
        - Price consistency
        - Source diversity
        - Data quality metrics
        - Category volatility
        """
        if not comparables:
            return 0.0
        
        prices = [comp['price'] for comp in comparables if comp['price'] > 0]
        
        if not prices:
            return 0.0
        
        # Factor 1: Quantity score (more comparables = better)
        count_score = min(len(comparables) / 15.0, 1.0)
        
        # Factor 2: Price consistency
        if len(prices) > 1:
            mean_price = statistics.mean(prices)
            std_dev = statistics.stdev(prices)
            cv = std_dev / mean_price if mean_price > 0 else 1.0
            
            # Adjust for category volatility
            category_info = self.category_factors.get(
                category.lower(),
                self.category_factors['default']
            )
            expected_cv = category_info['volatility']
            
            # Lower CV relative to expected = higher consistency
            consistency_score = max(1.0 - (cv / expected_cv), 0.0)
        else:
            consistency_score = 0.5
        
        # Factor 3: Source diversity
        sources = set(comp.get('source', 'unknown') for comp in comparables)
        diversity_score = min(len(sources) / 3.0, 1.0)
        
        # Factor 4: Data quality (sold items, reviews, etc.)
        quality_scores = []
        
        for comp in comparables:
            quality = 0.5  # Base quality
            
            # eBay: sold items are high quality
            if comp.get('sold', False):
                quality = 1.0
            
            # Etsy: high review count indicates reliability
            if comp.get('reviews', 0) > 20:
                quality = max(quality, 0.8)
            
            # Sahibinden: recent posts are better
            if 'date_posted' in comp:
                quality = max(quality, 0.6)
            
            quality_scores.append(quality)
        
        data_quality_score = statistics.mean(quality_scores) if quality_scores else 0.5
        
        # Weighted confidence calculation
        confidence = (
            count_score * 0.3 +
            consistency_score * 0.3 +
            diversity_score * 0.2 +
            data_quality_score * 0.2
        )
        
        return min(confidence, 1.0)

    def _calculate_target_price_v2(
        self,
        estimated_value: float,
        confidence_score: float,
        category: str
    ) -> float:
        """
        Calculate target buy price with dynamic margin.
        
        Margin adjusts based on:
        - Confidence score
        - Category volatility
        - Historical accuracy
        """
        # Base safety margin
        margin = self.safety_margin
        
        # Adjust for confidence (lower confidence = higher margin)
        confidence_adjustment = (1.0 - confidence_score) * 0.1
        margin += confidence_adjustment
        
        # Adjust for category volatility
        category_info = self.category_factors.get(
            category.lower(),
            self.category_factors['default']
        )
        volatility_adjustment = category_info['volatility'] * 0.2
        margin += volatility_adjustment
        
        # Adjust based on historical accuracy for this category
        if category in self.historical_accuracy:
            accuracy = self.historical_accuracy[category]
            # If we're usually accurate, reduce margin
            if accuracy > 0.8:
                margin -= 0.03
            # If we're usually off, increase margin
            elif accuracy < 0.6:
                margin += 0.05
        
        # Cap margin
        margin = max(0.05, min(margin, 0.40))
        
        target_price = estimated_value * (1.0 - margin)
        return target_price

    def _remove_outliers(self, prices: List[float]) -> List[float]:
        """Remove outliers using IQR method."""
        if len(prices) < 4:
            return prices
        
        sorted_prices = sorted(prices)
        q1_idx = len(sorted_prices) // 4
        q3_idx = (3 * len(sorted_prices)) // 4
        
        q1 = sorted_prices[q1_idx]
        q3 = sorted_prices[q3_idx]
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        return [p for p in prices if lower_bound <= p <= upper_bound]

    def update_category_accuracy(self, category: str, accuracy: float):
        """Update historical accuracy for a category."""
        self.historical_accuracy[category] = accuracy

    def update_learning_parameters(
        self,
        actual_resale_price: float,
        estimated_value: float,
        target_buy_price: float,
        category: str
    ):
        """Update learning parameters based on outcome."""
        if target_buy_price <= 0:
            return
        
        # Calculate actual margin
        actual_margin = (actual_resale_price - target_buy_price) / target_buy_price
        
        # Update safety margin
        if actual_margin > 0.5:
            # Too conservative
            self.safety_margin = max(self.safety_margin - 0.01, 0.05)
        elif actual_margin < 0:
            # Lost money
            self.safety_margin = min(self.safety_margin + 0.02, 0.40)
        
        # Update category accuracy
        error = abs(estimated_value - actual_resale_price) / actual_resale_price
        accuracy = 1.0 - min(error, 1.0)
        
        if category in self.historical_accuracy:
            # Moving average
            old_accuracy = self.historical_accuracy[category]
            self.historical_accuracy[category] = (old_accuracy * 0.7 + accuracy * 0.3)
        else:
            self.historical_accuracy[category] = accuracy
