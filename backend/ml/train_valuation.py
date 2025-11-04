"""
Sprint 6: ML Valuation Model Training Pipeline

Trains valuation models with XGBoost/sklearn fallback, handles
multiple data sources, and saves versioned artifacts.

Usage:
    python -m backend.ml.train_valuation --out models/ --notes "v1 baseline"
"""

import argparse
import json
import os
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import pickle
import logging

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, r2_score

# Try XGBoost first, fall back to sklearn
try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    from sklearn.ensemble import GradientBoostingRegressor
    HAS_XGBOOST = False

from backend.ml.features import get_feature_names

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_training_data() -> Optional[pd.DataFrame]:
    """
    Load training data from available sources in priority order:
    1. Postgres view `training_valuation_samples`
    2. CSV file `data/valuation_samples.csv`
    3. Generate synthetic dataset
    
    Returns:
        DataFrame with columns: features + target_price
    """
    # Try Postgres first (production)
    try:
        from sqlalchemy import create_engine
        import os
        
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            engine = create_engine(db_url)
            query = "SELECT * FROM training_valuation_samples LIMIT 10000"
            df = pd.read_sql(query, engine)
            if not df.empty:
                logger.info(f"Loaded {len(df)} samples from Postgres")
                return df
    except Exception as e:
        logger.warning(f"Could not load from Postgres: {e}")
    
    # Try CSV file
    csv_path = Path("data/valuation_samples.csv")
    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            logger.info(f"Loaded {len(df)} samples from {csv_path}")
            return df
        except Exception as e:
            logger.warning(f"Could not load from CSV: {e}")
    
    # Generate synthetic data (deterministic)
    logger.info("Generating synthetic training data...")
    return generate_synthetic_data(n_samples=5000, seed=42)


def generate_synthetic_data(n_samples: int = 5000, seed: int = 42) -> pd.DataFrame:
    """
    Generate synthetic valuation training data.
    
    Args:
        n_samples: Number of samples to generate
        seed: Random seed for reproducibility
    
    Returns:
        DataFrame with features and target_price
    """
    np.random.seed(seed)
    
    feature_names = get_feature_names()
    
    # Generate features with realistic distributions
    data = {}
    
    # Price-related features (lognormal)
    data["internal_estimate"] = np.random.lognormal(7, 1, n_samples)  # ~1000-5000
    data["market_value"] = data["internal_estimate"] * np.random.uniform(0.8, 1.3, n_samples)
    
    # Scores (beta distribution)
    data["demand_score"] = np.random.beta(2, 2, n_samples)
    data["seller_trust"] = np.random.beta(5, 2, n_samples)  # Skewed towards high trust
    data["condition_score"] = np.random.beta(3, 2, n_samples)
    
    # Trend (normal around 0)
    data["trend_delta"] = np.random.normal(0, 0.15, n_samples)
    
    # Categories (uniform discrete)
    data["category_id"] = np.random.randint(0, 20, n_samples)
    
    # Cache metadata
    data["cache_age_sec"] = np.random.exponential(1800, n_samples)  # ~30 min avg
    data["cache_hit"] = np.random.binomial(1, 0.7, n_samples)  # 70% hit rate
    
    # Temporal
    data["time_of_day"] = np.random.randint(0, 24, n_samples)
    data["day_of_week"] = np.random.randint(0, 7, n_samples)
    data["listing_age_sec"] = np.random.exponential(172800, n_samples)  # ~2 days avg
    
    # Generate target price with realistic relationship
    # Base on market_value with adjustments
    target_price = data["market_value"] * (
        1.0 +
        0.1 * data["demand_score"] +
        0.05 * data["trend_delta"] +
        0.05 * data["seller_trust"] +
        0.03 * (data["condition_score"] - 0.5) +
        np.random.normal(0, 0.1, n_samples)  # Noise
    )
    
    # Ensure positive prices
    data["target_price"] = np.maximum(target_price, 10)
    
    df = pd.DataFrame(data)
    
    return df


