"""Season leaderboard routes."""
import logging
from datetime import datetime

from fasthtml.common import *
from starlette.responses import RedirectResponse

from components.layout import page_shell, card
from routes.utils import get_current_user, get_db, format_score

logger = logging.getLogger(__name__)


def get_season_standings(db, season_year=None):
    """Query season standings for a specific year or all years.

    Computes season aggregates (total score, wins, top finishes, etc.) from raw tournament data.

    Args:
        db: Database module
        season_year: Optional year string (e.g., "2024"). If None, returns all years.

    Returns:
        List of season standing records
    """
    import sqlalchemy as sa

    # Build the query dynamically - compute aggregates on the fly without a VIEW
    query = """
    WITH tournament_purses AS (
        -- Calculate actual purse per tournament accounting for 3-pack pricing
        -- For each user, determine if they paid entry_price or three_entry_price
        SELECT
            t.id as tournament_id,
            t.entry_price,
            t.three_entry_price,
            SUM(CASE
                WHEN user_max_entries >= 3 AND t.three_entry_price > 0
                THEN t.three_entry_price
                ELSE user_max_entries * t.entry_price
            END) as total_purse
        FROM tournament t
        LEFT JOIN (
            SELECT tournament_id, user_id, MAX(entry_number) as user_max_entries
            FROM pick
            GROUP BY tournament_id, user_id
        ) entry_counts ON t.id = entry_counts.tournament_id
        WHERE t.status = 'completed'
          AND entry_counts.user_id IS NOT NULL
        GROUP BY t.id, t.entry_price, t.three_entry_price
    ),
    wins AS (
        -- Calculate winnings for tournaments won (rank = 1)
        SELECT
            ps.user_id,
            ps.tournament_id,
            tp.total_purse as winnings
        FROM pickem_standing ps
        JOIN tournament_purses tp ON ps.tournament_id = tp.tournament_id
        WHERE ps.rank = 1
          AND ps.user_id IS NOT NULL
    ),
    standings AS (
        SELECT
            EXTRACT(YEAR FROM t.start_date::date)::text as season_year,
            u.id as user_id,
            u.display_name,
            COUNT(DISTINCT p.tournament_id) as tournaments_played,
            COUNT(ps.id) as total_entries,
            SUM(CASE WHEN ps.best_two_total IS NOT NULL THEN ps.best_two_total ELSE 0 END) as total_score,
            SUM(CASE WHEN ps.rank = 1 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN ps.rank <= 3 THEN 1 ELSE 0 END) as top3_finishes,
            SUM(CASE WHEN ps.rank <= 5 THEN 1 ELSE 0 END) as top5_finishes,
            SUM(CASE WHEN ps.rank <= 10 THEN 1 ELSE 0 END) as top10_finishes,
            AVG(CAST(ps.rank AS DECIMAL)) as average_position,
            MIN(ps.rank) as best_finish,
            COALESCE(SUM(w.winnings), 0)::DECIMAL as total_winnings
        FROM "user" u
        JOIN pick p ON u.id = p.user_id
        JOIN tournament t ON p.tournament_id = t.id
        LEFT JOIN pickem_standing ps ON u.id = ps.user_id AND p.tournament_id = ps.tournament_id
        LEFT JOIN wins w ON u.id = w.user_id AND t.id = w.tournament_id
        WHERE t.status = 'completed'
        GROUP BY EXTRACT(YEAR FROM t.start_date::date), u.id, u.display_name
    )
    SELECT * FROM standings
    """

    if season_year:
        query += f" WHERE season_year = '{season_year}'"

    query += " ORDER BY total_winnings DESC, average_position ASC"

    try:
        result = list(db.db.conn.execute(sa.text(query)))
        return result
    except Exception as e:
        logger.error(f"Error querying season standings: {e}", exc_info=True)
        return []


def get_available_years(db):
    """Get list of distinct years that have completed tournaments.

    Returns:
        List of year strings in descending order (most recent first)
    """
    import sqlalchemy as sa

    query = """
    SELECT DISTINCT EXTRACT(YEAR FROM t.start_date::date)::text as season_year
    FROM tournament t
    WHERE t.status = 'completed'
    ORDER BY season_year DESC
    """

    try:
        result = list(db.db.conn.execute(sa.text(query)))
        return [row[0] for row in result if row[0]]
    except Exception as e:
        logger.error(f"Error getting available years: {e}", exc_info=True)
        return []


