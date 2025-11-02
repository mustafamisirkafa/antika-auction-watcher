"""
Nightly profit analysis background job.
Analyzes all upcoming auction items for profit estimation.
"""
import asyncio
import logging
from datetime import datetime
from sqlmodel import Session, create_engine

from backend.core.config import settings
from backend.db.database import engine
from backend.services.profit_advisor import ProfitAdvisorService

logger = logging.getLogger(__name__)


async def run_nightly_profit_analysis():
    """
    Run profit analysis for all teams with upcoming auctions.
    Scheduled to run daily at 03:00.
    """
    logger.info("=== Starting nightly profit analysis ===")
    start_time = datetime.utcnow()
    
    try:
        # Create database session
        with Session(engine) as session:
            # Create profit advisor service
            advisor = ProfitAdvisorService(session)
            
            # Run analysis for all teams
            await advisor.run_all_teams()
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"=== Nightly profit analysis completed in {duration:.2f}s ===")
        
    except Exception as e:
        logger.error(f"=== Nightly profit analysis failed: {e} ===", exc_info=True)
        raise


def run_profit_analysis_sync():
    """
    Synchronous wrapper for async profit analysis.
    Used by schedulers that don't support async.
    """
    asyncio.run(run_nightly_profit_analysis())


# For APScheduler
if __name__ == "__main__":
    run_profit_analysis_sync()
