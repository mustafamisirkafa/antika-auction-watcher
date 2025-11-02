"""
Background task scheduler for Antika Auction Watcher.
Schedules periodic tasks like profit analysis and usage tracking.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import logging

from backend.tasks.profit_analysis_job import run_profit_analysis_sync
from backend.tasks.feedback_learning_loop import run_feedback_learning_cycle

logger = logging.getLogger(__name__)


def create_scheduler() -> AsyncIOScheduler:
    """
    Create and configure the background task scheduler.
    
    Returns:
        Configured AsyncIOScheduler
    """
    scheduler = AsyncIOScheduler()
    
    # Nightly profit analysis (every day at 3:00 AM)
    scheduler.add_job(
        run_profit_analysis_sync,
        trigger=CronTrigger(hour=3, minute=0),
        id="nightly_profit_analysis",
        name="Nightly Profit Analysis",
        replace_existing=True,
        misfire_grace_time=3600  # Allow 1 hour grace period
    )
    logger.info("Scheduled: Nightly profit analysis at 03:00 daily")
    
    # Feedback learning loop (every 30 minutes)
    scheduler.add_job(
        run_feedback_learning_cycle,
        trigger=IntervalTrigger(minutes=30),
        id="feedback_learning_loop",
        name="Feedback Learning Loop",
        replace_existing=True,
        misfire_grace_time=600  # Allow 10 minute grace period
    )
    logger.info("Scheduled: Feedback learning loop every 30 minutes")
    
    # Usage tracking (hourly)
    # Note: This is handled by UsageTracker.run_hourly_task() separately
    
    return scheduler


# Global scheduler instance
scheduler = None


def start_scheduler():
    """Start the background task scheduler."""
    global scheduler
    
    if scheduler is None:
        scheduler = create_scheduler()
        scheduler.start()
        logger.info("Background task scheduler started")
    else:
        logger.warning("Scheduler already started")


def stop_scheduler():
    """Stop the background task scheduler."""
    global scheduler
    
    if scheduler is not None:
        scheduler.shutdown()
        scheduler = None
        logger.info("Background task scheduler stopped")
    else:
        logger.warning("Scheduler not running")