def setup_season_leaderboard_routes(app):
    """Register season leaderboard routes."""

    @app.get("/season-leaderboard")
    def season_leaderboard_page(request, year: str = None):
        """Display season-long leaderboard for a specific year or current year."""
        db = get_db()
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)

        # Get available years
        available_years = get_available_years(db)

        if not available_years:
            return page_shell(
                "Season Leaderboard",
                card(
                    "No Season Data",
                    P("No completed tournaments yet. Season standings will appear once tournaments are completed.")
                ),
                user=user
            )

        # Default to current year or most recent year with data
        current_year = str(datetime.now().year)
        if not year:
            year = current_year if current_year in available_years else available_years[0]

        # Get standings for selected year
        standings = get_season_standings(db, year)

        # Calculate rank for each entry (handle ties by showing same rank)
        ranked_standings = []
        current_rank = 1
        prev_winnings = None
        prev_avg_pos = None
        for i, standing in enumerate(standings):
            # Convert row to dict
            standing_dict = dict(standing._mapping) if hasattr(standing, '_mapping') else dict(standing)

            # If winnings or average position is different from previous, update rank
            current_winnings = standing_dict.get('total_winnings')
            current_avg_pos = standing_dict.get('average_position')
            if prev_winnings is None or current_winnings != prev_winnings or current_avg_pos != prev_avg_pos:
                current_rank = i + 1

            ranked_standings.append({
                'rank': current_rank,
                **standing_dict
            })
            prev_winnings = current_winnings
            prev_avg_pos = current_avg_pos

        # Count tournaments for this year
        import sqlalchemy as sa
        tournaments = list(db.db.conn.execute(
            sa.text("""SELECT COUNT(*) as count FROM tournament
               WHERE status = 'completed'
               AND EXTRACT(YEAR FROM start_date::date)::text = :year"""),
            {'year': year}
        ))
        tournament_count = tournaments[0][0] if tournaments else 0

        # Build year selector
        year_options = [
            Option(
                y,
                value=y,
                selected=(y == year)
            )
            for y in available_years
        ]

        year_selector = Div(
            Label("Season:", fr="year-select"),
            Select(
                *year_options,
                name="year",
                id="year-select",
                onchange="window.location.href='/season-leaderboard?year=' + this.value"
            ),
            cls="season-selector"
        ) if len(available_years) > 1 else None

        # Build leaderboard rows
        def standing_row(s):
            """Create a table row for a season standing."""
            avg_pos = f"{s['average_position']:.1f}" if s['average_position'] is not None else "-"
            best_finish = str(s['best_finish']) if s['best_finish'] is not None else "-"

            # Format winnings
            winnings = f"${s['total_winnings']:.0f}" if s['total_winnings'] and s['total_winnings'] > 0 else "-"

            # Compact top finishes format: "wins/top3/top5/top10"
            top_finishes = f"{s['wins']}/{s['top3_finishes']}/{s['top5_finishes']}/{s['top10_finishes']}"

            # Check if current user
            is_current = user and s['user_id'] == user.id

            return Tr(
                Td(str(s['rank']), cls="rank"),
                Td(s['display_name'] or f"User {s['user_id']}", cls="player-name"),
                Td(str(s['tournaments_played']), cls="text-center"),
                Td(top_finishes, cls="text-center compact"),
                Td(avg_pos, cls="text-center"),
                Td(best_finish, cls="text-center"),
                Td(winnings, cls="text-right"),
                cls=f"{'current-user' if is_current else ''}"
            )

        # Build table rows
        desktop_rows = [standing_row(s) for s in ranked_standings]

        # Build content
        content = Div(
            Div(
                H1(f"{year} Season Leaderboard"),
                Span(f"📊 {tournament_count} Tournament{'s' if tournament_count != 1 else ''} Completed", cls="tournament-count"),
                cls="season-header"
            ),
            Div(
                year_selector,
                cls="season-controls"
            ),
            P("Stats include all completed tournaments in the calendar year.", cls="season-description"),
            # Season leaderboard table
            Table(
                Thead(
                    Tr(
                        Th("Rank"),
                        Th("Player"),
                        Th("Tournaments", cls="text-center"),
                        Th("W/T3/T5/T10", cls="text-center", title="Wins / Top 3 / Top 5 / Top 10"),
                        Th("Avg Pos", cls="text-center", title="Average Position"),
                        Th("Best", cls="text-center", title="Best Finish"),
                        Th("Winnings", cls="text-right")
                    )
                ),
                Tbody(*desktop_rows),
                cls="leaderboard-table season-table"
            ) if ranked_standings else None,
            # Empty state
            P("No standings for this season yet.") if not ranked_standings else None,
            cls="season-leaderboard-page"
        )

        return page_shell(
            "Season Leaderboard",
            content,
            user=user
        )
