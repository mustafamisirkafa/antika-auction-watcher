"""
Analytics API Router (Phase 17)
Provides aggregated system metrics for monitoring dashboard.
"""
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, func
import json

from backend.db.database import get_db
from backend.core.auth import get_current_user
from backend.middleware.team_context import get_redis
from backend.models.bid_rules import AutoBidAudit
from backend.models.user_prefs import UserPreference
from backend.services.seller_profile import SellerProfile
from backend.core.i18n import tr_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

# Cache TTL for analytics data
ANALYTICS_CACHE_TTL = 15  # seconds


async def get_autobid_metrics(db: Session, redis) -> Dict[str, Any]:
    """
    Get AutoBid Engine metrics.
    
    Returns:
        - active_bids: Count of active AutoBid sessions
        - sla_p95: 95th percentile latency (ms)
        - last_bid_ms: Last bid latency (ms)
    """
    try:
        # Count active bids from Redis
        active_keys = await redis.keys("lock:autobid:*")
        active_bids = len(active_keys) if active_keys else 0
        
        # Get recent bid latencies from audit log (last hour)
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        stmt = select(AutoBidAudit.decision_latency_ms).where(
            AutoBidAudit.created_at >= one_hour_ago,
            AutoBidAudit.decision_latency_ms.isnot(None)
        ).order_by(AutoBidAudit.created_at.desc()).limit(100)
        
        result = db.exec(stmt)
        latencies = [row for row in result.all() if row is not None]
        
        # Calculate p95
        sla_p95 = 0.0
        last_bid_ms = 0.0
        
        if latencies:
            sorted_latencies = sorted(latencies)
            p95_index = int(len(sorted_latencies) * 0.95)
            sla_p95 = sorted_latencies[p95_index] if p95_index < len(sorted_latencies) else sorted_latencies[-1]
            last_bid_ms = latencies[0] if latencies else 0.0
        
        return {
            "active_bids": active_bids,
            "sla_p95": round(sla_p95 / 1000, 2),  # Convert to seconds
            "last_bid_ms": int(last_bid_ms)
        }
    except Exception as e:
        logger.error(f"Error fetching AutoBid metrics: {e}")
        return {"active_bids": 0, "sla_p95": 0.0, "last_bid_ms": 0}


async def get_valuation_metrics(redis) -> Dict[str, Any]:
    """
    Get Valuation Feed metrics.
    
    Returns:
        - avg_market_value: Average market value across cached items
        - trend_delta: Average trend change
        - demand_score: Average demand score
    """
    try:
        # Get valuation cache keys
        keys = await redis.keys("valuation:cache:*")
        
        if not keys:
            return {
                "avg_market_value": 0,
                "trend_delta": 0.0,
                "demand_score": 0.0
            }
        
        # Sample up to 50 items for performance
        sample_keys = keys[:50] if len(keys) > 50 else keys
        
        total_value = 0
        total_trend = 0.0
        total_demand = 0.0
        count = 0
        
        for key in sample_keys:
            try:
                data = await redis.get(key)
                if data:
                    val_data = json.loads(data)
                    total_value += val_data.get("market_value", 0)
                    total_trend += val_data.get("trend_delta", 0)
                    total_demand += val_data.get("demand_score", 0)
                    count += 1
            except:
                continue
        
        if count == 0:
            return {
                "avg_market_value": 0,
                "trend_delta": 0.0,
                "demand_score": 0.0
            }
        
        return {
            "avg_market_value": int(total_value / count),
            "trend_delta": round(total_trend / count, 2),
            "demand_score": round(total_demand / count, 2)
        }
    except Exception as e:
        logger.error(f"Error fetching valuation metrics: {e}")
        return {
            "avg_market_value": 0,
            "trend_delta": 0.0,
            "demand_score": 0.0
        }


async def get_seller_trust_metrics(db: Session) -> Dict[str, int]:
    """
    Get Seller Trust distribution.
    
    Returns:
        - trusted: Count of high-trust sellers (trust >= 0.7)
        - medium: Count of medium-trust sellers (0.4 <= trust < 0.7)
        - risky: Count of low-trust sellers (trust < 0.4)
    """
    try:
        # Query seller profiles
        stmt = select(SellerProfile.trust_score).where(
            SellerProfile.trust_score.isnot(None)
        )
        
        result = db.exec(stmt)
        trust_scores = result.all()
        
        trusted = sum(1 for score in trust_scores if score >= 0.7)
        medium = sum(1 for score in trust_scores if 0.4 <= score < 0.7)
        risky = sum(1 for score in trust_scores if score < 0.4)
        
        return {
            "trusted": trusted,
            "medium": medium,
            "risky": risky
        }
    except Exception as e:
        logger.error(f"Error fetching seller trust metrics: {e}")
        return {"trusted": 0, "medium": 0, "risky": 0}


async def get_user_prefs_metrics(db: Session) -> Dict[str, int]:
    """
    Get User Preferences metrics.
    
    Returns:
        - allowlist: Total allowlist entries across all users
        - blocklist: Total blocklist entries across all users
    """
    try:
        stmt = select(UserPreference)
        result = db.exec(stmt)
        prefs = result.all()
        
        total_allowlist = 0
        total_blocklist = 0
        
        for pref in prefs:
            if pref.allowlist:
                total_allowlist += len(pref.allowlist)
            if pref.blocklist:
                total_blocklist += len(pref.blocklist)
        
        return {
            "allowlist": total_allowlist,
            "blocklist": total_blocklist
        }
    except Exception as e:
        logger.error(f"Error fetching user preferences metrics: {e}")
        return {"allowlist": 0, "blocklist": 0}


