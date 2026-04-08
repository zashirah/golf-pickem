"""ETL: Sync live tournament results from DataGolf into DB."""
import logging
from datetime import datetime

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


def sync_results(db, datagolf_client, tournament) -> dict:
    """Sync live tournament results from DataGolf into tournament_result table.

    Validates that the DataGolf API is returning data for the correct tournament.
    Does NOT call calculate_standings — callers must do that separately.

    Raises:
        ValueError: if the DataGolf event name doesn't match the tournament.

    Returns dict with 'result_count' key.
    """
    from sqlalchemy import text

    tournament_id = tournament.id

    live_data = datagolf_client.get_live_stats()

    # Validate tournament name match before writing anything
    api_event_name = live_data.get('event_name', '')
    if not _tournament_names_match(tournament.name, api_event_name):
        raise ValueError(
            f"Tournament mismatch: DataGolf is returning data for '{api_event_name}', "
            f"not '{tournament.name}'. Sync cancelled."
        )

    live_stats = live_data.get('live_stats', [])
    golfers_by_dg_id = {g.datagolf_id: g for g in db.golfers()}

    now = datetime.now().isoformat()
    results_data = []

    for player in live_stats:
        dg_id = str(player.get('dg_id', ''))
        golfer = golfers_by_dg_id.get(dg_id)
        if not golfer:
            continue

        pos_str = player.get('position', '')
        position = None
        status = 'active'

        if pos_str:
            pos_clean = pos_str.replace('T', '').strip()
            if pos_clean.isdigit():
                position = int(pos_clean)
            elif pos_str.upper() in ('CUT', 'MC'):
                status = 'cut'
            elif pos_str.upper() in ('WD', 'W/D'):
                status = 'wd'
            elif pos_str.upper() == 'DQ':
                status = 'dq'

        results_data.append({
            'tournament_id': tournament_id,
            'golfer_id': golfer.id,
            'position': position,
            'score_to_par': player.get('total'),
            'status': status,
            'round_num': player.get('round'),
            'thru': player.get('thru'),
            'updated_at': now
        })

    if results_data:
        logger.info(f"Batch upserting {len(results_data)} tournament results...")
        with db.db.engine.connect() as conn:
            conn.execute(
                text("DELETE FROM tournament_result WHERE tournament_id = :tid"),
                {"tid": tournament_id}
            )

            values_list = []
            params = {}
            for i, r in enumerate(results_data):
                values_list.append(
                    f"(:tid_{i}, :gid_{i}, :pos_{i}, :score_{i}, :status_{i}, :round_{i}, :thru_{i}, :updated_{i})"
                )
                params[f"tid_{i}"] = r['tournament_id']
                params[f"gid_{i}"] = r['golfer_id']
                params[f"pos_{i}"] = r['position']
                params[f"score_{i}"] = r['score_to_par']
                params[f"status_{i}"] = r['status']
                params[f"round_{i}"] = r['round_num']
                params[f"thru_{i}"] = r['thru']
                params[f"updated_{i}"] = r['updated_at']

            sql = f"""
                INSERT INTO tournament_result
                (tournament_id, golfer_id, position, score_to_par, status, round_num, thru, updated_at)
                VALUES {', '.join(values_list)}
            """
            conn.execute(text(sql), params)
            conn.commit()

        logger.info(f"Synced {len(results_data)} results for tournament {tournament_id}")

    # Update tournament last_synced_at timestamp
    db.tournaments.update(id=tournament_id, last_synced_at=now)

    return {"result_count": len(results_data)}
