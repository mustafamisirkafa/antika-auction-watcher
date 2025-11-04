"""Main FastAPI application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.db.database import create_db_and_tables
from backend.realtime.redis_manager import RedisManager
from backend.routers import auth, items, valuations, bids, websocket, admin, advisor, plans, teams, agents, user_prefs, analytics, health
from backend.middleware.rate_limiter import RateLimiter
from backend.middleware.performance import PerformanceMiddleware
from backend.middleware.graceful_shutdown import init_shutdown_handler
from backend.core.security import SecurityHeadersMiddleware, get_cors_config
from backend.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from backend.core.log_redaction import install_global_redaction_filter
from slowapi.errors import RateLimitExceeded

# Sprint 3: Observability
from backend.core.logging_json import setup_json_logging
from backend.core.metrics import init_metrics, metrics
from backend.middleware.observability import ObservabilityMiddleware
from backend.middleware.tracing import init_tracing, instrument_fastapi
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

# Initialize Redis manager
redis_manager = RedisManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    create_db_and_tables()
    await redis_manager.connect()
    
    # Seed plans on startup
    from backend.services.plan_seeder import seed_plans
    from backend.db.database import get_session
    try:
        with get_session() as session:
            seed_plans(session)
    except Exception as e:
        print(f"Warning: Failed to seed plans: {e}")
    
    # Initialize graceful shutdown handler (Sprint 1)
    shutdown_handler = init_shutdown_handler(app)
    print("? Graceful shutdown handler initialized")
    
    # Initialize secure logging with redaction (Sprint 2)
    install_global_redaction_filter()
    print("? Secure logging with redaction initialized")
    
    # Sprint 3: Initialize observability stack
    setup_json_logging(level="INFO", redact_sensitive=True)
    print("✅ JSON structured logging initialized")
    
    init_metrics(version=settings.api_version, environment="production")
    print("✅ Prometheus metrics initialized")
    
    init_tracing(
        service_name="antika-auction-watcher",
        jaeger_host="jaeger",
        jaeger_port=6831,
        environment="production",
        enabled=True
    )
    instrument_fastapi(app)
    print("✅ OpenTelemetry tracing initialized")
    
    yield
    
    # Shutdown
    print("Initiating graceful shutdown...")
    await shutdown_handler.shutdown()
    await redis_manager.disconnect()
    print("Shutdown complete")


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    lifespan=lifespan
)

# Sprint 2: Security headers middleware (HSTS, CSP, etc.)
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware with secure config (Sprint 2)
cors_config = get_cors_config()
app.add_middleware(
    CORSMiddleware,
    **cors_config
)

# Phase 2: Performance monitoring middleware
app.add_middleware(PerformanceMiddleware)

# Phase 2: Rate limiting middleware (legacy)
app.add_middleware(RateLimiter, redis_manager=redis_manager)

# Sprint 2: Enhanced rate limiting with slowapi
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Sprint 3: Observability middleware
app.add_middleware(ObservabilityMiddleware, log_requests=True)

# Include routers
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(items.router, prefix=settings.api_prefix)
app.include_router(valuations.router, prefix=settings.api_prefix)
app.include_router(bids.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)  # Phase 2
app.include_router(advisor.router, prefix=settings.api_prefix)  # Phase 5
app.include_router(plans.router, prefix=settings.api_prefix)  # Phase 8
app.include_router(teams.router, prefix=settings.api_prefix)  # Phase 8
app.include_router(agents.router, prefix=settings.api_prefix)  # Phase 8
app.include_router(user_prefs.router)  # Phase 14
app.include_router(analytics.router)  # Phase 17
app.include_router(health.router)  # Sprint 1: Health endpoints
app.include_router(websocket.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "status": "running"
    }


# Sprint 3: Prometheus metrics endpoint (backup, /metrics also in health router)
@app.get("/metrics")
async def get_metrics():
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format.
    """
    data = generate_latest(metrics.registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