async def get_system_health_metrics(redis, db: Session) -> Dict[str, Any]:
    """
    Get System Health metrics.
    
    Returns:
        - redis_latency_ms: Redis ping latency
        - cache_hit_ratio: Estimated cache hit ratio
        - db_latency_ms: Database query latency
    """
    try:
        # Measure Redis latency
        start = datetime.utcnow()
        await redis.ping()
        redis_latency = (datetime.utcnow() - start).total_seconds() * 1000
        
        # Estimate cache hit ratio from Redis stats
        # This is a simplified estimation
        cache_hit_ratio = 0.94  # Default estimation
        try:
            info = await redis.info("stats")
            hits = info.get("keyspace_hits", 0)
            misses = info.get("keyspace_misses", 0)
            if hits + misses > 0:
                cache_hit_ratio = hits / (hits + misses)
        except:
            pass
        
        # Measure DB latency with simple query
        start = datetime.utcnow()
        db.exec(select(func.count()).select_from(UserPreference))
        db_latency = (datetime.utcnow() - start).total_seconds() * 1000
        
        return {
            "redis_latency_ms": int(redis_latency),
            "cache_hit_ratio": round(cache_hit_ratio, 2),
            "db_latency_ms": int(db_latency)
        }
    except Exception as e:
        logger.error(f"Error fetching system health metrics: {e}")
        return {
            "redis_latency_ms": 0,
            "cache_hit_ratio": 0.0,
            "db_latency_ms": 0
        }


@router.get("/overview")
async def get_analytics_overview(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
    redis = Depends(get_redis)
):
    """
    Get aggregated analytics overview.
    
    **Performance Target:** <150ms
    
    **Data Sources:**
    - AutoBid Engine (active bids, SLA, latency)
    - Valuation Cache (market value, trends, demand)
    - Seller Profiles (trust distribution)
    - User Preferences (allowlist/blocklist counts)
    - System Health (Redis, DB latency, cache hit ratio)
    
    **Caching:**
    - 15-second Redis cache TTL
    - Cache key: `analytics:overview`
    
    **Response:**
    ```json
    {
      "autobid": {
        "active_bids": 12,
        "sla_p95": 2.8,
        "last_bid_ms": 2450
      },
      "valuation": {
        "avg_market_value": 3180,
        "trend_delta": 0.07,
        "demand_score": 0.82
      },
      "sellers": {
        "trusted": 35,
        "medium": 12,
        "risky": 4
      },
      "user_prefs": {
        "allowlist": 5,
        "blocklist": 2
      },
      "system": {
        "redis_latency_ms": 4,
        "cache_hit_ratio": 0.94,
        "db_latency_ms": 18
      },
      "timestamp": "2025-11-03T14:30:00Z"
    }
    ```
    """
    start_time = datetime.utcnow()
    
    try:
        # Check cache first
        cache_key = "analytics:overview"
        cached = await redis.get(cache_key)
        
        if cached:
            logger.debug("Analytics overview served from cache")
            return json.loads(cached)
        
        # Fetch all metrics concurrently
        autobid_task = get_autobid_metrics(db, redis)
        valuation_task = get_valuation_metrics(redis)
        sellers_task = get_seller_trust_metrics(db)
        user_prefs_task = get_user_prefs_metrics(db)
        system_task = get_system_health_metrics(redis, db)
        
        results = await asyncio.gather(
            autobid_task,
            valuation_task,
            sellers_task,
            user_prefs_task,
            system_task,
            return_exceptions=True
        )
        
        # Handle any exceptions
        autobid_metrics = results[0] if not isinstance(results[0], Exception) else {"active_bids": 0, "sla_p95": 0.0, "last_bid_ms": 0}
        valuation_metrics = results[1] if not isinstance(results[1], Exception) else {"avg_market_value": 0, "trend_delta": 0.0, "demand_score": 0.0}
        sellers_metrics = results[2] if not isinstance(results[2], Exception) else {"trusted": 0, "medium": 0, "risky": 0}
        user_prefs_metrics = results[3] if not isinstance(results[3], Exception) else {"allowlist": 0, "blocklist": 0}
        system_metrics = results[4] if not isinstance(results[4], Exception) else {"redis_latency_ms": 0, "cache_hit_ratio": 0.0, "db_latency_ms": 0}
        
        response = {
            "autobid": autobid_metrics,
            "valuation": valuation_metrics,
            "sellers": sellers_metrics,
            "user_prefs": user_prefs_metrics,
            "system": system_metrics,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Cache for 15 seconds
        await redis.setex(
            cache_key,
            ANALYTICS_CACHE_TTL,
            json.dumps(response)
        )
        
        elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.info(f"Analytics overview generated in {elapsed:.0f}ms")
        
        return response
        
    except Exception as e:
        logger.error(f"Error generating analytics overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=tr_error("server_error")
        )