def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculate Mean Absolute Percentage Error.
    
    Handles division by zero gracefully.
    """
    # Avoid division by zero
    mask = y_true != 0
    if not mask.any():
        return 0.0
    
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100


def train_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    use_xgboost: bool = True
) -> Tuple[Any, Dict[str, float]]:
    """
    Train valuation model with XGBoost or sklearn fallback.
    
    Args:
        X_train, y_train: Training data
        X_val, y_val: Validation data
        use_xgboost: Use XGBoost if available
    
    Returns:
        (model, metrics_dict)
    """
    logger.info(f"Training with {'XGBoost' if use_xgboost and HAS_XGBOOST else 'sklearn GradientBoosting'}...")
    
    if use_xgboost and HAS_XGBOOST:
        # XGBoost model
        model = xgb.XGBRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            early_stopping_rounds=20,
            verbose=False
        )
        
        lib_name = "xgboost"
        lib_version = xgb.__version__
    else:
        # Sklearn fallback
        model = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42
        )
        
        model.fit(X_train, y_train)
        
        lib_name = "sklearn"
        import sklearn
        lib_version = sklearn.__version__
    
    # Evaluate on validation set
    y_pred = model.predict(X_val)
    
    mae = mean_absolute_error(y_val, y_pred)
    mape = calculate_mape(y_val, y_pred)
    r2 = r2_score(y_val, y_pred)
    
    metrics = {
        "mae": float(mae),
        "mape": float(mape),
        "r2": float(r2),
        "n_train": len(X_train),
        "n_val": len(X_val),
        "lib": lib_name,
        "lib_version": lib_version
    }
    
    logger.info(f"Validation Metrics:")
    logger.info(f"  MAE:  {mae:.2f}")
    logger.info(f"  MAPE: {mape:.2f}%")
    logger.info(f"  R?:   {r2:.4f}")
    
    return model, metrics


def save_model_artifacts(
    model: Any,
    scaler: StandardScaler,
    metrics: Dict[str, float],
    output_dir: str,
    notes: str = ""
) -> Dict[str, str]:
    """
    Save model artifacts with versioning.
    
    Args:
        model: Trained model
        scaler: Feature scaler
        metrics: Training metrics
        output_dir: Output directory
        notes: Optional version notes
    
    Returns:
        Dictionary with saved file paths
    """
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = int(time.time())
    version = f"v{timestamp}"
    
    # Save model
    model_path = Path(output_dir) / f"valuation_{version}.pkl"
    with open(model_path, 'wb') as f:
        pickle.dump({"model": model, "scaler": scaler}, f)
    
    # Calculate model hash
    with open(model_path, 'rb') as f:
        model_hash = hashlib.sha256(f.read()).hexdigest()[:16]
    
    # Save metadata
    meta = {
        "version": version,
        "timestamp": timestamp,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": metrics,
        "features": get_feature_names(),
        "lib": metrics.get("lib", "unknown"),
        "lib_version": metrics.get("lib_version", "unknown"),
        "hash": model_hash,
        "notes": notes
    }
    
    meta_path = Path(output_dir) / f"valuation_{version}.meta.json"
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)
    
    logger.info(f"Model saved: {model_path}")
    logger.info(f"Metadata saved: {meta_path}")
    
    return {
        "model_path": str(model_path),
        "meta_path": str(meta_path),
        "version": version
    }


def main():
    parser = argparse.ArgumentParser(description="Train valuation model")
    parser.add_argument("--out", type=str, default="models/", help="Output directory")
    parser.add_argument("--notes", type=str, default="", help="Version notes")
    parser.add_argument("--no-xgboost", action="store_true", help="Force sklearn instead of XGBoost")
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("ML Valuation Model Training Pipeline")
    logger.info("=" * 60)
    
    # Load data
    df = load_training_data()
    if df is None:
        logger.error("Failed to load training data")
        return 1
    
    logger.info(f"Total samples: {len(df)}")
    
    # Prepare features and target
    feature_names = get_feature_names()
    
    # Check if all features present
    missing_features = set(feature_names) - set(df.columns)
    if missing_features:
        logger.error(f"Missing features in data: {missing_features}")
        return 1
    
    X = df[feature_names].values
    y = df["target_price"].values
    
    # Train/val split
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    logger.info(f"Train samples: {len(X_train)}")
    logger.info(f"Val samples: {len(X_val)}")
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    
    # Train model
    use_xgboost = not args.no_xgboost
    model, metrics = train_model(
        X_train_scaled, y_train,
        X_val_scaled, y_val,
        use_xgboost=use_xgboost
    )
    
    # Save artifacts
    paths = save_model_artifacts(
        model,
        scaler,
        metrics,
        args.out,
        args.notes
    )
    
    logger.info("=" * 60)
    logger.info("Training complete!")
    logger.info(f"Version: {paths['version']}")
    logger.info("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())
