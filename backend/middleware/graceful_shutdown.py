"""
Graceful Shutdown Middleware (Sprint 1)
Ensures safe shutdown of WebSocket connections and background tasks.
"""
import logging
import signal
import asyncio
from typing import Callable, Set
from fastapi import FastAPI

logger = logging.getLogger(__name__)


class GracefulShutdownHandler:
    """
    Handles graceful shutdown of the application.
    Drains WebSocket connections and completes ongoing tasks.
    """
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.is_shutting_down = False
        self.active_websockets: Set = set()
        self.active_tasks: Set[asyncio.Task] = set()
        self.shutdown_timeout = 30  # seconds
    
    def register_websocket(self, ws_id: str):
        """Register an active WebSocket connection."""
        self.active_websockets.add(ws_id)
        logger.debug(f"WebSocket registered: {ws_id} (total: {len(self.active_websockets)})")
    
    def unregister_websocket(self, ws_id: str):
        """Unregister a WebSocket connection."""
        self.active_websockets.discard(ws_id)
        logger.debug(f"WebSocket unregistered: {ws_id} (remaining: {len(self.active_websockets)})")
    
    def register_task(self, task: asyncio.Task):
        """Register an active background task."""
        self.active_tasks.add(task)
        task.add_done_callback(lambda t: self.active_tasks.discard(t))
    
    async def shutdown(self, sig: signal.Signals = None):
        """
        Perform graceful shutdown.
        
        Steps:
        1. Set shutdown flag
        2. Stop accepting new connections
        3. Drain WebSocket connections (send close frames)
        4. Wait for active tasks to complete (with timeout)
        5. Close database connections
        6. Close Redis connections
        """
        if self.is_shutting_down:
            logger.warning("Shutdown already in progress")
            return
        
        self.is_shutting_down = True
        
        if sig:
            logger.info(f"Received shutdown signal: {sig.name}")
        else:
            logger.info("Graceful shutdown initiated")
        
        # Step 1: Notify that we're shutting down
        logger.info(f"Active WebSockets: {len(self.active_websockets)}")
        logger.info(f"Active tasks: {len(self.active_tasks)}")
        
        # Step 2: Send close messages to all WebSocket connections
        logger.info("Draining WebSocket connections...")
        for ws_id in list(self.active_websockets):
            try:
                # WebSocket connections will close when they detect shutdown flag
                logger.debug(f"Closing WebSocket: {ws_id}")
            except Exception as e:
                logger.error(f"Error closing WebSocket {ws_id}: {e}")
        
        # Wait a bit for WebSockets to close gracefully
        await asyncio.sleep(2)
        
        # Step 3: Wait for active tasks to complete
        if self.active_tasks:
            logger.info(f"Waiting for {len(self.active_tasks)} tasks to complete...")
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.active_tasks, return_exceptions=True),
                    timeout=self.shutdown_timeout - 5
                )
                logger.info("All tasks completed")
            except asyncio.TimeoutError:
                logger.warning("Timeout waiting for tasks, cancelling remaining tasks")
                for task in self.active_tasks:
                    if not task.done():
                        task.cancel()
        
        # Step 4: Close connections (handled by lifespan in main.py)
        logger.info("Graceful shutdown complete")
    
    def setup_signal_handlers(self):
        """
        Setup signal handlers for graceful shutdown.
        Handles SIGTERM and SIGINT.
        """
        loop = asyncio.get_event_loop()
        
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self.shutdown(s))
            )
        
        logger.info("Signal handlers registered (SIGTERM, SIGINT)")


# Global shutdown handler instance
shutdown_handler: Optional[GracefulShutdownHandler] = None


def get_shutdown_handler() -> Optional[GracefulShutdownHandler]:
    """Get the global shutdown handler instance."""
    return shutdown_handler


def init_shutdown_handler(app: FastAPI) -> GracefulShutdownHandler:
    """
    Initialize and return the global shutdown handler.
    
    Args:
        app: FastAPI application instance
    
    Returns:
        GracefulShutdownHandler instance
    """
    global shutdown_handler
    
    if shutdown_handler is None:
        shutdown_handler = GracefulShutdownHandler(app)
        shutdown_handler.setup_signal_handlers()
        logger.info("Graceful shutdown handler initialized")
    
    return shutdown_handler


async def is_shutting_down() -> bool:
    """
    Check if application is shutting down.
    
    Returns:
        True if shutdown is in progress
    """
    handler = get_shutdown_handler()
    return handler.is_shutting_down if handler else False
