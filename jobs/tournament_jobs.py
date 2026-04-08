"""APScheduler job wrappers for tournament state management.

Each function is a thin wrapper around the corresponding ETL function in
etl/tournament_state.py. The actual business logic lives there; this module
exists solely to give app.py named callables to register with APScheduler.
"""
import logging

logger = logging.getLogger(__name__)


def activate_tournaments_job(db_module):
    """Activate upcoming tournaments on Tuesday of tournament week."""
    logger.info("Running activate_tournaments job...")
    from etl.tournament_state import activate_tournaments
    try:
        count = activate_tournaments(db_module)
        logger.info(f"Finished activate_tournaments job - activated {count} tournaments")
    except Exception as e:
        logger.error(f"Error in activate_tournaments job: {e}", exc_info=True)


def lock_picks_job(db_module):
    """Lock picks when tournament starts. Currently disabled in production."""
    logger.info("Running lock_picks job...")
    from etl.tournament_state import lock_picks
    try:
        count = lock_picks(db_module)
        logger.info(f"Finished lock_picks job - locked {count} tournaments")
    except Exception as e:
        logger.error(f"Error in lock_picks job: {e}", exc_info=True)


def complete_tournaments_job(db_module):
    """Complete finished tournaments when all players finish round 4."""
    logger.info("Running complete_tournaments job...")
    from services.datagolf import DataGolfClient
    from etl.tournament_state import complete_tournaments
    try:
        client = DataGolfClient()
        count = complete_tournaments(db_module, client)
        logger.info(f"Finished complete_tournaments job - completed {count} tournaments")
    except Exception as e:
        logger.error(f"Error in complete_tournaments job: {e}", exc_info=True)
