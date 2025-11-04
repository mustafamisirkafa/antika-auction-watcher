"""
Observability Middleware (Sprint 3)

Integrates Prometheus metrics, structured logging, and tracing
into FastAPI request handling.

Features:
- Automatic HTTP request metrics
- Request/response logging
- Trace ID injection and propagation
- Latency tracking
- Error logging with context

Usage:
    from backend.middleware.observability import ObservabilityMiddleware
    
    app.add_middleware(ObservabilityMiddleware)
"""

import time
import uuid
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.core.metrics import metrics
from backend.core.logging_json import (
    add_context,
    clear_context,
    log_request_start,
    log_request_end,
    get_logger
)

logger = get_logger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware for observability (metrics, logging, tracing).
    
    Automatically:
    - Records HTTP request metrics
    - Logs requests and responses
    - Injects trace IDs
    - Tracks request latency
    - Enriches logs with context
    """
    
    def __init__(
        self,
        app: ASGIApp,
        log_requests: bool = True,
        include_request_body: bool = False,
        include_response_body: bool = False
    ):
        """
        Initialize observability middleware.
        
        Args:
            app: ASGI application
            log_requests: Enable request/response logging
            include_request_body: Log request body (caution: sensitive data)
            include_response_body: Log response body (caution: large payloads)
        """
        super().__init__(app)
        self.log_requests = log_requests
        self.include_request_body = include_request_body
        self.include_response_body = include_response_body
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with observability instrumentation.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
        
        Returns:
            Response
        """
        # Generate or extract trace ID
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        
        # Extract user ID (if authenticated)
        user_id = None
        if hasattr(request.state, "user_id"):
            user_id = request.state.user_id
        
        # Normalize route pattern (remove path params)
        route_pattern = self._get_route_pattern(request)
        
        # Add context for logging
        add_context(
            trace_id=trace_id,
            path=str(request.url.path),
            method=request.method,
            user_id=user_id,
            client_ip=request.client.host if request.client else "unknown"
        )
        
        # Track request in progress
        metrics.http_requests_in_progress.labels(
            method=request.method,
            route=route_pattern
        ).inc()
        
        # Start timer
        start_time = time.perf_counter()
        
        # Log request start
        if self.log_requests:
            log_request_start(
                logger,
                method=request.method,
                path=str(request.url.path),
                trace_id=trace_id,
                user_id=user_id,
                query_params=dict(request.query_params) if request.query_params else None
            )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate latency
            latency_seconds = time.perf_counter() - start_time
            latency_ms = latency_seconds * 1000
            
            # Record metrics
            metrics.record_http_request(
                method=request.method,
                route=route_pattern,
                status_code=response.status_code,
                duration_seconds=latency_seconds
            )
            
            # Log request completion
            if self.log_requests:
                log_request_end(
                    logger,
                    method=request.method,
                    path=str(request.url.path),
                    status_code=response.status_code,
                    latency_ms=latency_ms
                )
            
            # Inject trace ID into response headers
            response.headers["X-Trace-ID"] = trace_id
            
            return response
        
        except Exception as e:
            # Calculate latency for failed request
            latency_seconds = time.perf_counter() - start_time
            latency_ms = latency_seconds * 1000
            
            # Record error metrics
            metrics.record_http_request(
                method=request.method,
                route=route_pattern,
                status_code=500,
                duration_seconds=latency_seconds
            )
            
            # Log error
            logger.error(
                "Request failed",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "latency_ms": round(latency_ms, 2)
                },
                exc_info=True
            )
            
            raise
        
        finally:
            # Decrement in-progress counter
            metrics.http_requests_in_progress.labels(
                method=request.method,
                route=route_pattern
            ).dec()
            
            # Clear logging context
            clear_context()
    
    def _get_route_pattern(self, request: Request) -> str:
        """
        Get route pattern from request.
        
        Extracts the route pattern (e.g., /api/users/{id})
        instead of the actual path (e.g., /api/users/123).
        
        Args:
            request: FastAPI request
        
        Returns:
            Route pattern string
        """
        if hasattr(request, "scope") and "route" in request.scope:
            route = request.scope["route"]
            if hasattr(route, "path"):
                return route.path
        
        # Fallback: use actual path
        return str(request.url.path)


# Trace ID utilities

def get_trace_id(request: Request) -> str:
    """
    Get trace ID from request.
    
    Args:
        request: FastAPI request
    
    Returns:
        Trace ID string
    """
    return request.headers.get("X-Trace-ID") or str(uuid.uuid4())


def inject_trace_id(request: Request) -> str:
    """
    Inject trace ID into request state.
    
    Args:
        request: FastAPI request
    
    Returns:
        Trace ID
    """
    trace_id = get_trace_id(request)
    request.state.trace_id = trace_id
    add_context(trace_id=trace_id)
    return trace_id


# Metrics recording helpers

async def record_autobid_metrics(
    auction_id: str,
    duration_seconds: float,
    result: str,
    category: str = "unknown"
):
    """
    Record AutoBid execution metrics.
    
    Args:
        auction_id: Auction ID
        duration_seconds: Execution duration
        result: Result status (success, denied, failed)
        category: Item category
    """
    metrics.record_autobid_execution(auction_id, duration_seconds, result)
    
    if result == "success":
        metrics.record_bid_placed("success", category)
    elif result == "denied":
        metrics.record_bid_placed("denied", category)
    else:
        metrics.record_bid_placed("failed", category)


async def record_valuation_metrics(
    category: str,
    duration_seconds: float,
    confidence: float
):
    """
    Record valuation processing metrics.
    
    Args:
        category: Item category
        duration_seconds: Processing duration
        confidence: Confidence score (0-1)
    """
    metrics.record_valuation(category, duration_seconds, confidence)


# WebSocket metrics

class WebSocketMetrics:
    """Helper for tracking WebSocket metrics."""
    
    @staticmethod
    def on_connect():
        """Record WebSocket connection."""
        metrics.websocket_connections.inc()
    
    @staticmethod
    def on_disconnect():
        """Record WebSocket disconnection."""
        metrics.websocket_connections.dec()
    
    @staticmethod
    def on_message_sent(event_type: str):
        """Record WebSocket message sent."""
        metrics.websocket_messages_sent.labels(event_type=event_type).inc()


# Example usage in route
"""
@router.post("/bid")
async def create_bid(request: Request, bid_data: BidCreate):
    trace_id = get_trace_id(request)
    
    # Log with context
    logger.info("Processing bid", item_id=bid_data.item_id)
    
    # Time operation
    start = time.perf_counter()
    result = await place_bid(bid_data)
    duration = time.perf_counter() - start
    
    # Record metrics
    await record_autobid_metrics(
        auction_id=bid_data.auction_id,
        duration_seconds=duration,
        result="success",
        category=bid_data.category
    )
    
    return result
"""
