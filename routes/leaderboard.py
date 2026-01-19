"""Leaderboard routes."""
import logging
from datetime import datetime
import time

from fasthtml.common import *
from starlette.responses import RedirectResponse

from components.layout import page_shell, card
from routes.utils import get_current_user, get_db, format_score

logger = logging.getLogger(__name__)


# Store last refresh time to rate limit (in-memory, resets on restart)
_last_refresh = {}


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


def setup_leaderboard_routes(app):
    """Register leaderboard routes."""

    @app.get("/leaderboard")
    def leaderboard_page(request, tournament_id: int = None):
        db = get_db()
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)

        # Get tournaments that can be viewed (active or completed)
        all_tournaments = list(db.tournaments())
        viewable = [t for t in all_tournaments if t.status in ('active', 'completed')]
        viewable.sort(key=lambda t: (t.status != 'active', t.start_date or ''), reverse=True)

        if not viewable:
            return page_shell(
                "Leaderboard",
                card("No Tournament", P("No tournaments available yet.")),
                user=user
            )

        # Select tournament - default to active or most recent completed
        tournament = None
        if tournament_id:
            tournament = next((t for t in viewable if t.id == tournament_id), None)
        if not tournament:
            # Default: active tournament, or most recently started completed
            active = [t for t in viewable if t.status == 'active']
            tournament = active[0] if active else viewable[0]

        # Build tournament selector
        tournament_options = [
            Option(
                f"{t.name}" + (" (Live)" if t.status == 'active' else ""),
                value=str(t.id),
                selected=(t.id == tournament.id)
            )
            for t in viewable
        ]

        tournament_selector = Div(
            Label("Tournament:", fr="tournament-select"),
            Select(
                *tournament_options,
                name="tournament_id",
                id="tournament-select",
                onchange="window.location.href='/leaderboard?tournament_id=' + this.value"
            ),
            cls="tournament-selector"
        ) if len(viewable) > 1 else None

        users_by_id = {u.id: u for u in db.users()}
        golfers_by_id = {g.id: g for g in db.golfers()}

        # Get all picks for this tournament
        all_picks = [p for p in db.picks() if p.tournament_id == tournament.id]

        # Get standings if they exist - keyed by (user_id, entry_number)
        standings = [s for s in db.pickem_standings() if s.tournament_id == tournament.id]
        standings_by_key = {(s.user_id, getattr(s, 'entry_number', 1) or 1): s for s in standings}

        # Count entries per user to know when to show entry numbers
        entries_per_user = {}
        for p in all_picks:
            entries_per_user[p.user_id] = entries_per_user.get(p.user_id, 0) + 1

        # Get results for thru info
        results = {r.golfer_id: r for r in db.tournament_results() if r.tournament_id == tournament.id}

        def get_golfer_name(golfer_id):
            g = golfers_by_id.get(golfer_id)
            return g.name if g else "-"

        # Check if tournament has any results (has it started?)
        has_results = len(results) > 0

        def pick_row(pick, rank):
            u = users_by_id.get(pick.user_id)
            entry_number = getattr(pick, 'entry_number', 1) or 1
            standing = standings_by_key.get((pick.user_id, entry_number))

            # Show entry number if user has multiple entries
            display_name = u.display_name if u else "Unknown"
            if entries_per_user.get(pick.user_id, 1) > 1:
                display_name = f"{display_name} ({entry_number})"

            def cell(golfer_id, score):
                name = get_golfer_name(golfer_id)
                result = results.get(golfer_id)

                # Determine display based on score and tournament state
                if score is None:
                    if not has_results:
                        # Tournament hasn't started yet
                        score_display = "-"
                        cls = "golfer-cell not-started"
                    elif result and result.status in ('cut', 'mc'):
                        # Actually missed the cut
                        score_display = "MC"
                        cls = "golfer-cell missed-cut"
                    elif result and result.status == 'wd':
                        score_display = "WD"
                        cls = "golfer-cell withdrawn"
                    elif result and result.status == 'dq':
                        score_display = "DQ"
                        cls = "golfer-cell disqualified"
                    elif result is None:
                        # No result for this golfer - hasn't teed off or not in field
                        score_display = "-"
                        cls = "golfer-cell not-started"
                    else:
                        # Has result but no score - still playing
                        score_display = "E"
                        cls = "golfer-cell"
                else:
                    score_display = format_score(score)
                    cls = "golfer-cell"
                    if score < 0:
                        cls += " under-par"
                    elif score > 0:
                        cls += " over-par"

                # Add thru info if available and tournament is active
                thru_info = ""
                if result and result.thru and tournament.status == 'active':
                    if result.thru == 18:
                        thru_info = " (F)"
                    else:
                        thru_info = f" ({result.thru})"

                return Td(
                    Div(
                        Span(name, cls="golfer-name-lb"),
                        Span(f"{score_display}{thru_info}", cls="golfer-score"),
                        cls="golfer-cell-content"
                    ),
                    cls=cls
                )

            # Get scores from standing (stored in tier*_position columns)
            t1_score = standing.tier1_position if standing else None
            t2_score = standing.tier2_position if standing else None
            t3_score = standing.tier3_position if standing else None
            t4_score = standing.tier4_position if standing else None

            total = standing.best_two_total if standing else None
            if not has_results:
                # Tournament hasn't started
                total_display = "-"
            elif total is None:
                # Has results but DQ (less than 2 valid scores)
                total_display = "DQ"
            else:
                total_display = format_score(total)

            rank_display = str(standing.rank) if standing and standing.rank else "-"
            is_current = u and u.id == user.id

            # Build golfer detail rows for mobile expandable view
            def golfer_detail(tier_num, golfer_id, score):
                name = get_golfer_name(golfer_id)
                result = results.get(golfer_id)

                if score is None:
                    if not has_results:
                        score_display = "-"
                    elif result and result.status in ('cut', 'mc'):
                        score_display = "MC"
                    elif result and result.status == 'wd':
                        score_display = "WD"
                    elif result and result.status == 'dq':
                        score_display = "DQ"
                    elif result is None:
                        score_display = "-"
                    else:
                        score_display = "E"
                else:
                    score_display = format_score(score)

                thru_info = ""
                if result and result.thru and tournament.status == 'active':
                    if result.thru == 18:
                        thru_info = " (F)"
                    else:
                        thru_info = f" ({result.thru})"

                score_cls = ""
                if score is not None:
                    if score < 0:
                        score_cls = "under-par"
                    elif score > 0:
                        score_cls = "over-par"
                elif result and result.status in ('cut', 'mc'):
                    score_cls = "missed-cut"

                return Div(
                    Span(f"T{tier_num}", cls="detail-tier"),
                    Span(name, cls="detail-name"),
                    Span(f"{score_display}{thru_info}", cls=f"detail-score {score_cls}"),
                    cls="golfer-detail-row"
                )

            # Mobile expandable card (hidden on desktop, shown on mobile via CSS)
            mobile_card = Div(
                Details(
                    Summary(
                        Span(rank_display, cls="card-rank"),
                        Span(display_name, cls="card-player"),
                        Span(total_display, cls="card-total"),
                    ),
                    Div(
                        golfer_detail(1, pick.tier1_golfer_id, t1_score),
                        golfer_detail(2, pick.tier2_golfer_id, t2_score),
                        golfer_detail(3, pick.tier3_golfer_id, t3_score),
                        golfer_detail(4, pick.tier4_golfer_id, t4_score),
                        cls="golfer-details"
                    ),
                ),
                cls=f"leaderboard-card {'current-user-card' if is_current else ''}"
            )

            # Desktop table row (hidden on mobile via CSS)
            desktop_row = Tr(
                Td(rank_display, cls="rank"),
                Td(display_name, cls="player-name"),
                cell(pick.tier1_golfer_id, t1_score),
                cell(pick.tier2_golfer_id, t2_score),
                cell(pick.tier3_golfer_id, t3_score),
                cell(pick.tier4_golfer_id, t4_score),
                Td(total_display, cls="total"),
                cls=f"desktop-row {'current-user' if is_current else ''}"
            )

            return (desktop_row, mobile_card)

        # Sort by standings if available, otherwise just show picks
        # DQ entries (None total) sort to bottom
        if standings:
            def get_sort_key(p):
                entry_num = getattr(p, 'entry_number', 1) or 1
                s = standings_by_key.get((p.user_id, entry_num))
                if s and s.best_two_total is not None:
                    return (False, s.best_two_total)
                return (True, 0)  # DQ entries go last
            all_picks.sort(key=get_sort_key)

        # Status indicator
        status_badge = None
        if tournament.status == 'active':
            status_badge = Span("Live", cls="badge badge-live")
        elif tournament.status == 'completed':
            status_badge = Span("Final", cls="badge badge-final")

        # Build rows and cards
        if all_picks:
            rows_and_cards = [pick_row(p, i+1) for i, p in enumerate(all_picks)]
            desktop_rows = [r[0] for r in rows_and_cards]
            mobile_cards = [r[1] for r in rows_and_cards]
        else:
            desktop_rows = []
            mobile_cards = []

        return page_shell(
            "Leaderboard",
            Div(
                Div(
                    Div(
                        H1(f"Leaderboard: {tournament.name}"),
                        status_badge,
                        cls="leaderboard-title"
                    ),
                    tournament_selector,
                    cls="leaderboard-header"
                ),
                P("Best 2 of 4 scores against par. Lowest total wins."),
                # Desktop table (hidden on mobile)
                Table(
                    Thead(
                        Tr(
                            Th("Rank"), Th("Player"),
                            Th("Tier 1"), Th("Tier 2"), Th("Tier 3"), Th("Tier 4"),
                            Th("Best 2", cls="total-header")
                        )
                    ),
                    Tbody(*desktop_rows),
                    cls="leaderboard-table desktop-only"
                ) if all_picks else None,
                # Mobile cards (hidden on desktop)
                Div(
                    *mobile_cards,
                    cls="leaderboard-cards mobile-only"
                ) if all_picks else None,
                P("No picks yet for this tournament.") if not all_picks else None,
                A("Make Picks", href="/picks", cls="btn btn-primary") if tournament.status == 'active' else None,
                cls="leaderboard-page"
            ),
            user=user
        )

    @app.post("/leaderboard/refresh")
    def refresh_scores(request, tournament_id: int):
        """Refresh scores from DataGolf API - rate limited to once per minute."""
        db = get_db()
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)

        global _last_refresh
        now = time.time()
        last = _last_refresh.get(tournament_id, 0)

        if now - last < 60:  # 60 seconds
            # Too soon, just redirect back
            return RedirectResponse(f"/leaderboard?tournament_id={tournament_id}", status_code=303)

        # Get tournament to validate
        tournament = None
        for t in db.tournaments():
            if t.id == tournament_id:
                tournament = t
                break

        if not tournament:
            return RedirectResponse("/leaderboard", status_code=303)

        # Do the sync
        from services.datagolf import DataGolfClient
        from services.scoring import ScoringService

        client = DataGolfClient()
        scoring = ScoringService(db)

        try:
            live_data = client.get_live_stats()

            # Validate tournament name matches
            api_event_name = live_data.get('event_name', '')
            if not _tournament_names_match(tournament.name, api_event_name):
                logger.warning(f"Refresh skipped: API returning '{api_event_name}', not '{tournament.name}'")
                return RedirectResponse(f"/leaderboard?tournament_id={tournament_id}", status_code=303)

            _last_refresh[tournament_id] = now

            live_stats = live_data.get('live_stats', [])
            golfers_by_dg_id = {g.datagolf_id: g for g in db.golfers()}

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

                score_to_par = player.get('total')
                thru = player.get('thru')
                round_num = player.get('round')

                existing = [r for r in db.tournament_results()
                            if r.tournament_id == tournament_id and r.golfer_id == golfer.id]

                if existing:
                    db.tournament_results.update(
                        id=existing[0].id,
                        position=position,
                        score_to_par=score_to_par,
                        status=status,
                        round_num=round_num,
                        thru=thru,
                        updated_at=datetime.now().isoformat()
                    )
                else:
                    db.tournament_results.insert(
                        tournament_id=tournament_id,
                        golfer_id=golfer.id,
                        position=position,
                        score_to_par=score_to_par,
                        status=status,
                        round_num=round_num,
                        thru=thru,
                        updated_at=datetime.now().isoformat()
                    )

            scoring.calculate_standings(tournament_id)
        except Exception as e:
            logger.error(f"Refresh error: {e}", exc_info=True)

        return RedirectResponse(f"/leaderboard?tournament_id={tournament_id}", status_code=303)


def get_last_sync_time(tournament_id: int):
    """Get the most recent update time for tournament results."""
    db = get_db()
    results = [r for r in db.tournament_results() if r.tournament_id == tournament_id]
    if not results:
        return None
    times = [r.updated_at for r in results if r.updated_at]
    return max(times) if times else None


def format_time_ago(iso_time: str) -> str:
    """Format ISO timestamp as 'X minutes ago'."""
    if not iso_time:
        return "Never"
    try:
        updated = datetime.fromisoformat(iso_time)
        now = datetime.now()
        diff = now - updated
        minutes = int(diff.total_seconds() / 60)
        if minutes < 1:
            return "Just now"
        elif minutes == 1:
            return "1 minute ago"
        elif minutes < 60:
            return f"{minutes} minutes ago"
        else:
            hours = minutes // 60
            if hours == 1:
                return "1 hour ago"
            else:
                return f"{hours} hours ago"
    except:
        return "Unknown"
