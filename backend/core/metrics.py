"""
Prometheus Metrics Module (Sprint 3)

Exposes application metrics for Prometheus scraping.

Metrics:
- autobid_latency_seconds: AutoBid end-to-end latency histogram
- bids_placed_total: Total bids placed counter
- active_auctions: Current active auction count
- http_request_duration_seconds: HTTP request latency histogram
- redis_cache_hit_ratio: Redis cache hit ratio gauge
- db_connections_active: Active database connections
- valuation_processing_seconds: Valuation calculation time
- websocket_connections_active: Active WebSocket connections

Usage:
    from backend.core.metrics import metrics
    
    # Record AutoBid latency
    with metrics.autobid_latency.time():
        execute_autobid()
    
    # Increment bid counter
    metrics.bids_placed.labels(status="success", category="ceramics").inc()
"""

import logging
import time
from typing import Optional
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

logger = logging.getLogger(__name__)


class ApplicationMetrics:
    """
    Central metrics registry for the application.
    
    All metrics are registered here and can be accessed
    via the global `metrics` instance.
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize application metrics.
        
        Args:
            registry: Prometheus registry (default: global registry)
        """
        self.registry = registry
        
        # AutoBid metrics
        self.autobid_latency = Histogram(
            name="autobid_latency_seconds",
            documentation="AutoBid end-to-end processing latency",
            labelnames=["auction_id", "result"],
            buckets=(0.5, 1.0, 2.0, 3.0, 5.0, 10.0),
            registry=registry
        )
        
        self.bids_placed = Counter(
            name="bids_placed_total",
            documentation="Total number of bids placed",
            labelnames=["status", "category"],
            registry=registry
        )
        
        self.active_auctions = Gauge(
            name="active_auctions",
            documentation="Number of currently active auctions",
            registry=registry
        )
        
        # HTTP request metrics
        self.http_request_duration = Histogram(
            name="http_request_duration_seconds",
            documentation="HTTP request latency",
            labelnames=["method", "route", "status_code"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=registry
        )
        
        self.http_requests_total = Counter(
            name="http_requests_total",
            documentation="Total HTTP requests",
            labelnames=["method", "route", "status_code"],
            registry=registry
        )
        
        self.http_requests_in_progress = Gauge(
            name="http_requests_in_progress",
            documentation="HTTP requests currently in progress",
            labelnames=["method", "route"],
            registry=registry
        )
        
        # Redis metrics
        self.redis_cache_hit_ratio = Gauge(
            name="redis_cache_hit_ratio",
            documentation="Redis cache hit ratio (0-1)",
            registry=registry
        )
        
        self.redis_cache_hits = Counter(
            name="redis_cache_hits_total",
            documentation="Total Redis cache hits",
            registry=registry
        )
        
        self.redis_cache_misses = Counter(
            name="redis_cache_misses_total",
            documentation="Total Redis cache misses",
            registry=registry
        )
        
        self.redis_operation_duration = Histogram(
            name="redis_operation_duration_seconds",
            documentation="Redis operation latency",
            labelnames=["operation"],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25),
            registry=registry
        )
        
        # Database metrics
        self.db_connections_active = Gauge(
            name="db_connections_active",
            documentation="Active database connections",
            registry=registry
        )
        
        self.db_query_duration = Histogram(
            name="db_query_duration_seconds",
            documentation="Database query execution time",
            labelnames=["operation"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
            registry=registry
        )
        
        self.db_queries_total = Counter(
            name="db_queries_total",
            documentation="Total database queries",
            labelnames=["operation", "status"],
            registry=registry
        )
        
        # Valuation metrics
        self.valuation_processing = Histogram(
            name="valuation_processing_seconds",
            documentation="Valuation calculation time",
            labelnames=["category"],
            buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
            registry=registry
        )
        
        self.valuations_total = Counter(
            name="valuations_total",
            documentation="Total valuations performed",
            labelnames=["category", "confidence_level"],
            registry=registry
        )
        
        # WebSocket metrics
        self.websocket_connections = Gauge(
            name="websocket_connections_active",
            documentation="Active WebSocket connections",
            registry=registry
        )
        
        self.websocket_messages_sent = Counter(
            name="websocket_messages_sent_total",
            documentation="Total WebSocket messages sent",
            labelnames=["event_type"],
            registry=registry
        )
        
        # Market feed metrics
        self.market_feed_updates = Counter(
            name="market_feed_updates_total",
            documentation="Total market feed updates received",
            labelnames=["source"],
            registry=registry
        )
        
        self.market_feed_errors = Counter(
            name="market_feed_errors_total",
            documentation="Total market feed errors",
            labelnames=["source", "error_type"],
            registry=registry
        )
        
        # Seller intelligence metrics
        self.seller_profiles_updated = Counter(
            name="seller_profiles_updated_total",
            documentation="Total seller profiles updated",
            registry=registry
        )
        
        self.seller_trust_score = Summary(
            name="seller_trust_score",
            documentation="Seller trust score distribution",
            registry=registry
        )
        
        # User preferences metrics
        self.user_prefs_updates = Counter(
            name="user_prefs_updates_total",
            documentation="Total user preference updates",
            labelnames=["action", "list_type"],
            registry=registry
        )
        
        # Circuit breaker metrics (Sprint 1)
        self.circuit_breaker_state = Gauge(
            name="circuit_breaker_state",
            documentation="Circuit breaker state (0=closed, 1=open, 2=half_open)",
            labelnames=["breaker_name"],
            registry=registry
        )
        
        self.circuit_breaker_failures = Counter(
            name="circuit_breaker_failures_total",
            documentation="Total circuit breaker failures",
            labelnames=["breaker_name"],
            registry=registry
        )
        
        # Rate limiting metrics (Sprint 2)
        self.rate_limit_exceeded = Counter(
            name="rate_limit_exceeded_total",
            documentation="Total rate limit exceeded events",
            labelnames=["endpoint", "identifier_type"],
            registry=registry
        )
        
        # System metrics
        self.info = Gauge(
            name="app_info",
            documentation="Application information",
            labelnames=["version", "environment"],
            registry=registry
        )
        
        logger.info("? Prometheus metrics initialized")
    
    def update_cache_hit_ratio(self, hits: int, total: int):
        """
        Update Redis cache hit ratio.
        
        Args:
            hits: Number of cache hits
            total: Total cache operations
        """
        if total > 0:
            ratio = hits / total
            self.redis_cache_hit_ratio.set(ratio)
    
    def record_autobid_execution(
        self,
        auction_id: str,
        duration_seconds: float,
        result: str
    ):
        """
        Record AutoBid execution metrics.
        
        Args:
            auction_id: Auction identifier
            duration_seconds: Execution duration
            result: Result status (success, failed, denied)
        """
        self.autobid_latency.labels(
            auction_id=auction_id,
            result=result
        ).observe(duration_seconds)
    
    def record_bid_placed(self, status: str, category: str):
        """
        Record a bid placement.
        
        Args:
            status: Bid status (success, failed, rejected)
            category: Item category
        """
        self.bids_placed.labels(status=status, category=category).inc()
    
    def record_http_request(
        self,
        method: str,
        route: str,
        status_code: int,
        duration_seconds: float
    ):
        """
        Record HTTP request metrics.
        
        Args:
            method: HTTP method
            route: Route pattern
            status_code: HTTP status code
            duration_seconds: Request duration
        """
        self.http_request_duration.labels(
            method=method,
            route=route,
            status_code=status_code
        ).observe(duration_seconds)
        
        self.http_requests_total.labels(
            method=method,
            route=route,
            status_code=status_code
        ).inc()
    
    def record_valuation(
        self,
        category: str,
        duration_seconds: float,
        confidence: float
    ):
        """
        Record valuation metrics.
        
        Args:
            category: Item category
            duration_seconds: Processing time
            confidence: Confidence score (0-1)
        """
        self.valuation_processing.labels(category=category).observe(duration_seconds)
        
        # Classify confidence level
        if confidence >= 0.8:
            confidence_level = "high"
        elif confidence >= 0.6:
            confidence_level = "medium"
        else:
            confidence_level = "low"
        
        self.valuations_total.labels(
            category=category,
            confidence_level=confidence_level
        ).inc()
    
    def set_app_info(self, version: str, environment: str):
        """
        Set application info metric.
        
        Args:
            version: Application version
            environment: Environment name (dev, staging, production)
        """
        self.info.labels(version=version, environment=environment).set(1)
    
    def export_metrics(self) -> tuple[bytes, str]:
        """
        Export metrics in Prometheus format.
        
        Returns:
            Tuple of (metrics_data, content_type)
        """
        return generate_latest(self.registry), CONTENT_TYPE_LATEST


# Global metrics instance
metrics = ApplicationMetrics()


# Metric helpers

class MetricsTimer:
    """
    Context manager for timing operations.
    
    Usage:
        with MetricsTimer(metrics.valuation_processing.labels(category="coins")):
            calculate_valuation()
    """
    
    def __init__(self, observer):
        """
        Initialize timer.
        
        Args:
            observer: Prometheus observer (Histogram or Summary)
        """
        self.observer = observer
        self.start_time = None
    
    def __enter__(self):
        """Start timer."""
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer and record metric."""
        if self.start_time:
            duration = time.perf_counter() - self.start_time
            self.observer.observe(duration)
        return False


def track_cache_operation(operation: str):
    """
    Decorator to track Redis cache operations.
    
    Usage:
        @track_cache_operation("get")
        async def get_from_cache(key):
            ...
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = await func(*args, **kwargs)
            duration = time.perf_counter() - start
            
            metrics.redis_operation_duration.labels(operation=operation).observe(duration)
            
            # Track hits/misses for get operations
            if operation == "get":
                if result is not None:
                    metrics.redis_cache_hits.inc()
                else:
                    metrics.redis_cache_misses.inc()
            
            return result
        return wrapper
    return decorator


def track_db_query(operation: str):
    """
    Decorator to track database queries.
    
    Usage:
        @track_db_query("select")
        def get_user(user_id):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start
                
                metrics.db_query_duration.labels(operation=operation).observe(duration)
                metrics.db_queries_total.labels(operation=operation, status="success").inc()
                
                return result
            except Exception as e:
                duration = time.perf_counter() - start
                metrics.db_query_duration.labels(operation=operation).observe(duration)
                metrics.db_queries_total.labels(operation=operation, status="error").inc()
                raise
        return wrapper
    return decorator


# Initialize app info
def init_metrics(version: str = "1.0.0", environment: str = "development"):
    """
    Initialize metrics with app info.
    
    Args:
        version: Application version
        environment: Environment name
    """
    metrics.set_app_info(version, environment)
    logger.info(f"? Metrics initialized: version={version}, env={environment}")


if __name__ == "__main__":
    # Test metrics
    init_metrics("1.0.0", "test")
    
    # Simulate some metrics
    metrics.bids_placed.labels(status="success", category="ceramics").inc()
    metrics.active_auctions.set(15)
    metrics.autobid_latency.labels(auction_id="A1", result="success").observe(2.5)
    
    # Export
    data, content_type = metrics.export_metrics()
    print(f"Metrics exported ({len(data)} bytes)")
    print(data.decode()[:500])
