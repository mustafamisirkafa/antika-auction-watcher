"""Main FastAPI application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.core.config import settings
from backend.db.database import create_db_and_tables
from backend.realtime.redis_manager import RedisManager
from backend.routers import auth, items, valuations, bids, websocket, admin, advisor, plans, teams, agents, user_prefs, analytics
from backend.middleware.rate_limiter import RateLimiter
from backend.middleware.performance import PerformanceMiddleware

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
    
    yield
    
    # Shutdown
    await redis_manager.disconnect()


app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Phase 2: Performance monitoring middleware
app.add_middleware(PerformanceMiddleware)

# Phase 2: Rate limiting middleware
app.add_middleware(RateLimiter, redis_manager=redis_manager)

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
app.include_router(websocket.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
