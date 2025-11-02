"""Performance monitoring middleware."""
import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from backend.services.analytics.metrics_collector import MetricsCollector


class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Performance monitoring middleware.
    
    Tracks:
    - Request duration
    - Response status codes
    - Slow endpoints
    """

    def __init__(self, app):
        super().__init__(app)
        self.slow_threshold_ms = 1000  # 1 second

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with performance tracking."""
        # Record start time
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Add timing header
        response.headers['X-Response-Time'] = f"{duration_ms:.2f}ms"
        
        # Log slow requests
        if duration_ms > self.slow_threshold_ms:
            # In production, log to metrics system
            print(f"SLOW REQUEST: {request.method} {request.url.path} took {duration_ms:.2f}ms")
        
        # Record metric (in background)
        # In production, this would be async/background task
        # For now, skip to avoid session issues
        
        return response


class DatabasePerformanceMonitor:
    """Monitor database query performance."""

    def __init__(self):
        self.slow_query_threshold_ms = 100
        self.queries: list = []

    def record_query(self, query_type: str, duration_ms: float, rows: int = 0):
        """Record a database query."""
        self.queries.append({
            'type': query_type,
            'duration_ms': duration_ms,
            'rows': rows,
            'timestamp': time.time()
        })
        
        # Log slow queries
        if duration_ms > self.slow_query_threshold_ms:
            print(f"SLOW QUERY: {query_type} took {duration_ms:.2f}ms, {rows} rows")
        
        # Keep only recent queries
        if len(self.queries) > 1000:
            self.queries = self.queries[-1000:]

    def get_slow_queries(self, threshold_ms: Optional[float] = None) -> list:
        """Get slow queries."""
        threshold = threshold_ms or self.slow_query_threshold_ms
        return [q for q in self.queries if q['duration_ms'] > threshold]

    def get_query_stats(self) -> dict:
        """Get query statistics."""
        if not self.queries:
            return {'total': 0}
        
        durations = [q['duration_ms'] for q in self.queries]
        durations.sort()
        
        return {
            'total_queries': len(self.queries),
            'avg_duration_ms': sum(durations) / len(durations),
            'min_duration_ms': min(durations),
            'max_duration_ms': max(durations),
            'p50_duration_ms': durations[len(durations) // 2],
            'p95_duration_ms': durations[int(len(durations) * 0.95)],
            'slow_queries': len(self.get_slow_queries())
        }


# Global monitor instance
db_monitor = DatabasePerformanceMonitor()
