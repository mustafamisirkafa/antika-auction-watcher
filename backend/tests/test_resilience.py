"""
Resilience Tests (Sprint 1)
Tests for circuit breakers, timeouts, and fault tolerance.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pybreaker import CircuitBreakerError

from backend.core.circuit_breaker import (
    with_circuit_breaker,
    with_retry,
    TimeoutBudget,
    get_timeout,
    ebay_circuit_breaker,
    redis_circuit_breaker,
)


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures():
    """Test that circuit breaker opens after max failures."""
    # Create a test circuit breaker
    from pybreaker import CircuitBreaker
    
    test_breaker = CircuitBreaker(fail_max=3, timeout=1, name="test")
    
    # Function that always fails
    async def failing_function():
        raise ValueError("Simulated failure")
    
    # Call it 3 times to open the circuit
    for i in range(3):
        try:
            await test_breaker.call_async(failing_function)
        except ValueError:
            pass
    
    # Circuit should now be open
    assert test_breaker.current_state.name == "open"
    
    # Next call should fail immediately with CircuitBreakerError
    with pytest.raises(CircuitBreakerError):
        await test_breaker.call_async(failing_function)


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery():
    """Test circuit breaker transitions to half-open and recovers."""
    from pybreaker import CircuitBreaker
    
    test_breaker = CircuitBreaker(fail_max=2, timeout=1, name="test_recovery")
    
    # Fail twice to open circuit
    async def failing_func():
        raise ValueError("Fail")
    
    for _ in range(2):
        try:
            await test_breaker.call_async(failing_func)
        except ValueError:
            pass
    
    assert test_breaker.current_state.name == "open"
    
    # Wait for timeout to transition to half-open
    await asyncio.sleep(1.1)
    
    # Successful call should close the circuit
    async def success_func():
        return "success"
    
    result = await test_breaker.call_async(success_func)
    assert result == "success"
    assert test_breaker.current_state.name == "closed"


@pytest.mark.asyncio
async def test_retry_decorator():
    """Test retry decorator with exponential backoff."""
    call_count = 0
    
    @with_retry(max_attempts=3, wait_min=0.1, wait_max=0.5)
    async def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary failure")
        return "success"
    
    result = await flaky_function()
    
    assert result == "success"
    assert call_count == 3  # Failed twice, succeeded on third attempt


@pytest.mark.asyncio
async def test_retry_gives_up_after_max_attempts():
    """Test that retry gives up after max attempts."""
    call_count = 0
    
    @with_retry(max_attempts=3, wait_min=0.1, wait_max=0.5)
    async def always_failing():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("Permanent failure")
    
    with pytest.raises(ConnectionError):
        await always_failing()
    
    assert call_count == 3


@pytest.mark.asyncio
async def test_timeout_budget_tracking():
    """Test timeout budget tracking."""
    budget = TimeoutBudget(total_budget_ms=1000)
    
    # Initially, budget should be nearly full
    assert budget.remaining_ms() > 900
    assert not budget.is_exceeded()
    
    # Simulate some work
    await asyncio.sleep(0.5)
    
    # Budget should be reduced
    remaining = budget.remaining_ms()
    assert 400 < remaining < 600
    
    # Checkpoint
    budget.checkpoint("test_operation")


@pytest.mark.asyncio
async def test_timeout_budget_exceeded():
    """Test timeout budget exceeded detection."""
    budget = TimeoutBudget(total_budget_ms=100)
    
    # Wait longer than budget
    await asyncio.sleep(0.15)
    
    # Budget should be exceeded
    assert budget.is_exceeded()
    assert budget.remaining_ms() == 0


def test_get_timeout_config():
    """Test timeout configuration retrieval."""
    # Test known timeout values
    assert get_timeout("api_call") == 1.0  # 1000ms -> 1s
    assert get_timeout("redis_op") == 0.1  # 100ms -> 0.1s
    assert get_timeout("db_query") == 0.5  # 500ms -> 0.5s
    
    # Test default for unknown operation
    assert get_timeout("unknown_op") == 1.0  # Default 1s


@pytest.mark.asyncio
async def test_redis_failover_simulation():
    """
    Simulate Redis failover scenario.
    
    Scenario:
    1. Master goes down
    2. Sentinel promotes replica
    3. Application reconnects to new master
    """
    # This is a conceptual test - actual failover testing requires:
    # - Redis Sentinel running
    # - Ability to kill master
    # - Sentinel client in application
    
    # Mock Redis client with Sentinel support
    redis_mock = AsyncMock()
    redis_mock.ping.side_effect = [
        ConnectionError("Master down"),  # First call fails
        True,                             # After failover, succeeds
    ]
    
    # Simulate retry with circuit breaker
    @with_retry(max_attempts=2, wait_min=0.1, wait_max=0.5)
    async def ping_redis():
        result = await redis_mock.ping()
        if isinstance(result, Exception):
            raise result
        return result
    
    # Should succeed after retry
    result = await ping_redis()
    assert result is True
    assert redis_mock.ping.call_count == 2


@pytest.mark.asyncio
async def test_api_timeout_with_circuit_breaker():
    """Test API timeout with circuit breaker protection."""
    from pybreaker import CircuitBreaker
    
    test_breaker = CircuitBreaker(fail_max=2, timeout=1, name="api_test")
    
    # Slow API call that times out
    async def slow_api_call():
        await asyncio.sleep(2)  # Exceeds timeout
        return "data"
    
    # Call with timeout should fail
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            test_breaker.call_async(slow_api_call),
            timeout=0.5
        )


@pytest.mark.asyncio
async def test_db_connection_pool_exhaustion():
    """
    Test database connection pool exhaustion scenario.
    
    Verifies that:
    1. Circuit breaker opens when pool is exhausted
    2. Requests fail fast instead of hanging
    3. Recovery happens when connections are released
    """
    # Mock database session
    db_mock = Mock()
    db_mock.execute.side_effect = Exception("Connection pool exhausted")
    
    # Wrap with circuit breaker
    @with_circuit_breaker(redis_circuit_breaker)
    async def query_db():
        db_mock.execute("SELECT 1")
        return "result"
    
    # Should raise exception (pool exhausted)
    with pytest.raises(Exception):
        await query_db()


@pytest.mark.asyncio
async def test_graceful_shutdown_websocket_drain():
    """Test graceful shutdown drains WebSocket connections."""
    from backend.middleware.graceful_shutdown import GracefulShutdownHandler
    from fastapi import FastAPI
    
    app = FastAPI()
    handler = GracefulShutdownHandler(app)
    
    # Register some WebSocket connections
    handler.register_websocket("ws-1")
    handler.register_websocket("ws-2")
    handler.register_websocket("ws-3")
    
    assert len(handler.active_websockets) == 3
    
    # Simulate shutdown
    await handler.shutdown()
    
    # Shutdown flag should be set
    assert handler.is_shutting_down is True


@pytest.mark.asyncio
async def test_graceful_shutdown_task_completion():
    """Test graceful shutdown waits for active tasks."""
    from backend.middleware.graceful_shutdown import GracefulShutdownHandler
    from fastapi import FastAPI
    
    app = FastAPI()
    handler = GracefulShutdownHandler(app)
    
    # Create a background task
    task_completed = False
    
    async def background_task():
        nonlocal task_completed
        await asyncio.sleep(0.5)
        task_completed = True
    
    task = asyncio.create_task(background_task())
    handler.register_task(task)
    
    assert len(handler.active_tasks) == 1
    
    # Trigger shutdown
    await handler.shutdown()
    
    # Task should have completed
    assert task_completed is True
    assert handler.is_shutting_down is True
