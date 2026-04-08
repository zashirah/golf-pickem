"""ETL: Sync golfers from DataGolf rankings into DB."""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def sync_golfers(db, datagolf_client) -> dict:
    """Sync golfers from DataGolf rankings into DB.

    Fetches top 400 ranked players (covers most tournament fields) and upserts
    into the golfer table. Returns dict with 'golfer_count' key.
    """
    from sqlalchemy import text
    from config import DATABASE_URL

    logger.info("Starting golfer sync - fetching rankings...")
    rankings = datagolf_client.get_rankings()[:400]
    logger.info(f"Fetched {len(rankings)} rankings from DataGolf")

    players = datagolf_client.get_player_list()
    logger.info(f"Fetched {len(players)} players from DataGolf")

    # Build lookup: dg_id -> {name, country}
    player_info = {}
    for p in players:
        dg_id = str(p.get('dg_id', ''))
        player_info[dg_id] = {
            'name': p.get('player_name', ''),
            'country': p.get('country', '')
        }

    now = datetime.now().isoformat()
    values_list = []
    params = {}
    for i, r in enumerate(rankings):
        dg_id = str(r.get('dg_id', ''))
        skill = r.get('dg_skill_estimate', 0)
        info = player_info.get(dg_id, {})
        name = info.get('name', r.get('player_name', ''))
        country = info.get('country', '')

        values_list.append(f"(:dg_id_{i}, :name_{i}, :country_{i}, :skill_{i}, :updated_at_{i})")
        params[f"dg_id_{i}"] = dg_id
        params[f"name_{i}"] = name
        params[f"country_{i}"] = country
        params[f"skill_{i}"] = skill
        params[f"updated_at_{i}"] = now

    logger.info(f"Batch upserting {len(values_list)} golfers...")
    with db.db.engine.connect() as conn:
        if DATABASE_URL.startswith("postgresql"):
            sql = f"""
                INSERT INTO golfer (datagolf_id, name, country, dg_skill, updated_at)
                VALUES {', '.join(values_list)}
                ON CONFLICT (datagolf_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    country = EXCLUDED.country,
                    dg_skill = EXCLUDED.dg_skill,
                    updated_at = EXCLUDED.updated_at
            """
            conn.execute(text(sql), params)
        else:
            sql = f"""
                INSERT OR REPLACE INTO golfer (datagolf_id, name, country, dg_skill, updated_at)
                VALUES {', '.join(values_list)}
            """
            conn.execute(text(sql), params)

        conn.commit()

    logger.info(f"Synced {len(rankings)} ranked players to database")
    return {"golfer_count": len(rankings)}
