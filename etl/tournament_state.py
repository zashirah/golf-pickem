"""ETL: Tournament state management (activate / complete / lock)."""
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def _normalize_tournament_name(name: str) -> str:
    """Normalize tournament name for comparison."""
    if not name:
        return ""
    normalized = name.lower().strip()
    if normalized.startswith("the "):
        normalized = normalized[4:]
    for suffix in [" presented by mastercard", " pga tour"]:
        normalized = normalized.replace(suffix, "")
    return normalized


def _tournament_names_match(db_name: str, api_name: str) -> bool:
    """Check if tournament names match (fuzzy comparison)."""
    norm_db = _normalize_tournament_name(db_name)
    norm_api = _normalize_tournament_name(api_name)
    if norm_db == norm_api:
        return True
    if norm_db in norm_api or norm_api in norm_db:
        return True
    return False


def send_final_leaderboard_groupme(db, tournament_id):
    """Send final leaderboard to GroupMe when a tournament completes."""
    try:
        from services.groupme import GroupMeClient
        from routes.utils import calculate_tournament_purse, format_score

        tournament = None
        for t in db.tournaments():
            if t.id == tournament_id:
                tournament = t
                break

        if not tournament:
            return

        all_picks = [p for p in db.picks() if p.tournament_id == tournament_id]
        standings = [s for s in db.pickem_standings() if s.tournament_id == tournament_id]
        standings.sort(key=lambda s: s.rank if s.rank else 999)

        users_by_id = {u.id: u for u in db.users()}
        purse = calculate_tournament_purse(tournament, all_picks)

        message_lines = [f"🏁 FINAL LEADERBOARD: {tournament.name}"]
        if purse:
            message_lines.append(f"💰 Purse: ${purse}")
        message_lines.append("")

        for i, standing in enumerate(standings[:10]):
            user = users_by_id.get(standing.user_id)
            player_name = user.display_name if user else f"User {standing.user_id}"
            rank = standing.rank if standing.rank else (i + 1)
            score = standing.best_two_total if standing.best_two_total is not None else "DQ"
            score_str = format_score(score) if isinstance(score, int) else str(score)
            message_lines.append(f"{rank}. {player_name} - {score_str}")

        message = "\n".join(message_lines)

        client = GroupMeClient(db_module=db)
        client.send_message(message)
        logger.info(f"Sent final leaderboard for {tournament.name} to GroupMe")

    except Exception as e:
        logger.error(f"Failed to send final leaderboard to GroupMe: {e}", exc_info=True)


def activate_tournaments(db) -> int:
    """Activate upcoming tournaments when current date >= Tuesday of tournament week.

    Tournaments are assumed to start Thursday; Tuesday is start_date - 2 days.
    Returns the number of tournaments activated.
    """
    logger.info("Running activate_tournaments...")
    activated_count = 0
    now = datetime.now()

    for tournament in db.tournaments():
        if tournament.status != 'upcoming' or not tournament.start_date:
            continue

        try:
            start_date = datetime.fromisoformat(tournament.start_date.replace('Z', '+00:00'))
        except Exception:
            start_date = datetime.fromisoformat(tournament.start_date)

        tuesday_of_week = start_date - timedelta(days=2)

        if now >= tuesday_of_week:
            logger.info(f"Activating tournament: {tournament.name} (today >= {tuesday_of_week.date()})")
            db.tournaments.update(id=tournament.id, status='active')
            activated_count += 1

    logger.info(f"activate_tournaments complete - activated {activated_count} tournaments")
    return activated_count


def complete_tournaments(db, datagolf_client, groupme_client=None) -> int:
    """Complete active tournaments when all players finish round 4.

    Fetches live stats from DataGolf and checks if all active players have
    finished round 4 (thru == 18 or 'F'). On completion, sends the final
    leaderboard to GroupMe.

    The groupme_client parameter is accepted but not used directly; GroupMe
    messaging is handled internally via send_final_leaderboard_groupme.

    Returns the number of tournaments completed.
    """
    logger.info("Running complete_tournaments...")
    completed_count = 0

    live_data = datagolf_client.get_live_stats()
    live_stats = live_data.get('live_stats', [])
    current_event_name = live_data.get('event_name', '')
    current_round = live_data.get('current_round')

    logger.info(f"DataGolf event: {current_event_name}, round: {current_round}")

    for tournament in db.tournaments():
        if tournament.status != 'active' or not tournament.datagolf_name:
            continue

        if not _tournament_names_match(tournament.datagolf_name, current_event_name):
            continue

        if current_round != 4:
            continue

        active_players = []
        for player in live_stats:
            pos = player.get('position', '')
            clean_pos = pos.replace('T', '').strip() if pos else ''
            if clean_pos and clean_pos.isdigit():
                active_players.append(player)
        finished_players = [
            p for p in active_players
            if p.get('thru') in [18, 'F', '18']
        ]

        if len(active_players) > 0 and len(finished_players) == len(active_players):
            logger.info(
                f"Completing tournament: {tournament.name} "
                f"({len(finished_players)}/{len(active_players)} players finished round 4)"
            )
            db.tournaments.update(id=tournament.id, status='completed')
            send_final_leaderboard_groupme(db, tournament.id)
            completed_count += 1
        else:
            logger.debug(
                f"Tournament {tournament.name}: {len(finished_players)}/{len(active_players)} "
                "players finished (waiting for all to finish)"
            )

    logger.info(f"complete_tournaments done - completed {completed_count} tournaments")
    return completed_count


def lock_picks(db) -> int:
    """Lock picks for active tournaments when tournament day arrives.

    Currently disabled in production — use the admin UI to lock manually.
    Returns the number of tournaments locked.
    """
    logger.info("Running lock_picks...")
    locked_count = 0
    now = datetime.now()

    for tournament in db.tournaments():
        if tournament.status != 'active' or tournament.picks_locked or not tournament.start_date:
            continue

        try:
            start_date = datetime.fromisoformat(tournament.start_date.replace('Z', '+00:00'))
        except Exception:
            start_date = datetime.fromisoformat(tournament.start_date)

        if now.date() >= start_date.date():
            logger.info(f"Locking picks for tournament: {tournament.name} (tournament started)")
            db.tournaments.update(id=tournament.id, picks_locked=True)
            locked_count += 1

    logger.info(f"lock_picks complete - locked {locked_count} tournaments")
    return locked_count
