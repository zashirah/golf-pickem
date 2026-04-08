"""ETL: Auto-assign tournament field tiers from DataGolf field data."""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def auto_assign_field(db, datagolf_client, tournament_id) -> dict:
    """Auto-assign golfer tiers from DataGolf field for a tournament.

    Tier assignment by dg_skill rank:
      Tier 1: top 6
      Tier 2: next 18 (ranks 7-24)
      Tier 3: next 36 (ranks 25-60)
      Tier 4: remainder

    Creates any golfers found in the DataGolf field that are missing from the DB.

    Raises:
        ValueError: if tournament not found or DataGolf event name doesn't match.

    Returns dict with 'assigned_count' and 'created_count' keys.
    """
    from sqlalchemy import text

    tournament = None
    for t in db.tournaments():
        if t.id == tournament_id:
            tournament = t
            break

    if not tournament:
        raise ValueError(f"Tournament {tournament_id} not found")

    field_data = datagolf_client.get_field_updates()
    dg_event_name = field_data.get('event_name', '')
    field_players = field_data.get('field', [])

    if not tournament.datagolf_name or tournament.datagolf_name != dg_event_name:
        raise ValueError(
            f"Tournament mismatch: DB='{tournament.datagolf_name}' vs DataGolf='{dg_event_name}'"
        )

    golfers_by_dg_id = {g.datagolf_id: g for g in db.golfers()}

    # Create any golfers in the field that are missing from the DB
    golfers_to_create = [
        p for p in field_players
        if str(p.get('dg_id', '')) and str(p.get('dg_id', '')) not in golfers_by_dg_id
    ]

    created_count = 0
    if golfers_to_create:
        now = datetime.now().isoformat()
        values_list = []
        params = {}
        for i, p in enumerate(golfers_to_create):
            dg_id = str(p.get('dg_id', ''))
            raw_name = p.get('player_name', '')
            if ', ' in raw_name:
                last, first = raw_name.split(', ', 1)
                name = f"{first} {last}"
            else:
                name = raw_name
            country = p.get('country', '')

            values_list.append(f"(:dg_id_{i}, :name_{i}, :country_{i}, :updated_at_{i})")
            params[f"dg_id_{i}"] = dg_id
            params[f"name_{i}"] = name
            params[f"country_{i}"] = country
            params[f"updated_at_{i}"] = now

        logger.info(f"Creating {len(golfers_to_create)} missing golfers from field...")
        with db.db.engine.connect() as conn:
            sql = f"""
                INSERT INTO golfer (datagolf_id, name, country, updated_at)
                VALUES {', '.join(values_list)}
                ON CONFLICT (datagolf_id) DO NOTHING
            """
            conn.execute(text(sql), params)
            conn.commit()

        # Refresh lookup after creating new golfers
        golfers_by_dg_id = {g.datagolf_id: g for g in db.golfers()}
        created_count = len(golfers_to_create)
        logger.info(f"Created {created_count} golfers")

    # Match field players to DB golfers and sort by skill
    field_with_skill = []
    for p in field_players:
        dg_id = str(p.get('dg_id', ''))
        golfer = golfers_by_dg_id.get(dg_id)
        if golfer:
            field_with_skill.append(golfer)
        else:
            logger.warning(
                f"Skipped golfer not in DB: {p.get('player_name', 'Unknown')} (dg_id: {dg_id})"
            )

    field_with_skill.sort(key=lambda g: g.dg_skill or 0, reverse=True)

    now = datetime.now().isoformat()
    field_data_list = []
    for i, golfer in enumerate(field_with_skill):
        if i < 6:
            tier = 1
        elif i < 24:
            tier = 2
        elif i < 60:
            tier = 3
        else:
            tier = 4
        field_data_list.append((tournament_id, golfer.id, tier, now))

    logger.info(
        f"Batch assigning {len(field_data_list)} golfers to tiers for tournament {tournament_id}..."
    )
    with db.db.engine.connect() as conn:
        conn.execute(
            text("DELETE FROM tournament_field WHERE tournament_id = :tid"),
            {"tid": tournament_id}
        )

        if field_data_list:
            values_list = []
            params = {}
            for i, (t_id, g_id, tier, created) in enumerate(field_data_list):
                values_list.append(f"(:tid_{i}, :gid_{i}, :tier_{i}, :created_{i})")
                params[f"tid_{i}"] = t_id
                params[f"gid_{i}"] = g_id
                params[f"tier_{i}"] = tier
                params[f"created_{i}"] = created

            sql = f"""
                INSERT INTO tournament_field (tournament_id, golfer_id, tier, created_at)
                VALUES {', '.join(values_list)}
            """
            conn.execute(text(sql), params)
        conn.commit()

    logger.info(f"Assigned {len(field_data_list)} golfers to tiers")
    return {"assigned_count": len(field_data_list), "created_count": created_count}
