"""
Sprint 6: Online ML Inference Service for Valuation

Loads trained models, performs inference with blending, and implements
safety fallbacks.
"""

import json
import os
import pickle
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import logging

import numpy as np

from backend.ml.features import build_features, features_to_array, validate_features

logger = logging.getLogger(__name__)

# Configuration (override via environment)
ML_BLEND_ALPHA = float(os.getenv("ML_BLEND_ALPHA", "0.35"))
MODELS_DIR = os.getenv("MODELS_DIR", "models/")
ACTIVE_MODEL_FILE = os.getenv("ACTIVE_MODEL_FILE", "models/active.json")

# Safety bounds
SAFETY_CLAMP_MIN = 0.5  # 0.5x of fused value
SAFETY_CLAMP_MAX = 2.0  # 2.0x of fused value
CONFIDENCE_THRESHOLD = 0.5  # Apply clamping when confidence < this


class ValuationMLService:
    """
    Online ML inference service for valuation prediction.
    """
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.meta = None
        self._load_active_model()
    
    def _load_active_model(self) -> bool:
        """
        Load active model from registry.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            # Read active model registry
            active_path = Path(ACTIVE_MODEL_FILE)
            if not active_path.exists():
                logger.warning(f"No active model registry at {ACTIVE_MODEL_FILE}")
                return False
            
            with open(active_path, 'r') as f:
                active_info = json.load(f)
            
            version = active_info.get("version")
            if not version:
                logger.error("No version in active model registry")
                return False
            
            # Load model artifacts
            model_path = Path(MODELS_DIR) / f"valuation_{version}.pkl"
            meta_path = Path(MODELS_DIR) / f"valuation_{version}.meta.json"
            
            if not model_path.exists():
                logger.error(f"Model file not found: {model_path}")
                return False
            
            # Load model
            with open(model_path, 'rb') as f:
                artifacts = pickle.load(f)
            
            self.model = artifacts.get("model")
            self.scaler = artifacts.get("scaler")
            
            # Load metadata
            if meta_path.exists():
                with open(meta_path, 'r') as f:
                    self.meta = json.load(f)
            else:
                self.meta = {"version": version}
            
            logger.info(f"Loaded model version {version}")
            logger.info(f"Model metrics: {self.meta.get('metrics', {})}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}", exc_info=True)
            self.model = None
            self.scaler = None
            self.meta = None
            return False
    
    def reload_model(self) -> bool:
        """Reload active model from disk."""
        return self._load_active_model()
    
    def is_model_loaded(self) -> bool:
        """Check if model is loaded and ready."""
        return self.model is not None and self.scaler is not None
    
    def predict_price(
        self,
        features: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Predict price using loaded model.
        
        Args:
            features: Feature dictionary from build_features()
        
        Returns:
            Dictionary with:
                - ml_price: Model prediction
                - model_confidence: Model confidence score
                - model_version: Active model version
                - error: Error message if prediction failed
        """
        if not self.is_model_loaded():
            return {
                "ml_price": None,
                "model_confidence": 0.0,
                "model_version": None,
                "error": "no_model_loaded"
            }
        
        try:
            # Validate features
            if not validate_features(features):
                logger.warning("Invalid features provided")
                return {
                    "ml_price": None,
                    "model_confidence": 0.0,
                    "model_version": self.meta.get("version"),
                    "error": "invalid_features"
                }
            
            # Convert to array
            X = np.array([features_to_array(features)])
            
            # Scale
            X_scaled = self.scaler.transform(X)
            
            # Predict
            ml_price = float(self.model.predict(X_scaled)[0])
            
            # Model confidence (simplified - based on training metrics)
            model_confidence = self._compute_model_confidence(features)
            
            return {
                "ml_price": ml_price,
                "model_confidence": model_confidence,
                "model_version": self.meta.get("version"),
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Prediction error: {e}", exc_info=True)
            return {
                "ml_price": None,
                "model_confidence": 0.0,
                "model_version": self.meta.get("version"),
                "error": str(e)
            }
    
    def _compute_model_confidence(self, features: Dict[str, float]) -> float:
        """
        Compute model confidence based on feature quality.
        
        Simple heuristic: confidence degrades with:
        - Old cache (cache_age_sec)
        - Low data quality indicators
        
        Returns:
            Confidence score 0-1
        """
        base_confidence = 0.8  # Base from training R?
        
        # Degrade for old cache
        cache_age = features.get("cache_age_sec", 0)
        if cache_age > 3600:  # > 1 hour
            cache_penalty = min(0.2, (cache_age - 3600) / 18000)  # Up to -0.2
            base_confidence -= cache_penalty
        
        # Degrade for missing market data
        if features.get("market_value", 0) == 0:
            base_confidence -= 0.1
        
        return max(0.0, min(1.0, base_confidence))
    
    def blend_with_fused_value(
        self,
        ml_price: float,
        fused_market_value: float,
        ml_confidence: float,
        fused_confidence: float,
        alpha: float = ML_BLEND_ALPHA
    ) -> Dict[str, Any]:
        """
        Blend ML prediction with fused market value.
        
        Args:
            ml_price: ML model prediction
            fused_market_value: Phase 11 fused market value
            ml_confidence: ML model confidence
            fused_confidence: Fused market confidence
            alpha: Blend factor (0 = all fused, 1 = all ML)
        
        Returns:
            Dictionary with:
                - blended_price: Final blended price
                - final_confidence: Minimum of both confidences
                - clamped: Whether safety clamping was applied
        """
        # Blend prices
        blended_price = alpha * ml_price + (1 - alpha) * fused_market_value
        
        # Final confidence is minimum of both
        final_confidence = min(ml_confidence, fused_confidence)
        
        # Safety clamping for low confidence
        clamped = False
        if final_confidence < CONFIDENCE_THRESHOLD:
            # Clamp to safe range around fused value
            min_price = fused_market_value * SAFETY_CLAMP_MIN
            max_price = fused_market_value * SAFETY_CLAMP_MAX
            
            if blended_price < min_price or blended_price > max_price:
                blended_price = max(min_price, min(max_price, blended_price))
                clamped = True
                logger.info(
                    f"Applied safety clamp: confidence={final_confidence:.2f}, "
                    f"range=[{min_price:.2f}, {max_price:.2f}]"
                )
        
        return {
            "blended_price": blended_price,
            "final_confidence": final_confidence,
            "clamped": clamped,
            "alpha": alpha
        }
    
    def predict_and_blend(
        self,
        item: Dict[str, Any],
        fused_market_value: float,
        fused_confidence: float
    ) -> Dict[str, Any]:
        """
        Full pipeline: build features, predict, blend.
        
        Args:
            item: Item data dictionary
            fused_market_value: Phase 11 fused value (fallback)
            fused_confidence: Phase 11 confidence
        
        Returns:
            Dictionary with:
                - price: Final price (blended or fallback)
                - confidence: Final confidence
                - ml_used: Whether ML was used
                - fallback_reason: Reason if ML not used
                - details: Additional info
        """
        start_time = time.time()
        
        # Check if model loaded
        if not self.is_model_loaded():
            return {
                "price": fused_market_value,
                "confidence": fused_confidence,
                "ml_used": False,
                "fallback_reason": "no_model",
                "details": {}
            }
        
        try:
            # Build features
            features = build_features(item)
            
            # Predict
            pred_result = self.predict_price(features)
            
            if pred_result["error"]:
                # Prediction failed, use fallback
                return {
                    "price": fused_market_value,
                    "confidence": fused_confidence,
                    "ml_used": False,
                    "fallback_reason": pred_result["error"],
                    "details": {"model_version": pred_result.get("model_version")}
                }
            
            # Blend with fused value
            blend_result = self.blend_with_fused_value(
                pred_result["ml_price"],
                fused_market_value,
                pred_result["model_confidence"],
                fused_confidence
            )
            
            latency = time.time() - start_time
            
            return {
                "price": blend_result["blended_price"],
                "confidence": blend_result["final_confidence"],
                "ml_used": True,
                "fallback_reason": None,
                "details": {
                    "model_version": pred_result["model_version"],
                    "ml_price": pred_result["ml_price"],
                    "fused_price": fused_market_value,
                    "alpha": blend_result["alpha"],
                    "clamped": blend_result["clamped"],
                    "latency_ms": latency * 1000
                }
            }
            
        except Exception as e:
            logger.error(f"Error in predict_and_blend: {e}", exc_info=True)
            return {
                "price": fused_market_value,
                "confidence": fused_confidence,
                "ml_used": False,
                "fallback_reason": "exception",
                "details": {"error": str(e)}
            }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about active model."""
        if not self.is_model_loaded():
            return {
                "loaded": False,
                "version": None,
                "metrics": {}
            }
        
        return {
            "loaded": True,
            "version": self.meta.get("version"),
            "created_at": self.meta.get("created_at"),
            "metrics": self.meta.get("metrics", {}),
            "features": self.meta.get("features", []),
            "lib": self.meta.get("lib"),
            "hash": self.meta.get("hash")
        }


# Global service instance
_ml_service: Optional[ValuationMLService] = None


def get_ml_service() -> ValuationMLService:
    """Get global ML service instance (singleton)."""
    global _ml_service
    if _ml_service is None:
        _ml_service = ValuationMLService()
    return _ml_service


def reload_ml_service() -> bool:
    """Reload ML service (e.g., after model activation)."""
    global _ml_service
    _ml_service = ValuationMLService()
    return _ml_service.is_model_loaded()
