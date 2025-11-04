"""
Circuit Breaker Service (Sprint 1)
Implements fault-tolerance for external API calls and critical services.
"""
import logging
from typing import Callable, Any, Optional
from functools import wraps
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from pybreaker import CircuitBreaker, CircuitBreakerListener
import time

logger = logging.getLogger(__name__)


class CircuitBreakerMetrics(CircuitBreakerListener):
    """
    Custom listener for circuit breaker metrics.
    Tracks state changes and failures.
    """
    
    def __init__(self):
        self.metrics = {
            "state_changes": 0,
            "failures": 0,
            "successes": 0,
            "timeouts": 0,
        }
    
    def state_change(self, cb, old_state, new_state):
        """Called when circuit breaker changes state."""
        self.metrics["state_changes"] += 1
        logger.warning(
            f"Circuit breaker '{cb.name}' state changed: {old_state.name} ? {new_state.name}"
        )
    
    def before_call(self, cb, func, *args, **kwargs):
        """Called before a call is made."""
        pass
    
    def success(self, cb):
        """Called on successful call."""
        self.metrics["successes"] += 1
    
    def failure(self, cb, exc):
        """Called on failed call."""
        self.metrics["failures"] += 1
        logger.error(f"Circuit breaker '{cb.name}' recorded failure: {exc}")


# Global circuit breaker metrics
cb_metrics = CircuitBreakerMetrics()


# Circuit breaker configurations
# fail_max: Number of failures before opening circuit
# timeout: Time in seconds circuit stays open
# reset_timeout: Time in seconds before attempting recovery

# External API circuit breakers
ebay_circuit_breaker = CircuitBreaker(
    fail_max=5,
    timeout=30,
    name="ebay_api",
    listeners=[cb_metrics]
)

etsy_circuit_breaker = CircuitBreaker(
    fail_max=5,
    timeout=30,
    name="etsy_api",
    listeners=[cb_metrics]
)

instagram_circuit_breaker = CircuitBreaker(
    fail_max=5,
    timeout=30,
    name="instagram_api",
    listeners=[cb_metrics]
)

sahibinden_circuit_breaker = CircuitBreaker(
    fail_max=5,
    timeout=30,
    name="sahibinden_api",
    listeners=[cb_metrics]
)

# Internal service circuit breakers
redis_circuit_breaker = CircuitBreaker(
    fail_max=3,
    timeout=10,
    name="redis",
    listeners=[cb_metrics]
)

database_circuit_breaker = CircuitBreaker(
    fail_max=3,
    timeout=10,
    name="database",
    listeners=[cb_metrics]
)


