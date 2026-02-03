"""Automated tournament state management jobs using APScheduler."""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def activate_tournaments_job(db_module):
    """
    Automatically activate tournaments on Tuesday of tournament week.

    Runs daily at 6 AM Eastern Time.

    Tournament activation logic:
    - Tournaments with status='upcoming' are activated when current date >= Tuesday of tournament week
    - Tuesday is calculated as start_date - 2 days (assumes tournaments start Thursday)
    """
    logger.info("Running activate_tournaments job...")
    activated_count = 0

    try:
        now = datetime.now()

        for tournament in db_module.tournaments():
            if tournament.status != 'upcoming' or not tournament.start_date:
                continue

            try:
                # Parse start date
                start_date = datetime.fromisoformat(tournament.start_date.replace('Z', '+00:00'))
            except:
                start_date = datetime.fromisoformat(tournament.start_date)

            # Calculate Tuesday of tournament week (2 days before start)
            tuesday_of_week = start_date - timedelta(days=2)

            # Activate tournament if current date >= Tuesday of tournament week
            if now >= tuesday_of_week:
                logger.info(f"Activating tournament: {tournament.name} (today >= {tuesday_of_week.date()})")
                db_module.tournaments.update(id=tournament.id, status='active')
                activated_count += 1

        logger.info(f"Finished activate_tournaments job - activated {activated_count} tournaments")

    except Exception as e:
        logger.error(f"Error in activate_tournaments job: {e}", exc_info=True)


def lock_picks_job(db_module):
    """
    Automatically lock picks when tournament starts (tournament day).

    Runs every 3 hours Eastern Time.

    Lock picks logic:
    - Tournaments with status='active' and picks_locked=False are locked when current date >= start_date
    """
    logger.info("Running lock_picks job...")
    locked_count = 0

    try:
        now = datetime.now()

        for tournament in db_module.tournaments():
            if tournament.status != 'active' or tournament.picks_locked or not tournament.start_date:
                continue

            try:
                # Parse start date
                start_date = datetime.fromisoformat(tournament.start_date.replace('Z', '+00:00'))
            except:
                start_date = datetime.fromisoformat(tournament.start_date)

            # Lock picks when tournament day arrives
            if now.date() >= start_date.date():
                logger.info(f"Locking picks for tournament: {tournament.name} (tournament started)")
                db_module.tournaments.update(id=tournament.id, picks_locked=True)
                locked_count += 1

        logger.info(f"Finished lock_picks job - locked {locked_count} tournaments")

    except Exception as e:
        logger.error(f"Error in lock_picks job: {e}", exc_info=True)


def complete_tournaments_job(db_module):
    """
    Automatically complete tournaments when all active players finish round 4.

    Runs every 2 hours on Sunday/Monday Eastern Time.

    Tournament completion logic:
    - Fetches live stats from DataGolf for the current tournament
    - Checks if current round is 4 and all active players have finished
    - Updates tournament status to 'completed' and sends final leaderboard to GroupMe
    """
    logger.info("Running complete_tournaments job...")
    completed_count = 0

    try:
        from services.datagolf import DataGolfClient
        from routes.admin import _tournament_names_match, _send_final_leaderboard_groupme

        client = DataGolfClient()

        # Get current tournament info from DataGolf
        live_data = client.get_live_stats()
        live_stats = live_data.get('live_stats', [])
        current_event_name = live_data.get('event_name', '')
        current_round = live_data.get('current_round')

        logger.info(f"DataGolf event: {current_event_name}, round: {current_round}")

        # Process active tournaments
        for tournament in db_module.tournaments():
            if tournament.status != 'active':
                continue

            if not tournament.datagolf_name:
                continue

            # Check if this is the current tournament on DataGolf
            if _tournament_names_match(tournament.datagolf_name, current_event_name):
                # Check if round 4 is complete
                if current_round == 4:
                    # Extract active players (those with numeric positions)
                    active_players = []
                    for player in live_stats:
                        pos = player.get('position', '')
                        # Check if position is numeric (remove 'T' prefix if present)
                        clean_pos = pos.replace('T', '').strip() if pos else ''
                        if clean_pos and clean_pos.isdigit():
                            active_players.append(player)

                    # Count players who finished round 4 (thru = 18 or 'F')
                    finished_players = []
                    for player in active_players:
                        thru = player.get('thru')
                        if thru in [18, 'F', '18']:
                            finished_players.append(player)

                    # Tournament is complete when all active players finished round 4
                    if len(active_players) > 0 and len(finished_players) == len(active_players):
                        if tournament.status != 'completed':
                            logger.info(f"Completing tournament: {tournament.name} "
                                      f"({len(finished_players)}/{len(active_players)} players finished round 4)")
                            db_module.tournaments.update(id=tournament.id, status='completed')

                            # Send final leaderboard to GroupMe
                            _send_final_leaderboard_groupme(db_module, tournament.id)
                            completed_count += 1
                    else:
                        logger.debug(f"Tournament {tournament.name}: {len(finished_players)}/{len(active_players)} "
                                   "players finished (waiting for all to finish)")

        logger.info(f"Finished complete_tournaments job - completed {completed_count} tournaments")

    except Exception as e:
        logger.error(f"Error in complete_tournaments job: {e}", exc_info=True)
