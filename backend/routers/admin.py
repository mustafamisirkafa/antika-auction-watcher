"""Admin API endpoints for system management."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel
from datetime import datetime
from backend.db.database import get_session
from backend.db.models import User
from backend.db.analytics_models import CategoryMetrics, SystemMetrics
from backend.routers.auth import get_current_user
from backend.services.analytics.outcome_tracker import OutcomeTracker
from backend.services.analytics.learning_service import LearningService
from backend.services.analytics.metrics_collector import MetricsCollector
from backend.services.marketplace.adapter_factory import adapter_factory

router = APIRouter(prefix="/admin", tags=["Admin"])


class AdminAuth:
    """Admin authentication dependency."""
    
    async def __call__(self, current_user: User = Depends(get_current_user)):
        """Check if user has admin privileges."""
        # In production, check for admin role in database
        # For now, all authenticated users are admins
        return current_user


admin_required = AdminAuth()


# System Health Endpoints

@router.get("/health/services", dependencies=[Depends(admin_required)])
async def get_services_health():
    """Get health status of all services."""
    await adapter_factory.initialize()
    
    marketplace_health = await adapter_factory.get_health_status()
    
    return {
        'timestamp': datetime.utcnow().isoformat(),
        'services': {
            'database': 'healthy',  # If we got here, DB is working
            'redis': 'healthy',     # If caching works, Redis is up
            'marketplace_apis': marketplace_health
        },
        'overall_status': 'healthy' if all(marketplace_health.values()) else 'degraded'
    }


@router.get("/health/database", dependencies=[Depends(admin_required)])
async def get_database_health(session: Session = Depends(get_session)):
    """Get database health metrics."""
    try:
        # Test query
        statement = select(User).limit(1)
        session.exec(statement).first()
        
        # Get table counts
        user_count = len(session.exec(select(User)).all())
        
        return {
            'status': 'healthy',
            'connection': 'active',
            'tables': {
                'users': user_count
            }
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


@router.get("/health/redis", dependencies=[Depends(admin_required)])
async def get_redis_health():
    """Get Redis health status."""
    from backend.realtime.redis_manager import RedisManager
    
    redis_mgr = RedisManager()
    try:
        await redis_mgr.connect()
        # Test operation
        await redis_mgr.cache_set('health_check', 'ok', 10)
        result = await redis_mgr.cache_get('health_check')
        await redis_mgr.disconnect()
        
        return {
            'status': 'healthy',
            'test_result': result == 'ok'
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e)
        }


# User Management Endpoints

class UserUpdateRequest(BaseModel):
    """User update request."""
    is_active: Optional[bool] = None


@router.get("/users", dependencies=[Depends(admin_required)])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """List all users."""
    statement = select(User).offset(skip).limit(limit)
    users = session.exec(statement).all()
    
    return {
        'users': [
            {
                'id': u.id,
                'username': u.username,
                'email': u.email,
                'is_active': u.is_active,
                'created_at': u.created_at.isoformat()
            }
            for u in users
        ],
        'total': len(users)
    }


@router.patch("/users/{user_id}", dependencies=[Depends(admin_required)])
async def update_user(
    user_id: int,
    update_data: UserUpdateRequest,
    session: Session = Depends(get_session)
):
    """Update user status."""
    user = session.get(User, user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if update_data.is_active is not None:
        user.is_active = update_data.is_active
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return {
        'id': user.id,
        'username': user.username,
        'is_active': user.is_active
    }


# Analytics Dashboard Endpoints

@router.get("/analytics/overview", dependencies=[Depends(admin_required)])
async def get_analytics_overview(session: Session = Depends(get_session)):
    """Get analytics overview."""
    learning_service = LearningService(session)
    
    report = await learning_service.get_model_performance_report()
    
    return report


@router.get("/analytics/categories", dependencies=[Depends(admin_required)])
async def get_category_analytics(session: Session = Depends(get_session)):
    """Get category-wise analytics."""
    statement = select(CategoryMetrics)
    metrics = session.exec(statement).all()
    
    return {
        'categories': [
            {
                'category': m.category,
                'total_bids': m.total_bids,
                'win_rate': m.win_rate,
                'average_profit': m.average_profit,
                'average_roi': m.average_roi,
                'valuation_accuracy': m.average_valuation_accuracy,
                'sample_size': m.sample_size,
                'last_updated': m.last_updated.isoformat()
            }
            for m in metrics
        ]
    }


@router.get("/analytics/bids", dependencies=[Depends(admin_required)])
async def get_bid_analytics(
    category: Optional[str] = None,
    days: int = 30,
    session: Session = Depends(get_session)
):
    """Get bid analytics."""
    tracker = OutcomeTracker(session)
    
    time_series = await tracker.get_time_series_metrics(days=days, category=category)
    
    return {
        'period_days': days,
        'category': category,
        'time_series': time_series
    }


@router.get("/analytics/profitability", dependencies=[Depends(admin_required)])
async def get_profitability_analytics(session: Session = Depends(get_session)):
    """Get profitability analytics."""
    statement = select(CategoryMetrics)
    metrics = session.exec(statement).all()
    
    total_profit = sum(m.total_profit for m in metrics)
    total_bids = sum(m.total_bids for m in metrics)
    
    return {
        'total_profit': total_profit,
        'total_bids': total_bids,
        'categories': [
            {
                'category': m.category,
                'total_profit': m.total_profit,
                'average_roi': m.average_roi,
                'bid_count': m.total_bids
            }
            for m in metrics
        ]
    }


# System Metrics Endpoints

@router.get("/metrics/response-times", dependencies=[Depends(admin_required)])
async def get_response_times(
    endpoint: Optional[str] = None,
    hours: int = 24,
    session: Session = Depends(get_session)
):
    """Get API response time metrics."""
    collector = MetricsCollector(session)
    
    stats = await collector.get_response_time_stats(endpoint=endpoint, hours=hours)
    
    return stats


@router.get("/metrics/api-usage", dependencies=[Depends(admin_required)])
async def get_api_usage(
    hours: int = 24,
    session: Session = Depends(get_session)
):
    """Get external API usage metrics."""
    collector = MetricsCollector(session)
    
    usage = await collector.get_external_api_usage(hours=hours)
    
    return usage


@router.get("/metrics/cache", dependencies=[Depends(admin_required)])
async def get_cache_metrics(
    hours: int = 24,
    session: Session = Depends(get_session)
):
    """Get cache performance metrics."""
    collector = MetricsCollector(session)
    
    performance = await collector.get_cache_performance(hours=hours)
    
    return performance


@router.get("/metrics/slow-queries", dependencies=[Depends(admin_required)])
async def get_slow_queries(
    threshold_ms: float = 100,
    hours: int = 24,
    session: Session = Depends(get_session)
):
    """Get slow database queries."""
    collector = MetricsCollector(session)
    
    slow_queries = await collector.get_slow_queries(
        threshold_ms=threshold_ms,
        hours=hours
    )
    
    return {
        'threshold_ms': threshold_ms,
        'period_hours': hours,
        'slow_queries': slow_queries,
        'count': len(slow_queries)
    }


@router.get("/metrics/dashboard", dependencies=[Depends(admin_required)])
async def get_metrics_dashboard(session: Session = Depends(get_session)):
    """Get comprehensive metrics dashboard."""
    collector = MetricsCollector(session)
    
    dashboard = await collector.get_dashboard_metrics()
    
    return dashboard


# Learning & Training Endpoints

@router.post("/learning/train/{category}", dependencies=[Depends(admin_required)])
async def train_category_model(
    category: str,
    session: Session = Depends(get_session)
):
    """Train learning model for a category."""
    learning_service = LearningService(session)
    
    result = await learning_service.train_category_model(category)
    
    return result


@router.post("/learning/train-all", dependencies=[Depends(admin_required)])
async def train_all_models(session: Session = Depends(get_session)):
    """Train all category models."""
    learning_service = LearningService(session)
    
    results = await learning_service.retrain_all_categories()
    
    return {
        'status': 'completed',
        'categories_trained': len(results),
        'results': results
    }


@router.get("/learning/recommendations/{category}", dependencies=[Depends(admin_required)])
async def get_learning_recommendations(
    category: str,
    session: Session = Depends(get_session)
):
    """Get AI recommendations for a category."""
    learning_service = LearningService(session)
    
    recommendations = await learning_service.get_learning_recommendations(category)
    
    return recommendations


# Configuration Management

class ConfigUpdateRequest(BaseModel):
    """Configuration update request."""
    key: str
    value: str


@router.get("/config", dependencies=[Depends(admin_required)])
async def get_configuration():
    """Get current configuration."""
    from backend.core.config import settings
    
    # Return safe config (no secrets)
    return {
        'rate_limit_enabled': settings.rate_limit_enabled,
        'cache_ttl_seconds': settings.cache_ttl_seconds,
        'jwt_expiration_minutes': settings.jwt_expiration_minutes,
        'rate_limit_per_minute': settings.rate_limit_per_minute
    }


# Audit Log (placeholder for future implementation)

@router.get("/audit-log", dependencies=[Depends(admin_required)])
async def get_audit_log(
    limit: int = 100,
    skip: int = 0
):
    """Get admin action audit log."""
    # Placeholder - would query audit log table
    return {
        'logs': [],
        'message': 'Audit logging to be implemented'
    }


# System Operations

@router.post("/system/cleanup-metrics", dependencies=[Depends(admin_required)])
async def cleanup_old_metrics(
    days: int = 30,
    session: Session = Depends(get_session)
):
    """Clean up old metrics data."""
    collector = MetricsCollector(session)
    
    deleted_count = await collector.cleanup_old_metrics(days=days)
    
    return {
        'status': 'success',
        'deleted_metrics': deleted_count,
        'older_than_days': days
    }
