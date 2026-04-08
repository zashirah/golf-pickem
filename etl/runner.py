"""Standalone ETL runner with APScheduler.

Run as a separate process:
    python etl/runner.py

Environment variables:
    DATABASE_URL                - SQLAlchemy connection string (same as web app)
    DATAGOLF_API_KEY            - DataGolf API key
    ETL_SYNC_INTERVAL_MINUTES   - How often to sync live results (default: 10)
"""
import logging
import os
import sys

# Ensure the project root is on the Python path when invoked directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from apscheduler.schedulers.blocking import BlockingScheduler

from db import init_db
import db as db_module
from services.datagolf import DataGolfClient

from etl.tournament_state import activate_tournaments, complete_tournaments
from etl.results import sync_results


def _activate_job():
    """Job: activate upcoming tournaments on Tuesday of tournament week."""
    logger.info("ETL job: activate_tournaments")
    try:
        count = activate_tournaments(db_module)
        logger.info(f"ETL job done: activated {count} tournaments")
    except Exception as e:
        logger.error(f"activate_tournaments failed: {e}", exc_info=True)


def _complete_job():
    """Job: complete finished tournaments when all players finish round 4."""
    logger.info("ETL job: complete_tournaments")
    try:
        client = DataGolfClient()
        count = complete_tournaments(db_module, client)
        logger.info(f"ETL job done: completed {count} tournaments")
    except Exception as e:
        logger.error(f"complete_tournaments failed: {e}", exc_info=True)


def _sync_results_job():
    """Job: sync live results and recalculate standings for the active tournament."""
    logger.info("ETL job: sync_results")
    try:
        active = [t for t in db_module.tournaments() if t.status == 'active']
        if not active:
            logger.debug("No active tournament, skipping results sync")
            return

        client = DataGolfClient()
        tournament = active[0]
        result = sync_results(db_module, client, tournament)

        from services.scoring import ScoringService
        ScoringService(db_module).calculate_standings(tournament.id)

        logger.info(
            f"ETL job done: synced {result['result_count']} results "
            f"for '{tournament.name}', standings recalculated"
        )
    except ValueError as e:
        # Tournament name mismatch — not an error condition, just skip
        logger.warning(f"Results sync skipped: {e}")
    except Exception as e:
        logger.error(f"sync_results failed: {e}", exc_info=True)


if __name__ == "__main__":
    logger.info("Initializing database for ETL runner...")
    init_db()

    sync_interval = int(os.getenv("ETL_SYNC_INTERVAL_MINUTES", "10"))
    logger.info(f"ETL runner starting (live results sync interval: {sync_interval} min)...")

    scheduler = BlockingScheduler(timezone='America/New_York')

    # Job 1: Activate tournaments daily at 6 AM ET
    scheduler.add_job(
        _activate_job,
        'cron',
        hour=6,
        id='activate_tournaments',
        replace_existing=True
    )

    # Job 2: Complete tournaments every 2 hours on Sun/Mon ET
    scheduler.add_job(
        _complete_job,
        'cron',
        hour='*/2',
        day_of_week='sun,mon',
        id='complete_tournaments',
        replace_existing=True
    )

    # Job 3: Sync live results every N minutes
    scheduler.add_job(
        _sync_results_job,
        'interval',
        minutes=sync_interval,
        id='sync_results',
        replace_existing=True
    )

    logger.info("ETL scheduler started with 3 jobs")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("ETL runner stopped")
