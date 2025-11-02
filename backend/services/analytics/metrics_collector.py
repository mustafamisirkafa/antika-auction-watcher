"""System metrics collection for monitoring and analytics."""
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlmodel import Session, select
from backend.db.analytics_models import SystemMetrics
import time
import asyncio


class MetricsCollector:
    """
    Collect and track system-wide metrics.
    
    Metrics tracked:
    - API response times
    - External API usage
    - Database query performance
    - Cache hit rates
    - Error rates
    """

    def __init__(self, session: Session):
        self.session = session
        self._request_timings: List[float] = []
        self._api_call_counts: Dict[str, int] = {}
        self._cache_stats: Dict[str, int] = {'hits': 0, 'misses': 0}

    async def record_request_time(
        self,
        endpoint: str,
        duration_ms: float,
        status_code: int
    ):
        """Record API request timing."""
        metric = SystemMetrics(
            metric_type='api_response_time',
            metric_name=endpoint,
            value=duration_ms,
            unit='milliseconds',
            metadata={
                'status_code': status_code,
                'endpoint': endpoint
            }
        )
        
        self.session.add(metric)
        self.session.commit()
        
        # Keep in-memory for quick stats
        self._request_timings.append(duration_ms)
        if len(self._request_timings) > 1000:
            self._request_timings = self._request_timings[-1000:]

    async def record_external_api_call(
        self,
        api_name: str,
        success: bool,
        duration_ms: float
    ):
        """Record external API call (eBay, Etsy, Sahibinden)."""
        metric = SystemMetrics(
            metric_type='external_api',
            metric_name=api_name,
            value=duration_ms,
            unit='milliseconds',
            metadata={
                'success': success,
                'api': api_name
            }
        )
        
        self.session.add(metric)
        self.session.commit()
        
        # Track call counts
        self._api_call_counts[api_name] = self._api_call_counts.get(api_name, 0) + 1

    async def record_database_query(
        self,
        query_type: str,
        duration_ms: float,
        rows_affected: int = 0
    ):
        """Record database query performance."""
        metric = SystemMetrics(
            metric_type='database_query',
            metric_name=query_type,
            value=duration_ms,
            unit='milliseconds',
            metadata={
                'query_type': query_type,
                'rows': rows_affected
            }
        )
        
        self.session.add(metric)
        self.session.commit()

    async def record_cache_hit(self, cache_key: str):
        """Record cache hit."""
        self._cache_stats['hits'] += 1
        
        # Periodically persist cache stats
        if (self._cache_stats['hits'] + self._cache_stats['misses']) % 100 == 0:
            await self._persist_cache_stats()

    async def record_cache_miss(self, cache_key: str):
        """Record cache miss."""
        self._cache_stats['misses'] += 1

    async def _persist_cache_stats(self):
        """Persist cache statistics."""
        total = self._cache_stats['hits'] + self._cache_stats['misses']
        if total == 0:
            return
        
        hit_rate = self._cache_stats['hits'] / total
        
        metric = SystemMetrics(
            metric_type='cache_performance',
            metric_name='hit_rate',
            value=hit_rate,
            unit='ratio',
            metadata={
                'hits': self._cache_stats['hits'],
                'misses': self._cache_stats['misses'],
                'total': total
            }
        )
        
        self.session.add(metric)
        self.session.commit()

    async def get_response_time_stats(
        self,
        endpoint: Optional[str] = None,
        hours: int = 24
    ) -> Dict:
        """Get response time statistics."""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        statement = select(SystemMetrics).where(
            SystemMetrics.metric_type == 'api_response_time',
            SystemMetrics.recorded_at >= start_time
        )
        
        if endpoint:
            statement = statement.where(SystemMetrics.metric_name == endpoint)
        
        metrics = self.session.exec(statement).all()
        
        if not metrics:
            return {'status': 'no_data'}
        
        values = [m.value for m in metrics]
        values.sort()
        
        # Calculate percentiles
        p50_idx = len(values) // 2
        p95_idx = int(len(values) * 0.95)
        p99_idx = int(len(values) * 0.99)
        
        return {
            'endpoint': endpoint or 'all',
            'sample_size': len(values),
            'min': min(values),
            'max': max(values),
            'mean': sum(values) / len(values),
            'p50': values[p50_idx],
            'p95': values[p95_idx],
            'p99': values[p99_idx],
            'period_hours': hours
        }

    async def get_external_api_usage(self, hours: int = 24) -> Dict:
        """Get external API usage statistics."""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        statement = select(SystemMetrics).where(
            SystemMetrics.metric_type == 'external_api',
            SystemMetrics.recorded_at >= start_time
        )
        
        metrics = self.session.exec(statement).all()
        
        # Group by API
        api_stats = {}
        for metric in metrics:
            api_name = metric.metadata.get('api', 'unknown')
            
            if api_name not in api_stats:
                api_stats[api_name] = {
                    'total_calls': 0,
                    'successful_calls': 0,
                    'failed_calls': 0,
                    'total_duration_ms': 0
                }
            
            api_stats[api_name]['total_calls'] += 1
            api_stats[api_name]['total_duration_ms'] += metric.value
            
            if metric.metadata.get('success'):
                api_stats[api_name]['successful_calls'] += 1
            else:
                api_stats[api_name]['failed_calls'] += 1
        
        # Calculate averages
        for api_name in api_stats:
            stats = api_stats[api_name]
            stats['average_duration_ms'] = stats['total_duration_ms'] / stats['total_calls']
            stats['success_rate'] = stats['successful_calls'] / stats['total_calls'] if stats['total_calls'] > 0 else 0
        
        return {
            'period_hours': hours,
            'api_usage': api_stats
        }

    async def get_slow_queries(
        self,
        threshold_ms: float = 100,
        hours: int = 24
    ) -> List[Dict]:
        """Get slow database queries."""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        statement = select(SystemMetrics).where(
            SystemMetrics.metric_type == 'database_query',
            SystemMetrics.recorded_at >= start_time,
            SystemMetrics.value >= threshold_ms
        )
        
        metrics = self.session.exec(statement).all()
        
        return [
            {
                'query_type': m.metric_name,
                'duration_ms': m.value,
                'rows': m.metadata.get('rows', 0),
                'timestamp': m.recorded_at.isoformat()
            }
            for m in metrics
        ]

    async def get_cache_performance(self, hours: int = 24) -> Dict:
        """Get cache performance metrics."""
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        statement = select(SystemMetrics).where(
            SystemMetrics.metric_type == 'cache_performance',
            SystemMetrics.recorded_at >= start_time
        )
        
        metrics = self.session.exec(statement).all()
        
        if not metrics:
            # Use in-memory stats
            total = self._cache_stats['hits'] + self._cache_stats['misses']
            if total == 0:
                return {'status': 'no_data'}
            
            return {
                'current_hit_rate': self._cache_stats['hits'] / total,
                'hits': self._cache_stats['hits'],
                'misses': self._cache_stats['misses']
            }
        
        # Calculate average hit rate
        avg_hit_rate = sum(m.value for m in metrics) / len(metrics)
        total_hits = sum(m.metadata.get('hits', 0) for m in metrics)
        total_misses = sum(m.metadata.get('misses', 0) for m in metrics)
        
        return {
            'period_hours': hours,
            'average_hit_rate': avg_hit_rate,
            'total_hits': total_hits,
            'total_misses': total_misses,
            'samples': len(metrics)
        }

    async def get_dashboard_metrics(self) -> Dict:
        """Get comprehensive dashboard metrics."""
        return {
            'response_times': await self.get_response_time_stats(hours=1),
            'external_api_usage': await self.get_external_api_usage(hours=1),
            'cache_performance': await self.get_cache_performance(hours=1),
            'slow_queries_count': len(await self.get_slow_queries(hours=1)),
            'timestamp': datetime.utcnow().isoformat()
        }

    async def cleanup_old_metrics(self, days: int = 30):
        """Clean up metrics older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        statement = select(SystemMetrics).where(
            SystemMetrics.recorded_at < cutoff_date
        )
        
        old_metrics = self.session.exec(statement).all()
        
        for metric in old_metrics:
            self.session.delete(metric)
        
        self.session.commit()
        
        return len(old_metrics)
