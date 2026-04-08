"""ETL: Sync tournament schedule from DataGolf into DB."""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def sync_tournaments(db, datagolf_client) -> dict:
    """Sync tournament schedule from DataGolf into DB.

    Only updates name/start_date/datagolf_name for existing tournaments;
    preserves admin-set fields (status, picks_locked, pricing, etc.).
    Returns dict with 'tournament_count' key.
    """
    from sqlalchemy import text
    from config import DATABASE_URL

    logger.info("Fetching tournament schedule...")
    schedule = datagolf_client.get_schedule()
    logger.info(f"Fetched {len(schedule)} tournaments from schedule")

    now = datetime.now().isoformat()
    tournament_values = []
    tournament_params = {}
    for i, event in enumerate(schedule):
        event_id = str(event.get('event_id', ''))
        name = event.get('event_name', '')
        start = event.get('start_date', '')

        tournament_values.append(
            f"(:event_id_{i}, :dg_name_{i}, :name_{i}, :start_{i}, 'upcoming', :created_at_{i})"
        )
        tournament_params[f"event_id_{i}"] = event_id
        tournament_params[f"dg_name_{i}"] = name
        tournament_params[f"name_{i}"] = name
        tournament_params[f"start_{i}"] = start
        tournament_params[f"created_at_{i}"] = now

    if tournament_values:
        with db.db.engine.connect() as conn:
            if DATABASE_URL.startswith("postgresql"):
                sql = f"""
                    INSERT INTO tournament (datagolf_id, datagolf_name, name, start_date, status, created_at)
                    VALUES {', '.join(tournament_values)}
                    ON CONFLICT (datagolf_id) DO UPDATE SET
                        datagolf_name = EXCLUDED.datagolf_name,
                        name = EXCLUDED.name,
                        start_date = EXCLUDED.start_date
                """
                conn.execute(text(sql), tournament_params)
            else:
                # SQLite: preserve admin-set fields on conflict
                insert_sql = f"""
                    INSERT OR IGNORE INTO tournament (datagolf_id, datagolf_name, name, start_date, status, created_at)
                    VALUES {', '.join(tournament_values)}
                """
                conn.execute(text(insert_sql), tournament_params)

                # Update only name/dates for existing rows
                for i, event in enumerate(schedule):
                    event_id = str(event.get('event_id', ''))
                    name = event.get('event_name', '')
                    start = event.get('start_date', '')
                    update_sql = """
                        UPDATE tournament
                        SET datagolf_name = ?, name = ?, start_date = ?
                        WHERE datagolf_id = ?
                    """
                    conn.execute(text(update_sql), [name, name, start, event_id])

            conn.commit()

    logger.info(f"Sync complete: {len(schedule)} tournaments")
    return {"tournament_count": len(schedule)}