def with_circuit_breaker(breaker: CircuitBreaker):
    """
    Decorator to wrap function with circuit breaker.
    
    Usage:
        @with_circuit_breaker(ebay_circuit_breaker)
        async def fetch_ebay_data(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await breaker.call_async(func, *args, **kwargs)
        return wrapper
    return decorator


def with_retry(
    max_attempts: int = 3,
    wait_min: float = 1.0,
    wait_max: float = 10.0,
    exception_types: tuple = (Exception,)
):
    """
    Decorator to add retry logic with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        wait_min: Minimum wait time between retries (seconds)
        wait_max: Maximum wait time between retries (seconds)
        exception_types: Tuple of exception types to retry on
    
    Usage:
        @with_retry(max_attempts=3, wait_min=1.0, wait_max=10.0)
        async def fetch_data(...):
            ...
    """
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=wait_min, max=wait_max),
        retry=retry_if_exception_type(exception_types),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


class TimeoutBudget:
    """
    Timeout budget tracker for request processing.
    Ensures total request time stays within SLA.
    """
    
    def __init__(self, total_budget_ms: float = 3000):
        """
        Initialize timeout budget.
        
        Args:
            total_budget_ms: Total time budget in milliseconds (default 3000ms = 3s)
        """
        self.total_budget_ms = total_budget_ms
        self.start_time = time.time()
        self.spent_time_ms = 0
    
    def remaining_ms(self) -> float:
        """Get remaining time in milliseconds."""
        elapsed = (time.time() - self.start_time) * 1000
        return max(0, self.total_budget_ms - elapsed)
    
    def remaining_seconds(self) -> float:
        """Get remaining time in seconds."""
        return self.remaining_ms() / 1000
    
    def is_exceeded(self) -> bool:
        """Check if budget is exceeded."""
        return self.remaining_ms() <= 0
    
    def checkpoint(self, operation: str) -> None:
        """
        Log checkpoint with elapsed time.
        
        Args:
            operation: Name of the operation
        """
        elapsed = (time.time() - self.start_time) * 1000
        remaining = self.remaining_ms()
        logger.debug(f"Timeout budget - {operation}: {elapsed:.0f}ms elapsed, {remaining:.0f}ms remaining")
        
        if remaining < 500:  # Less than 500ms remaining
            logger.warning(f"Timeout budget low: {remaining:.0f}ms remaining for {operation}")


# Timeout configurations (milliseconds)
TIMEOUT_CONFIG = {
    "autobid_total": 2500,      # AutoBid total budget (2.5s)
    "api_call": 1000,           # External API calls (1s)
    "redis_op": 100,            # Redis operations (100ms)
    "db_query": 500,            # Database queries (500ms)
    "websocket_send": 200,      # WebSocket message send (200ms)
    "valuation": 1200,          # Valuation calculation (1.2s)
    "system_buffer": 500,       # System buffer (500ms)
}


def get_timeout(operation: str) -> float:
    """
    Get timeout for a specific operation in seconds.
    
    Args:
        operation: Operation name (e.g., 'api_call', 'redis_op')
    
    Returns:
        Timeout in seconds
    """
    timeout_ms = TIMEOUT_CONFIG.get(operation, 1000)
    return timeout_ms / 1000


async def with_timeout_budget(func: Callable, budget: TimeoutBudget, operation: str) -> Any:
    """
    Execute function within timeout budget.
    
    Args:
        func: Async function to execute
        budget: TimeoutBudget instance
        operation: Operation name for logging
    
    Returns:
        Function result
    
    Raises:
        TimeoutError: If budget exceeded
    """
    if budget.is_exceeded():
        raise TimeoutError(f"Timeout budget exceeded before {operation}")
    
    import asyncio
    
    try:
        result = await asyncio.wait_for(
            func(),
            timeout=budget.remaining_seconds()
        )
        budget.checkpoint(operation)
        return result
    except asyncio.TimeoutError:
        logger.error(f"Operation '{operation}' timed out")
        raise TimeoutError(f"Operation '{operation}' exceeded timeout budget")


def get_circuit_breaker_state(name: str) -> dict:
    """
    Get current state of a circuit breaker.
    
    Args:
        name: Circuit breaker name
    
    Returns:
        Dict with state information
    """
    breakers = {
        "ebay_api": ebay_circuit_breaker,
        "etsy_api": etsy_circuit_breaker,
        "instagram_api": instagram_circuit_breaker,
        "sahibinden_api": sahibinden_circuit_breaker,
        "redis": redis_circuit_breaker,
        "database": database_circuit_breaker,
    }
    
    cb = breakers.get(name)
    if not cb:
        return {"error": "Circuit breaker not found"}
    
    return {
        "name": cb.name,
        "state": cb.current_state.name,
        "fail_counter": cb.fail_counter,
        "fail_max": cb.fail_max,
        "timeout": cb.timeout,
    }


def get_all_circuit_breaker_states() -> dict:
    """
    Get states of all circuit breakers.
    
    Returns:
        Dict mapping breaker names to their states
    """
    breakers = [
        "ebay_api",
        "etsy_api",
        "instagram_api",
        "sahibinden_api",
        "redis",
        "database",
    ]
    
    return {
        name: get_circuit_breaker_state(name)
        for name in breakers
    }
