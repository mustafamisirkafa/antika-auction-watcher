"""
Structured JSON Logging (Sprint 3)

Provides structured logging in JSON format for Loki ingestion.

Features:
- JSON output with consistent schema
- Trace ID injection for correlation
- Automatic context enrichment (user_id, path, method)
- Integration with Sprint 2 log redaction
- Performance-optimized (async-safe)

Usage:
    from backend.core.logging_json import get_logger, add_context
    
    logger = get_logger(__name__)
    logger.info("User logged in", user_id=123, ip="192.168.1.1")
    
    # Add context for request
    add_context(trace_id="abc123", path="/api/bid")
    logger.info("Processing bid")  # Automatically includes trace_id, path
"""

import logging
import json
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from contextvars import ContextVar
import threading

from backend.core.log_redaction import redact_sensitive_data

# Context variables for request-scoped data
_request_context: ContextVar[Dict[str, Any]] = ContextVar("request_context", default={})


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.
    
    Output format:
    {
        "timestamp": "2025-11-02T15:30:45.123Z",
        "level": "INFO",
        "logger": "backend.services.autobid",
        "message": "Bid placed successfully",
        "trace_id": "abc123",
        "path": "/api/bid",
        "user_id": 123,
        "latency_ms": 150,
        "extra_field": "value"
    }
    """
    
    def __init__(
        self,
        include_trace: bool = True,
        include_location: bool = True,
        redact_sensitive: bool = True
    ):
        """
        Initialize JSON formatter.
        
        Args:
            include_trace: Include stack trace for exceptions
            include_location: Include file/line info
            redact_sensitive: Apply log redaction (Sprint 2)
        """
        super().__init__()
        self.include_trace = include_trace
        self.include_location = include_location
        self.redact_sensitive = redact_sensitive
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
        
        Returns:
            JSON-formatted log string
        """
        # Base log structure
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add location info
        if self.include_location:
            log_data["file"] = record.filename
            log_data["line"] = record.lineno
            log_data["function"] = record.funcName
        
        # Add context from context vars
        try:
            context = _request_context.get()
            if context:
                log_data.update(context)
        except LookupError:
            pass
        
        # Add extra fields from record
        if hasattr(record, "__dict__"):
            extra_fields = {
                key: value
                for key, value in record.__dict__.items()
                if key not in logging.LogRecord.__dict__ and not key.startswith("_")
            }
            log_data.update(extra_fields)
        
        # Add exception info
        if record.exc_info and self.include_trace:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        # Apply redaction (Sprint 2)
        if self.redact_sensitive:
            log_data = redact_sensitive_data(log_data)
        
        # Serialize to JSON
        try:
            return json.dumps(log_data, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as e:
            # Fallback for non-serializable objects
            log_data["serialization_error"] = str(e)
            return json.dumps(
                {k: str(v) for k, v in log_data.items()},
                ensure_ascii=False
            )


class ContextFilter(logging.Filter):
    """
    Logging filter that adds request context to log records.
    
    Enriches logs with trace_id, user_id, path, etc.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add context to log record.
        
        Args:
            record: Log record to enrich
        
        Returns:
            True (always allow record)
        """
        try:
            context = _request_context.get()
            for key, value in context.items():
                setattr(record, key, value)
        except LookupError:
            pass
        
        return True


def setup_json_logging(
    level: str = "INFO",
    include_trace: bool = True,
    redact_sensitive: bool = True
):
    """
    Configure application-wide JSON logging.
    
    This should be called once during application startup.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        include_trace: Include stack traces for exceptions
        redact_sensitive: Apply log redaction
    
    Example:
        from backend.core.logging_json import setup_json_logging
        
        setup_json_logging(level="INFO", redact_sensitive=True)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    root_logger.handlers = []
    
    # Create JSON formatter
    formatter = JSONFormatter(
        include_trace=include_trace,
        include_location=True,
        redact_sensitive=redact_sensitive
    )
    
    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Add context filter
    context_filter = ContextFilter()
    console_handler.addFilter(context_filter)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    logging.info("? JSON structured logging configured", extra={"level": level})


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    
    Example:
        logger = get_logger(__name__)
        logger.info("Processing request", user_id=123)
    """
    return logging.getLogger(name)


def add_context(**kwargs):
    """
    Add key-value pairs to request context.
    
    Context is automatically included in all subsequent log messages
    within the same request.
    
    Args:
        **kwargs: Context key-value pairs
    
    Example:
        add_context(trace_id="abc123", user_id=456, path="/api/bid")
        logger.info("Processing")  # Includes trace_id, user_id, path
    """
    context = _request_context.get()
    context.update(kwargs)
    _request_context.set(context)


def clear_context():
    """
    Clear request context.
    
    Should be called at the end of each request.
    """
    _request_context.set({})


def get_context() -> Dict[str, Any]:
    """
    Get current request context.
    
    Returns:
        Context dictionary
    """
    return _request_context.get().copy()


class LoggingContextManager:
    """
    Context manager for scoped logging context.
    
    Usage:
        with LoggingContextManager(user_id=123, operation="valuation"):
            logger.info("Starting")  # Includes user_id, operation
            # ... do work ...
            logger.info("Complete")  # Still includes user_id, operation
    """
    
    def __init__(self, **kwargs):
        """
        Initialize context manager.
        
        Args:
            **kwargs: Context key-value pairs
        """
        self.context = kwargs
        self.previous_context = None
    
    def __enter__(self):
        """Enter context."""
        self.previous_context = get_context()
        add_context(**self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        clear_context()
        if self.previous_context:
            _request_context.set(self.previous_context)
        return False


# Performance logging utilities

class LatencyLogger:
    """
    Context manager for logging operation latency.
    
    Usage:
        with LatencyLogger(logger, "valuation", category="coins"):
            calculate_valuation()
        # Logs: "valuation completed" with latency_ms and category
    """
    
    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        level: int = logging.INFO,
        **extra_context
    ):
        """
        Initialize latency logger.
        
        Args:
            logger: Logger instance
            operation: Operation name
            level: Log level
            **extra_context: Additional context fields
        """
        self.logger = logger
        self.operation = operation
        self.level = level
        self.extra_context = extra_context
        self.start_time = None
    
    def __enter__(self):
        """Start timer."""
        import time
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer and log."""
        import time
        if self.start_time:
            latency_ms = (time.perf_counter() - self.start_time) * 1000
            
            log_data = {
                "operation": self.operation,
                "latency_ms": round(latency_ms, 2),
                **self.extra_context
            }
            
            if exc_type:
                log_data["error"] = str(exc_val)
                self.logger.log(
                    logging.ERROR,
                    f"{self.operation} failed",
                    extra=log_data
                )
            else:
                self.logger.log(
                    self.level,
                    f"{self.operation} completed",
                    extra=log_data
                )
        
        return False


# Logging helpers

def log_request_start(
    logger: logging.Logger,
    method: str,
    path: str,
    trace_id: str,
    user_id: Optional[int] = None,
    **kwargs
):
    """
    Log incoming HTTP request.
    
    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        trace_id: Trace ID
        user_id: User ID (if authenticated)
        **kwargs: Additional fields
    """
    log_data = {
        "event": "request_start",
        "method": method,
        "path": path,
        "trace_id": trace_id,
        **kwargs
    }
    
    if user_id:
        log_data["user_id"] = user_id
    
    logger.info("Incoming request", extra=log_data)


def log_request_end(
    logger: logging.Logger,
    method: str,
    path: str,
    status_code: int,
    latency_ms: float,
    **kwargs
):
    """
    Log completed HTTP request.
    
    Args:
        logger: Logger instance
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        latency_ms: Request latency in milliseconds
        **kwargs: Additional fields
    """
    log_data = {
        "event": "request_end",
        "method": method,
        "path": path,
        "status_code": status_code,
        "latency_ms": round(latency_ms, 2),
        **kwargs
    }
    
    # Use appropriate log level based on status
    if status_code >= 500:
        level = logging.ERROR
    elif status_code >= 400:
        level = logging.WARNING
    else:
        level = logging.INFO
    
    logger.log(level, "Request completed", extra=log_data)


def log_autobid_execution(
    logger: logging.Logger,
    auction_id: str,
    item_id: str,
    result: str,
    latency_ms: float,
    **kwargs
):
    """
    Log AutoBid execution.
    
    Args:
        logger: Logger instance
        auction_id: Auction ID
        item_id: Item ID
        result: Execution result (success, denied, failed)
        latency_ms: Execution latency
        **kwargs: Additional fields (bid_amount, confidence, reason, etc.)
    """
    log_data = {
        "event": "autobid_execution",
        "auction_id": auction_id,
        "item_id": item_id,
        "result": result,
        "latency_ms": round(latency_ms, 2),
        **kwargs
    }
    
    level = logging.INFO if result == "success" else logging.WARNING
    logger.log(level, f"AutoBid {result}", extra=log_data)


# Example usage
if __name__ == "__main__":
    # Setup JSON logging
    setup_json_logging(level="INFO", redact_sensitive=True)
    
    # Get logger
    logger = get_logger(__name__)
    
    # Log with context
    add_context(trace_id="abc123", user_id=456)
    logger.info("User authenticated", ip="192.168.1.1")
    
    # Log with latency
    with LatencyLogger(logger, "database_query", table="users"):
        import time
        time.sleep(0.1)
    
    # Scoped context
    with LoggingContextManager(operation="valuation", category="ceramics"):
        logger.info("Starting valuation")
        logger.info("Valuation complete", confidence=0.85)
    
    clear_context()
    
    # Log without context
    logger.info("Background task completed")
