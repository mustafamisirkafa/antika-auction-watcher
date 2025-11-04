"""
Sprint 6: Feature Engineering for ML Valuation Model

Builds feature vectors from auction item data with robust handling
of missing values, type errors, and edge cases.
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Feature defaults for missing values
FEATURE_DEFAULTS = {
    "internal_estimate": 0.0,
    "market_value": 0.0,
    "demand_score": 0.5,
    "trend_delta": 0.0,
    "seller_trust": 0.5,
    "category_id": 0,
    "condition_score": 0.5,
    "cache_age_sec": 3600.0,  # 1 hour default
    "cache_hit": 0,
    "time_of_day": 12,  # Noon
    "day_of_week": 3,   # Wednesday
    "listing_age_sec": 86400.0,  # 1 day default
}

# Feature ranges for validation
FEATURE_RANGES = {
    "internal_estimate": (0, 1e8),
    "market_value": (0, 1e8),
    "demand_score": (0, 1),
    "trend_delta": (-1, 1),
    "seller_trust": (0, 1),
    "category_id": (0, 100),
    "condition_score": (0, 1),
    "cache_age_sec": (0, 604800),  # Max 1 week
    "cache_hit": (0, 1),
    "time_of_day": (0, 23),
    "day_of_week": (0, 6),
    "listing_age_sec": (0, 2592000),  # Max 30 days
}


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float with fallback.
    
    Handles: None, NaN, inf, strings, errors
    """
    if value is None:
        return default
    
    try:
        result = float(value)
        
        # Check for NaN or infinity
        if result != result:  # NaN check
            return default
        if result == float('inf') or result == float('-inf'):
            return default
        
        return result
    except (ValueError, TypeError, OverflowError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely convert value to int with fallback.
    """
    if value is None:
        return default
    
    try:
        return int(value)
    except (ValueError, TypeError, OverflowError):
        return default


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to range [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def build_features(item: Dict[str, Any]) -> Dict[str, float]:
    """
    Build feature vector from auction item data.
    
    Args:
        item: Dictionary containing item data with fields:
            - internal_estimate: Phase 9 profit advisor estimate
            - market_value: Phase 11 fused market value
            - demand_score: Phase 11 demand metric
            - trend_delta: Phase 11 trend change
            - seller_trust: Phase 12 seller trust score
            - category_id: Item category identifier
            - condition_score: Item condition (0-1)
            - cache_age_sec: Age of cached data (Sprint 5)
            - cache_hit: Whether cache was hit (Sprint 5)
            - created_at: Listing creation timestamp
    
    Returns:
        Dictionary of feature name -> float value
        
    Example:
        >>> item = {
        ...     "internal_estimate": 1000,
        ...     "market_value": 1200,
        ...     "seller_trust": 0.85,
        ...     "category_id": 5
        ... }
        >>> features = build_features(item)
        >>> features["market_value"]
        1200.0
    """
    features = {}
    
    # Phase 9: Internal estimate
    features["internal_estimate"] = safe_float(
        item.get("internal_estimate"),
        FEATURE_DEFAULTS["internal_estimate"]
    )
    
    # Phase 11: Market data
    features["market_value"] = safe_float(
        item.get("market_value"),
        FEATURE_DEFAULTS["market_value"]
    )
    features["demand_score"] = safe_float(
        item.get("demand_score"),
        FEATURE_DEFAULTS["demand_score"]
    )
    features["trend_delta"] = safe_float(
        item.get("trend_delta"),
        FEATURE_DEFAULTS["trend_delta"]
    )
    
    # Phase 12: Seller trust
    features["seller_trust"] = safe_float(
        item.get("seller_trust"),
        FEATURE_DEFAULTS["seller_trust"]
    )
    
    # Item metadata
    features["category_id"] = safe_int(
        item.get("category_id"),
        FEATURE_DEFAULTS["category_id"]
    )
    features["condition_score"] = safe_float(
        item.get("condition_score"),
        FEATURE_DEFAULTS["condition_score"]
    )
    
    # Sprint 5: Cache metadata
    features["cache_age_sec"] = safe_float(
        item.get("cache_age_sec"),
        FEATURE_DEFAULTS["cache_age_sec"]
    )
    features["cache_hit"] = safe_int(
        item.get("cache_hit"),
        FEATURE_DEFAULTS["cache_hit"]
    )
    
    # Temporal features
    created_at = item.get("created_at")
    if created_at:
        try:
            if isinstance(created_at, str):
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            elif isinstance(created_at, (int, float)):
                dt = datetime.fromtimestamp(created_at)
            else:
                dt = created_at
            
            features["time_of_day"] = float(dt.hour)
            features["day_of_week"] = float(dt.weekday())
            
            # Listing age
            now = time.time()
            listing_timestamp = dt.timestamp()
            features["listing_age_sec"] = max(0, now - listing_timestamp)
        except Exception as e:
            logger.warning(f"Error parsing created_at: {e}")
            features["time_of_day"] = FEATURE_DEFAULTS["time_of_day"]
            features["day_of_week"] = FEATURE_DEFAULTS["day_of_week"]
            features["listing_age_sec"] = FEATURE_DEFAULTS["listing_age_sec"]
    else:
        features["time_of_day"] = FEATURE_DEFAULTS["time_of_day"]
        features["day_of_week"] = FEATURE_DEFAULTS["day_of_week"]
        features["listing_age_sec"] = FEATURE_DEFAULTS["listing_age_sec"]
    
    # Clamp all features to valid ranges
    for feature_name, (min_val, max_val) in FEATURE_RANGES.items():
        if feature_name in features:
            features[feature_name] = clamp(
                features[feature_name],
                min_val,
                max_val
            )
    
    return features


def get_feature_names() -> list:
    """
    Get ordered list of feature names.
    
    Returns:
        List of feature names in order expected by model
    """
    return [
        "internal_estimate",
        "market_value",
        "demand_score",
        "trend_delta",
        "seller_trust",
        "category_id",
        "condition_score",
        "cache_age_sec",
        "cache_hit",
        "time_of_day",
        "day_of_week",
        "listing_age_sec",
    ]


def features_to_array(features: Dict[str, float]) -> list:
    """
    Convert feature dictionary to ordered array for model input.
    
    Args:
        features: Feature dictionary from build_features()
    
    Returns:
        List of feature values in expected order
    """
    feature_names = get_feature_names()
    return [features.get(name, FEATURE_DEFAULTS.get(name, 0.0)) for name in feature_names]


def validate_features(features: Dict[str, float]) -> bool:
    """
    Validate that features are within acceptable ranges.
    
    Args:
        features: Feature dictionary
    
    Returns:
        True if valid, False otherwise
    """
    feature_names = get_feature_names()
    
    # Check all required features present
    for name in feature_names:
        if name not in features:
            logger.warning(f"Missing feature: {name}")
            return False
    
    # Check ranges
    for name, (min_val, max_val) in FEATURE_RANGES.items():
        value = features.get(name)
        if value is not None and not (min_val <= value <= max_val):
            logger.warning(
                f"Feature {name}={value} outside range [{min_val}, {max_val}]"
            )
            return False
    
    return True
