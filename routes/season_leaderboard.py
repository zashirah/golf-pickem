"""Season leaderboard routes."""
import logging
from datetime import datetime

from fasthtml.common import *
from starlette.responses import RedirectResponse

from components.layout import page_shell, card
from routes.utils import get_current_user, get_db, format_score

logger = logging.getLogger(__name__)


def get_season_standings(db, season_year=None):
    """Query season standings view for a specific year or all years.

    Args:
        db: Database module
        season_year: Optional year string (e.g., "2024"). If None, returns all years.

    Returns:
        List of season standing records
    """
    import sqlalchemy as sa

    query = "SELECT * FROM season_standings_view"
    params = {}

    if season_year:
        query += " WHERE season_year = :year"
        params['year'] = str(season_year)

    query += " ORDER BY average_score ASC"  # Lowest average score wins

    try:
        result = list(db.db.conn.execute(sa.text(query), params))
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

    try:
        # Query for distinct years from the view
        query = "SELECT DISTINCT season_year FROM season_standings_view ORDER BY season_year DESC"
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
        prev_score = None
        for i, standing in enumerate(standings):
            # Convert row to dict
            standing_dict = dict(standing._mapping) if hasattr(standing, '_mapping') else dict(standing)

            # If average score is different from previous, update rank
            if prev_score is None or standing_dict['average_score'] != prev_score:
                current_rank = i + 1

            ranked_standings.append({
                'rank': current_rank,
                **standing_dict
            })
            prev_score = standing_dict['average_score']

        # Count tournaments for this year
        import sqlalchemy as sa
        tournaments = list(db.db.conn.execute(
            sa.text("""SELECT COUNT(*) as count FROM tournament
               WHERE status = 'completed'
               AND strftime('%Y', start_date) = :year"""),
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
            # Format average score
            avg_score = format_score(int(s['average_score'])) if s['average_score'] is not None else "-"
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
                Td(avg_score, cls="total"),
                Td(str(s['tournaments_played']), cls="text-center"),
                Td(top_finishes, cls="text-center compact"),
                Td(avg_pos, cls="text-center"),
                Td(best_finish, cls="text-center"),
                Td(winnings, cls="text-right"),
                cls=f"{'current-user' if is_current else ''}"
            )

        # Build mobile cards
        def standing_card(s):
            """Create a mobile card for a season standing."""
            avg_score = format_score(int(s['average_score'])) if s['average_score'] is not None else "-"
            winnings = f"${s['total_winnings']:.0f}" if s['total_winnings'] and s['total_winnings'] > 0 else "-"
            avg_pos = f"{s['average_position']:.1f}" if s['average_position'] is not None else "-"

            is_current = user and s['user_id'] == user.id

            return Div(
                Div(
                    Span(f"#{s['rank']}", cls="card-rank"),
                    Span(s['display_name'] or f"User {s['user_id']}", cls="card-player"),
                    cls="card-header"
                ),
                Div(
                    Div(
                        Span("Avg Score:", cls="label"),
                        Span(avg_score, cls="value"),
                        cls="card-stat"
                    ),
                    Div(
                        Span("Tournaments:", cls="label"),
                        Span(str(s['tournaments_played']), cls="value"),
                        cls="card-stat"
                    ),
                    Div(
                        Span("Wins:", cls="label"),
                        Span(str(s['wins']), cls="value"),
                        cls="card-stat"
                    ),
                    Div(
                        Span("Avg Pos:", cls="label"),
                        Span(avg_pos, cls="value"),
                        cls="card-stat"
                    ),
                    Div(
                        Span("Winnings:", cls="label"),
                        Span(winnings, cls="value"),
                        cls="card-stat"
                    ),
                    cls="card-stats"
                ),
                cls=f"season-card {'current-user-card' if is_current else ''}"
            )

        # Build table rows and mobile cards
        desktop_rows = [standing_row(s) for s in ranked_standings]
        mobile_cards = [standing_card(s) for s in ranked_standings]

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
            P("Lowest average score wins. Stats include all completed tournaments in the calendar year.", cls="season-description"),
            # Desktop table
            Table(
                Thead(
                    Tr(
                        Th("Rank"),
                        Th("Player"),
                        Th("Avg Score", title="Average score across all tournaments"),
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
            # Mobile cards
            Div(
                *mobile_cards,
                cls="season-cards mobile-only"
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
