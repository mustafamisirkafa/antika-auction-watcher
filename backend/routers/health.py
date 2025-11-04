"""
Health Check Endpoints (Sprint 1)
Provides liveness, readiness, and metrics endpoints.
"""
import logging
import time
from typing import Dict, Any
from fastapi import APIRouter, Depends, Response, status
from sqlmodel import Session, select, func
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CollectorRegistry,
    CONTENT_TYPE_LATEST,
)
import psutil

from backend.db.database import get_db
from backend.middleware.team_context import get_redis
from backend.models.user_prefs import UserPreference
from backend.core.circuit_breaker import get_all_circuit_breaker_states

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])

# Prometheus metrics registry
registry = CollectorRegistry()

# HTTP metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint'],
    registry=registry
)

# AutoBid metrics
autobid_active_sessions = Gauge(
    'autobid_active_sessions',
    'Number of active AutoBid sessions',
    registry=registry
)

autobid_sla_duration = Histogram(
    'autobid_sla_duration_seconds',
    'AutoBid decision duration',
    buckets=[0.1, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 5.0],
    registry=registry
)

# Cache metrics
cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_type'],
    registry=registry
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_type'],
    registry=registry
)

# Database metrics
db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['query_type'],
    registry=registry
)

db_connections_active = Gauge(
    'db_connections_active',
    'Number of active database connections',
    registry=registry
)

# Redis metrics
redis_operation_duration = Histogram(
    'redis_operation_duration_seconds',
    'Redis operation duration',
    ['operation'],
    registry=registry
)

# System metrics
system_cpu_usage = Gauge(
    'system_cpu_usage_percent',
    'System CPU usage percentage',
    registry=registry
)

system_memory_usage = Gauge(
    'system_memory_usage_percent',
    'System memory usage percentage',
    registry=registry
)


@router.get("/health")
async def health_check():
    """
    Liveness probe endpoint.
    
    Returns 200 OK if the service is alive.
    Kubernetes/Docker uses this to know if the container is alive.
    
    This endpoint should be lightweight and always succeed unless
    the application is completely broken.
    """
    return {
        "status": "healthy",
        "service": "antika-auction-watcher",
        "timestamp": time.time()
    }


@router.get("/ready")
async def readiness_check(
    db: Session = Depends(get_db),
    redis = Depends(get_redis)
):
    """
    Readiness probe endpoint.
    
    Returns 200 OK if the service is ready to handle requests.
    Checks:
    - Redis connection
    - Database connection
    
    Kubernetes/Docker uses this to know when to send traffic.
    """
    checks = {
        "redis": False,
        "database": False,
    }
    
    # Check Redis
    try:
        start = time.time()
        await redis.ping()
        redis_latency = (time.time() - start) * 1000
        checks["redis"] = True
        checks["redis_latency_ms"] = round(redis_latency, 2)
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        checks["redis_error"] = str(e)
    
    # Check Database
    try:
        start = time.time()
        db.exec(select(func.count()).select_from(UserPreference))
        db_latency = (time.time() - start) * 1000
        checks["database"] = True
        checks["db_latency_ms"] = round(db_latency, 2)
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database_error"] = str(e)
    
    # Overall ready status
    is_ready = checks["redis"] and checks["database"]
    
    if not is_ready:
        return Response(
            content={"status": "not_ready", "checks": checks},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    return {
        "status": "ready",
        "checks": checks,
        "timestamp": time.time()
    }


@router.get("/metrics")
async def metrics_endpoint(
    redis = Depends(get_redis)
):
    """
    Prometheus metrics endpoint.
    
    Exposes metrics in Prometheus format for scraping.
    
    Metrics include:
    - HTTP request counts and durations
    - AutoBid session counts and SLA durations
    - Cache hit/miss rates
    - Database query durations
    - Redis operation durations
    - System CPU and memory usage
    """
    # Update system metrics
    system_cpu_usage.set(psutil.cpu_percent(interval=0.1))
    system_memory_usage.set(psutil.virtual_memory().percent)
    
    # Update AutoBid active sessions from Redis
    try:
        active_locks = await redis.keys("lock:autobid:*")
        autobid_active_sessions.set(len(active_locks) if active_locks else 0)
    except Exception as e:
        logger.error(f"Error fetching AutoBid metrics: {e}")
    
    # Generate Prometheus metrics
    metrics_output = generate_latest(registry)
    
    return Response(
        content=metrics_output,
        media_type=CONTENT_TYPE_LATEST
    )


@router.get("/status")
async def status_check(
    db: Session = Depends(get_db),
    redis = Depends(get_redis)
):
    """
    Detailed status endpoint with circuit breaker states.
    
    Returns comprehensive system status including:
    - Service health
    - Circuit breaker states
    - Resource usage
    - Connection counts
    """
    # Redis status
    redis_status = {"connected": False, "latency_ms": None}
    try:
        start = time.time()
        await redis.ping()
        redis_status["connected"] = True
        redis_status["latency_ms"] = round((time.time() - start) * 1000, 2)
    except Exception as e:
        redis_status["error"] = str(e)
    
    # Database status
    db_status = {"connected": False, "latency_ms": None}
    try:
        start = time.time()
        db.exec(select(func.count()).select_from(UserPreference))
        db_status["connected"] = True
        db_status["latency_ms"] = round((time.time() - start) * 1000, 2)
    except Exception as e:
        db_status["error"] = str(e)
    
    # Circuit breaker states
    circuit_breakers = get_all_circuit_breaker_states()
    
    # System resources
    resources = {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
    }
    
    return {
        "service": "antika-auction-watcher",
        "status": "operational" if (redis_status["connected"] and db_status["connected"]) else "degraded",
        "redis": redis_status,
        "database": db_status,
        "circuit_breakers": circuit_breakers,
        "resources": resources,
        "timestamp": time.time()
    }
