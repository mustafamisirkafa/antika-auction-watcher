"""
Feedback Learning Loop Background Job
Runs periodically (every 30 minutes) to learn from user feedback
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from backend.services.feedback_collector import FeedbackCollector
from backend.services.feedback_learner import FeedbackLearner


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FeedbackLearningLoop:
    """
    Background task that periodically learns from feedback
    """
    
    def __init__(self, interval_minutes: int = 30):
        """
        Initialize learning loop
        
        Args:
            interval_minutes: How often to run learning cycle (default: 30)
        """
        self.interval_minutes = interval_minutes
        self.interval_seconds = interval_minutes * 60
        self.running = False
        self.collector = None
        self.learner = None
        self.cycle_count = 0
    
    async def initialize(self):
        """Initialize services"""
        logger.info("Initializing Feedback Learning Loop")
        
        self.collector = FeedbackCollector()
        await self.collector.initialize()
        
        self.learner = FeedbackLearner(self.collector)
        await self.learner.initialize()
        
        logger.info("Feedback Learning Loop initialized")
    
    async def run_learning_cycle(self) -> bool:
        """
        Run one learning cycle
        
        Returns:
            True if learning occurred, False if skipped
        """
        try:
            logger.info(f"Starting learning cycle #{self.cycle_count + 1}")
            
            # Check pending feedback count
            pending_count = await self.learner.get_pending_feedback_count()
            logger.info(f"Pending feedback: {pending_count}")
            
            if pending_count == 0:
                logger.info("No pending feedback, skipping cycle")
                return False
            
            # Run learning
            metrics = await self.learner.learn_from_feedback()
            
            if metrics:
                self.cycle_count += 1
                logger.info(f"Learning cycle #{self.cycle_count} complete")
                logger.info(f"  - Processed: {metrics.feedback_processed} feedback entries")
                logger.info(f"  - Accuracy: {metrics.overall_accuracy:.2%}")
                logger.info(f"  - Helpfulness: {metrics.helpfulness_rate:.2%}")
                logger.info(f"  - Improvement: {metrics.accuracy_improvement:+.2%}")
                logger.info(f"  - New weights: Pattern={metrics.new_weights.pattern:.2f}, "
                          f"Market={metrics.new_weights.market:.2f}, "
                          f"Behavior={metrics.new_weights.behavior:.2f}, "
                          f"Risk={metrics.new_weights.risk:.2f}")
                return True
            else:
                logger.info("Not enough feedback for learning cycle")
                return False
                
        except Exception as e:
            logger.error(f"Error in learning cycle: {str(e)}", exc_info=True)
            return False
    
    async def run_forever(self):
        """
        Run learning loop continuously
        """
        await self.initialize()
        
        logger.info(f"Starting continuous learning loop (interval: {self.interval_minutes} minutes)")
        self.running = True
        
        while self.running:
            try:
                await self.run_learning_cycle()
                
                # Wait for next cycle
                logger.info(f"Waiting {self.interval_minutes} minutes until next cycle...")
                await asyncio.sleep(self.interval_seconds)
                
            except asyncio.CancelledError:
                logger.info("Learning loop cancelled")
                break
            except Exception as e:
                logger.error(f"Unexpected error in learning loop: {str(e)}", exc_info=True)
                # Wait a bit before retrying
                await asyncio.sleep(60)
    
    async def run_once(self) -> bool:
        """
        Run one learning cycle and exit
        
        Returns:
            True if learning occurred
        """
        await self.initialize()
        return await self.run_learning_cycle()
    
    def stop(self):
        """Stop the learning loop"""
        logger.info("Stopping learning loop")
        self.running = False
    
    async def cleanup(self):
        """Cleanup old feedback data"""
        try:
            logger.info("Running cleanup task")
            deleted = await self.collector.clear_old_feedback(days=90)
            logger.info(f"Cleaned up {deleted} old feedback entries")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}", exc_info=True)


async def main():
    """
    Main entry point for running as standalone script
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Feedback Learning Loop')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--interval', type=int, default=30, help='Interval in minutes (default: 30)')
    parser.add_argument('--cleanup', action='store_true', help='Run cleanup and exit')
    
    args = parser.parse_args()
    
    loop = FeedbackLearningLoop(interval_minutes=args.interval)
    
    if args.cleanup:
        await loop.initialize()
        await loop.cleanup()
    elif args.once:
        success = await loop.run_once()
        logger.info(f"Learning cycle {'completed' if success else 'skipped'}")
    else:
        try:
            await loop.run_forever()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            loop.stop()


if __name__ == "__main__":
    asyncio.run(main())
