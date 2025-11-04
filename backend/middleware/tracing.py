"""
Distributed Tracing with OpenTelemetry (Sprint 3)

Instruments the application for distributed tracing with Jaeger.

Features:
- Automatic span creation for HTTP requests
- Manual span annotation for critical operations
- Trace context propagation
- Integration with logging (trace_id injection)
- Support for async operations

Usage:
    from backend.middleware.tracing import init_tracing, trace_operation
    
    # Initialize once at startup
    init_tracing(service_name="antika-auction-watcher")
    
    # Trace async operations
    @trace_operation("valuation")
    async def calculate_valuation(item_id):
        ...
"""

import logging
from typing import Callable, Optional
from functools import wraps
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.trace import Status, StatusCode, SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)

# Global tracer
_tracer: Optional[trace.Tracer] = None


def init_tracing(
    service_name: str = "antika-auction-watcher",
    jaeger_host: str = "localhost",
    jaeger_port: int = 6831,
    environment: str = "development",
    enabled: bool = True
):
    """
    Initialize OpenTelemetry tracing with Jaeger.
    
    Args:
        service_name: Service name for traces
        jaeger_host: Jaeger agent host
        jaeger_port: Jaeger agent port
        environment: Environment name (dev, staging, production)
        enabled: Enable tracing (disable for development if needed)
    
    Example:
        from backend.middleware.tracing import init_tracing
        
        init_tracing(
            service_name="antika-auction-watcher",
            jaeger_host="jaeger",
            jaeger_port=6831,
            environment="production"
        )
    """
    global _tracer
    
    if not enabled:
        logger.info("??  Tracing disabled")
        return
    
    try:
        # Create resource with service name
        resource = Resource.create({
            SERVICE_NAME: service_name,
            "environment": environment,
            "version": "1.0.0"
        })
        
        # Create tracer provider
        provider = TracerProvider(resource=resource)
        
        # Create Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=jaeger_host,
            agent_port=jaeger_port,
        )
        
        # Add span processor
        span_processor = BatchSpanProcessor(jaeger_exporter)
        provider.add_span_processor(span_processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(provider)
        
        # Get tracer
        _tracer = trace.get_tracer(__name__)
        
        # Instrument libraries
        HTTPXClientInstrumentor().instrument()
        RedisInstrumentor().instrument()
        
        logger.info(
            f"? OpenTelemetry tracing initialized: service={service_name}, "
            f"jaeger={jaeger_host}:{jaeger_port}"
        )
    
    except Exception as e:
        logger.error(f"? Failed to initialize tracing: {e}", exc_info=True)


def instrument_fastapi(app):
    """
    Instrument FastAPI app for tracing.
    
    Args:
        app: FastAPI application
    
    Example:
        from fastapi import FastAPI
        from backend.middleware.tracing import instrument_fastapi
        
        app = FastAPI()
        instrument_fastapi(app)
    """
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("? FastAPI instrumented for tracing")
    except Exception as e:
        logger.error(f"? Failed to instrument FastAPI: {e}")


def instrument_sqlalchemy(engine):
    """
    Instrument SQLAlchemy engine for tracing.
    
    Args:
        engine: SQLAlchemy engine
    
    Example:
        from sqlalchemy import create_engine
        from backend.middleware.tracing import instrument_sqlalchemy
        
        engine = create_engine("postgresql://...")
        instrument_sqlalchemy(engine)
    """
    try:
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("? SQLAlchemy instrumented for tracing")
    except Exception as e:
        logger.error(f"? Failed to instrument SQLAlchemy: {e}")


def get_tracer() -> trace.Tracer:
    """
    Get global tracer instance.
    
    Returns:
        Tracer instance
    """
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer(__name__)
    return _tracer


@contextmanager
def trace_span(
    name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[dict] = None
):
    """
    Context manager for creating a trace span.
    
    Args:
        name: Span name
        kind: Span kind (INTERNAL, CLIENT, SERVER, PRODUCER, CONSUMER)
        attributes: Span attributes
    
    Usage:
        with trace_span("fetch_valuation", attributes={"item_id": 123}):
            result = await fetch_valuation(123)
    """
    tracer = get_tracer()
    
    with tracer.start_as_current_span(name, kind=kind) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
        
        try:
            yield span
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise


def trace_operation(operation_name: str, span_kind: SpanKind = SpanKind.INTERNAL):
    """
    Decorator to trace a function/method.
    
    Args:
        operation_name: Name for the span
        span_kind: Span kind
    
    Usage:
        @trace_operation("calculate_valuation")
        async def calculate_valuation(item_id):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with trace_span(operation_name, kind=span_kind):
                return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with trace_span(operation_name, kind=span_kind):
                return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def add_span_attributes(**attributes):
    """
    Add attributes to current span.
    
    Args:
        **attributes: Key-value pairs to add
    
    Usage:
        add_span_attributes(user_id=123, item_id=456)
    """
    current_span = trace.get_current_span()
    if current_span:
        for key, value in attributes.items():
            current_span.set_attribute(key, str(value))


def add_span_event(name: str, attributes: Optional[dict] = None):
    """
    Add an event to current span.
    
    Args:
        name: Event name
        attributes: Event attributes
    
    Usage:
        add_span_event("cache_miss", {"key": "valuation:123"})
    """
    current_span = trace.get_current_span()
    if current_span:
        current_span.add_event(name, attributes=attributes or {})


def get_trace_id() -> str:
    """
    Get current trace ID.
    
    Returns:
        Trace ID string (hex format)
    """
    current_span = trace.get_current_span()
    if current_span:
        span_context = current_span.get_span_context()
        if span_context and span_context.is_valid:
            return format(span_context.trace_id, '032x')
    return ""


def inject_trace_context() -> dict:
    """
    Inject trace context into a dictionary.
    
    Useful for propagating context to external services.
    
    Returns:
        Dictionary with trace context headers
    
    Usage:
        headers = inject_trace_context()
        response = httpx.get(url, headers=headers)
    """
    carrier = {}
    TraceContextTextMapPropagator().inject(carrier)
    return carrier


# AutoBid tracing helpers

class AutoBidTracer:
    """
    Helper class for tracing AutoBid operations.
    
    Usage:
        tracer = AutoBidTracer(auction_id="A1", item_id="I1")
        
        with tracer.fetch_valuation():
            valuation = await get_valuation()
        
        with tracer.policy_decision():
            decision = await evaluate_policy()
        
        with tracer.bid_dispatch():
            result = await dispatch_bid()
    """
    
    def __init__(self, auction_id: str, item_id: str):
        """
        Initialize AutoBid tracer.
        
        Args:
            auction_id: Auction ID
            item_id: Item ID
        """
        self.auction_id = auction_id
        self.item_id = item_id
        self.base_attributes = {
            "auction_id": auction_id,
            "item_id": item_id
        }
    
    @contextmanager
    def fetch_valuation(self):
        """Trace valuation fetching."""
        with trace_span("autobid.fetch_valuation", attributes=self.base_attributes) as span:
            yield span
    
    @contextmanager
    def policy_decision(self):
        """Trace policy decision."""
        with trace_span("autobid.policy_decision", attributes=self.base_attributes) as span:
            yield span
    
    @contextmanager
    def bid_dispatch(self):
        """Trace bid dispatching."""
        with trace_span("autobid.bid_dispatch", attributes=self.base_attributes, kind=SpanKind.CLIENT) as span:
            yield span
    
    @contextmanager
    def cache_lookup(self, cache_key: str):
        """Trace cache lookup."""
        attributes = {**self.base_attributes, "cache_key": cache_key}
        with trace_span("autobid.cache_lookup", attributes=attributes) as span:
            yield span


# Database tracing helpers

@contextmanager
def trace_db_query(operation: str, table: str):
    """
    Trace database query.
    
    Args:
        operation: SQL operation (SELECT, INSERT, UPDATE, DELETE)
        table: Table name
    
    Usage:
        with trace_db_query("SELECT", "users"):
            user = db.query(User).filter_by(id=123).first()
    """
    attributes = {
        "db.operation": operation,
        "db.table": table
    }
    with trace_span(f"db.{operation.lower()}", kind=SpanKind.CLIENT, attributes=attributes) as span:
        yield span


# Redis tracing helpers

@contextmanager
def trace_redis_operation(operation: str, key: Optional[str] = None):
    """
    Trace Redis operation.
    
    Args:
        operation: Redis command (GET, SET, DEL, etc.)
        key: Redis key (optional)
    
    Usage:
        with trace_redis_operation("GET", "valuation:123"):
            value = await redis.get("valuation:123")
    """
    attributes = {"redis.operation": operation}
    if key:
        attributes["redis.key"] = key
    
    with trace_span(f"redis.{operation.lower()}", kind=SpanKind.CLIENT, attributes=attributes) as span:
        yield span


# HTTP client tracing helpers

@contextmanager
def trace_http_request(method: str, url: str):
    """
    Trace HTTP request to external service.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
    
    Usage:
        with trace_http_request("GET", "https://api.ebay.com/..."):
            response = await httpx.get(url)
    """
    attributes = {
        "http.method": method,
        "http.url": url
    }
    with trace_span(f"http.{method.lower()}", kind=SpanKind.CLIENT, attributes=attributes) as span:
        yield span


# Example usage in AutoBid flow
"""
async def execute_autobid(auction_id: str, item_id: str):
    tracer = AutoBidTracer(auction_id, item_id)
    
    # Fetch valuation
    with tracer.fetch_valuation():
        add_span_event("cache_check")
        valuation = await get_cached_valuation(item_id)
        
        if not valuation:
            add_span_event("cache_miss")
            valuation = await calculate_valuation(item_id)
    
    # Policy decision
    with tracer.policy_decision():
        add_span_attributes(confidence=valuation.confidence)
        decision = await evaluate_policy(valuation)
    
    # Dispatch bid
    if decision.ok:
        with tracer.bid_dispatch():
            result = await dispatch_bid(auction_id, decision.amount)
            add_span_attributes(bid_result=result.status)
    
    return result
"""
