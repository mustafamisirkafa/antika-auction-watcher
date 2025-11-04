"""
Sprint 6: Model Registry & Admin API

Endpoints for training, activating, and managing ML models.
"""

import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
import logging

from backend.services.valuation_ml import get_ml_service, reload_ml_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/valuation/model", tags=["ML Model Registry"])

# Configuration
MODELS_DIR = "models/"
ACTIVE_MODEL_FILE = "models/active.json"


# Request/Response Models
class ActivateModelRequest(BaseModel):
    version: str
    notes: str = ""


class TrainModelRequest(BaseModel):
    notes: str = ""
    no_xgboost: bool = False


class ModelStatusResponse(BaseModel):
    active_version: str | None
    loaded: bool
    metrics: Dict[str, Any]
    created_at: str | None


class ModelVersionInfo(BaseModel):
    version: str
    created_at: str
    metrics: Dict[str, Any]
    features: List[str]
    lib: str
    hash: str
    notes: str
    is_active: bool


# Dependency: Admin-only access
def require_admin():
    """
    Dependency for admin-only endpoints.
    
    In production, implement proper RBAC check.
    For now, placeholder that allows all (UNSAFE - implement auth!)
    """
    # TODO: Implement real RBAC
    # from fastapi import Header
    # if user_role != "ADMIN":
    #     raise HTTPException(403, "Admin access required")
    pass


@router.get("/status", response_model=ModelStatusResponse)
async def get_model_status():
    """
    Get status of currently active model.
    
    Returns:
        ModelStatusResponse with version, metrics, etc.
    """
    ml_service = get_ml_service()
    model_info = ml_service.get_model_info()
    
    # Get active version from registry
    active_version = None
    try:
        active_path = Path(ACTIVE_MODEL_FILE)
        if active_path.exists():
            with open(active_path, 'r') as f:
                active_info = json.load(f)
                active_version = active_info.get("version")
    except Exception as e:
        logger.warning(f"Could not read active model file: {e}")
    
    return ModelStatusResponse(
        active_version=active_version,
        loaded=model_info["loaded"],
        metrics=model_info.get("metrics", {}),
        created_at=model_info.get("created_at")
    )


@router.get("/versions", response_model=List[ModelVersionInfo])
async def list_model_versions():
    """
    List all available model versions.
    
    Returns:
        List of ModelVersionInfo for each saved model
    """
    models_path = Path(MODELS_DIR)
    if not models_path.exists():
        return []
    
    # Get active version
    active_version = None
    try:
        active_path = Path(ACTIVE_MODEL_FILE)
        if active_path.exists():
            with open(active_path, 'r') as f:
                active_info = json.load(f)
                active_version = active_info.get("version")
    except:
        pass
    
    # Find all metadata files
    versions = []
    for meta_file in models_path.glob("valuation_*.meta.json"):
        try:
            with open(meta_file, 'r') as f:
                meta = json.load(f)
            
            version = meta.get("version", "unknown")
            
            versions.append(ModelVersionInfo(
                version=version,
                created_at=meta.get("created_at", ""),
                metrics=meta.get("metrics", {}),
                features=meta.get("features", []),
                lib=meta.get("lib", "unknown"),
                hash=meta.get("hash", ""),
                notes=meta.get("notes", ""),
                is_active=(version == active_version)
            ))
        except Exception as e:
            logger.warning(f"Could not load metadata from {meta_file}: {e}")
    
    # Sort by creation time (newest first)
    versions.sort(key=lambda v: v.created_at, reverse=True)
    
    return versions


@router.post("/activate")
async def activate_model(
    request: ActivateModelRequest,
    _: None = Depends(require_admin)
):
    """
    Activate a specific model version.
    
    Args:
        request: ActivateModelRequest with version
    
    Returns:
        Success message
    
    Requires: ADMIN role
    """
    version = request.version
    
    # Verify model exists
    model_path = Path(MODELS_DIR) / f"valuation_{version}.pkl"
    meta_path = Path(MODELS_DIR) / f"valuation_{version}.meta.json"
    
    if not model_path.exists():
        raise HTTPException(404, f"Model version {version} not found")
    
    if not meta_path.exists():
        raise HTTPException(404, f"Metadata for version {version} not found")
    
    # Write active model registry
    try:
        active_info = {
            "version": version,
            "activated_at": str(pd.Timestamp.now()),
            "notes": request.notes
        }
        
        active_path = Path(ACTIVE_MODEL_FILE)
        active_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(active_path, 'w') as f:
            json.dump(active_info, f, indent=2)
        
        # Reload ML service
        success = reload_ml_service()
        
        if not success:
            raise HTTPException(500, "Model activation succeeded but reload failed")
        
        logger.info(f"Activated model version {version}")
        
        return {
            "status": "success",
            "message": f"Model version {version} activated",
            "version": version
        }
        
    except Exception as e:
        logger.error(f"Error activating model: {e}", exc_info=True)
        raise HTTPException(500, f"Activation failed: {str(e)}")


@router.post("/train")
async def train_model(
    request: TrainModelRequest,
    background_tasks: BackgroundTasks,
    _: None = Depends(require_admin)
):
    """
    Trigger model training (runs in background).
    
    Args:
        request: TrainModelRequest with training options
        background_tasks: FastAPI background tasks
    
    Returns:
        Job submission confirmation
    
    Requires: ADMIN role
    """
    def run_training():
        """Background task to run training."""
        try:
            logger.info("Starting model training...")
            
            cmd = [
                "python", "-m", "backend.ml.train_valuation",
                "--out", MODELS_DIR,
                "--notes", request.notes
            ]
            
            if request.no_xgboost:
                cmd.append("--no-xgboost")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            if result.returncode == 0:
                logger.info("Model training completed successfully")
                logger.info(f"Training output: {result.stdout}")
            else:
                logger.error(f"Model training failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("Model training timed out")
        except Exception as e:
            logger.error(f"Error running training: {e}", exc_info=True)
    
    # Queue training as background task
    background_tasks.add_task(run_training)
    
    return {
        "status": "submitted",
        "message": "Model training job submitted (runs in background)",
        "notes": request.notes
    }


# Import pandas for timestamp (only if needed)
try:
    import pandas as pd
except ImportError:
    from datetime import datetime
    
    class pd:
        class Timestamp:
            @staticmethod
            def now():
                return datetime.now().isoformat()
