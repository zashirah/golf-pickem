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


def _build_tournament_leaderboard(db, tournament, results, golfers_by_id):
    """Build the tournament leaderboard showing actual golfer results."""
    
    # Sort results by position (None positions go to bottom)
    sorted_results = sorted(
        results.values(),
        key=lambda r: (
            r.position is None,  # None positions at bottom
            r.position or 999,   # Sort by position
            r.score_to_par or 999  # Then by score
        )
    )
    
    logger.info(f"Building tournament leaderboard with {len(sorted_results)} results")
    
    if not sorted_results:
        return P("No tournament results yet. Results will appear once the tournament starts.")
    
    def golfer_row(result):
        golfer = golfers_by_id.get(result.golfer_id)
        name = golfer.name if golfer else "Unknown"
        
        # Position display
        if result.position:
            pos_display = f"T{result.position}" if result.position else str(result.position)
        elif result.status == 'cut':
            pos_display = "MC"
        elif result.status == 'wd':
            pos_display = "WD"
        elif result.status == 'dq':
            pos_display = "DQ"
        else:
            pos_display = "-"
        
        # Score display
        if result.score_to_par is not None:
            if result.score_to_par == 0:
                score_display = "E"
            elif result.score_to_par > 0:
                score_display = f"+{result.score_to_par}"
            else:
                score_display = str(result.score_to_par)
        else:
            score_display = "-"
        
        # Thru display
        if result.thru is not None:
            if result.thru == 18:
                thru_display = "F"
            else:
                thru_display = str(result.thru)
        else:
            thru_display = "-"
        
        # Score class for coloring
        score_cls = ""
        if result.score_to_par is not None:
            if result.score_to_par < 0:
                score_cls = "under-par"
            elif result.score_to_par > 0:
                score_cls = "over-par"
        if result.status in ('cut', 'wd', 'dq'):
            score_cls = "missed-cut"
        
        return Tr(
            Td(pos_display, cls="rank"),
            Td(name, cls="player-name"),
            Td(score_display, cls=f"score {score_cls}"),
            Td(thru_display),
        )
    
    # Build mobile cards too
    def golfer_card(result):
        golfer = golfers_by_id.get(result.golfer_id)
        name = golfer.name if golfer else "Unknown"
        
        if result.position:
            pos_display = f"T{result.position}" if result.position else str(result.position)
        elif result.status == 'cut':
            pos_display = "MC"
        elif result.status == 'wd':
            pos_display = "WD"
        elif result.status == 'dq':
            pos_display = "DQ"
        else:
            pos_display = "-"
        
        if result.score_to_par is not None:
            if result.score_to_par == 0:
                score_display = "E"
            elif result.score_to_par > 0:
                score_display = f"+{result.score_to_par}"
            else:
                score_display = str(result.score_to_par)
        else:
            score_display = "-"
        
        thru_display = "F" if result.thru == 18 else (str(result.thru) if result.thru else "-")
        
        score_cls = ""
        if result.score_to_par is not None:
            if result.score_to_par < 0:
                score_cls = "under-par"
            elif result.score_to_par > 0:
                score_cls = "over-par"
        if result.status in ('cut', 'wd', 'dq'):
            score_cls = "missed-cut"
        
        return Div(
            Span(pos_display, cls="card-rank"),
            Span(name, cls="card-player"),
            Span(score_display, cls=f"card-score {score_cls}"),
            Span(thru_display, cls="card-thru"),
            cls="tournament-card"
        )
    
    desktop_rows = [golfer_row(r) for r in sorted_results[:50]]  # Top 50
    mobile_cards = [golfer_card(r) for r in sorted_results[:50]]
    
    return Div(
        P(f"Showing top {min(50, len(sorted_results))} of {len(sorted_results)} golfers", cls="tournament-count"),
        # Desktop table - use same class as pick'em leaderboard
        Table(
            Thead(
                Tr(
                    Th("Pos"), Th("Player"), Th("Score"), Th("Thru")
                )
            ),
            Tbody(*desktop_rows),
            cls="leaderboard-table"
        ),
    )


def setup_leaderboard_routes(app):
    """Register leaderboard routes."""

    @app.get("/leaderboard")
    def leaderboard_page(request, tournament_id: int = None, message: str = None, view: str = "pickem"):
        db = get_db()
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)

        # Import alert for message display (will be set after auto-sync)
        from components.layout import alert
        
        # Validate view parameter
        if view not in ("pickem", "tournament"):
            view = "pickem"

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

        # Auto-sync if active tournament and >10 minutes since last sync
        should_auto_sync = False
        if tournament.status == 'active':
            if not tournament.last_synced_at:
                should_auto_sync = True
            else:
                try:
                    last_sync = datetime.fromisoformat(tournament.last_synced_at.replace('Z', '+00:00'))
                    minutes_since = (datetime.now() - last_sync).total_seconds() / 60
                    if minutes_since > 10:
                        should_auto_sync = True
                except:
                    pass
        
        # Auto-sync tracking variable
        auto_sync_message = None
        
        if should_auto_sync:
            logger.info(f"Auto-syncing {tournament.name} (>10 min since last sync)")
            try:
                from services.datagolf import DataGolfClient
                from services.scoring import ScoringService
                from sqlalchemy import text
                
                client = DataGolfClient()
                scoring = ScoringService(db)
                
                live_data = client.get_live_stats()
                api_event_name = live_data.get('event_name', '')
                
                # Only sync if tournament matches
                if _tournament_names_match(tournament.name, api_event_name):
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
                            'tournament_id': tournament.id,
                            'golfer_id': golfer.id,
                            'position': position,
                            'score_to_par': player.get('total'),
                            'status': status,
                            'round_num': player.get('round'),
                            'thru': player.get('thru'),
                            'updated_at': now
                        })
                    
                    if results_data:
                        with db.db.engine.connect() as conn:
                            conn.execute(text("DELETE FROM tournament_result WHERE tournament_id = :tid"), 
                                        {"tid": tournament.id})
                            
                            values_list = []
                            params = {}
                            for i, r in enumerate(results_data):
                                values_list.append(f"(:tid_{i}, :gid_{i}, :pos_{i}, :score_{i}, :status_{i}, :round_{i}, :thru_{i}, :updated_{i})")
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
                        
                        db.tournaments.update(id=tournament.id, last_synced_at=now)
                        scoring.calculate_standings(tournament.id)
                        logger.info(f"Auto-sync complete: {len(results_data)} results")
                        
                        # Reload tournament to get updated last_synced_at
                        tournament = next((t for t in db.tournaments() if t.id == tournament.id), tournament)
                else:
                    # Tournament doesn't match - set a message to inform the user
                    auto_sync_message = f"Live scores are for '{api_event_name}', not '{tournament.name}'"
                    logger.info(f"Auto-sync skipped: tournament mismatch ({api_event_name} vs {tournament.name})")
            except Exception as e:
                logger.error(f"Auto-sync failed: {e}", exc_info=True)

        # Create alert for any messages (from URL or auto-sync)
        display_message = message or auto_sync_message
        message_alert = alert(display_message, "warning") if display_message else None

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

        # Last sync info
        sync_info = None
        if tournament.last_synced_at:
            try:
                last_sync = datetime.fromisoformat(tournament.last_synced_at.replace('Z', '+00:00'))
                minutes_ago = int((datetime.now() - last_sync).total_seconds() / 60)
                if minutes_ago < 1:
                    sync_text = "Updated just now"
                elif minutes_ago == 1:
                    sync_text = "Updated 1 minute ago"
                else:
                    sync_text = f"Updated {minutes_ago} minutes ago"
                sync_info = Span(sync_text, cls="sync-info")
            except:
                sync_info = Span("Sync time unavailable", cls="sync-info")
        elif tournament.status == 'active':
            sync_info = Span("Never synced", cls="sync-info")

        # Refresh button (for active tournaments)
        refresh_button = None
        if tournament.status == 'active' and user.is_admin:
            refresh_button = Form(
                Button("🔄 Refresh Scores", type="submit", cls="btn btn-sm btn-primary"),
                Input(type="hidden", name="tournament_id", value=str(tournament.id)),
                action="/leaderboard/refresh",
                method="post",
                style="display:inline;"
            )

        # Send to GroupMe button (for admins)
        groupme_send_button = None
        if user.is_admin:
            groupme_send_button = Form(
                Button("💬 Send to GroupMe", type="submit", cls="btn btn-sm btn-info"),
                Input(type="hidden", name="tournament_id", value=str(tournament.id)),
                action="/leaderboard/send-groupme",
                method="post",
                style="display:inline; margin-left: 0.5rem;"
            )

        # Build rows and cards
        if all_picks:
            rows_and_cards = [pick_row(p, i+1) for i, p in enumerate(all_picks)]
            desktop_rows = [r[0] for r in rows_and_cards]
            mobile_cards = [r[1] for r in rows_and_cards]
        else:
            desktop_rows = []
            mobile_cards = []

        # Build tabs for switching views
        base_url = f"/leaderboard?tournament_id={tournament.id}"
        tabs = Div(
            A("Pick'em Standings", href=f"{base_url}&view=pickem", 
              cls=f"tab {'tab-active' if view == 'pickem' else ''}"),
            A("Tournament Leaderboard", href=f"{base_url}&view=tournament",
              cls=f"tab {'tab-active' if view == 'tournament' else ''}"),
            cls="tabs"
        )

        # Build content based on view
        if view == "tournament":
            # Tournament leaderboard - show actual golfer results
            tournament_content = _build_tournament_leaderboard(db, tournament, results, golfers_by_id)
        else:
            # Pick'em standings (default)
            tournament_content = Div(
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
            )

        # Calculate purse for header display
        from routes.utils import calculate_tournament_purse
        purse = calculate_tournament_purse(tournament, all_picks)
        purse_display = P(Strong("💰 Purse: "), f"${purse}") if purse else None

        return page_shell(
            "Leaderboard",
            Div(
                message_alert,
                Div(
                    Div(
                        H1(f"Leaderboard: {tournament.name}"),
                        status_badge,
                        purse_display,
                        cls="leaderboard-title"
                    ),
                    Div(
                        tournament_selector,
                        Div(
                            sync_info,
                            refresh_button,
                            groupme_send_button,
                            style="display: flex; gap: 10px; align-items: center;"
                        ) if sync_info or refresh_button or groupme_send_button else None,
                        cls="leaderboard-controls"
                    ),
                    cls="leaderboard-header"
                ),
                tabs,
                tournament_content,
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

        from urllib.parse import quote

        global _last_refresh
        now = time.time()
        last = _last_refresh.get(tournament_id, 0)

        if now - last < 60:  # 60 seconds
            # Too soon, just redirect back
            return RedirectResponse(f"/leaderboard?tournament_id={tournament_id}&message={quote('Please wait 60 seconds between refreshes')}", status_code=303)

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
                msg = f"Can't sync: DataGolf is showing '{api_event_name}', not '{tournament.name}'"
                return RedirectResponse(f"/leaderboard?tournament_id={tournament_id}&message={quote(msg)}", status_code=303)

            live_stats = live_data.get('live_stats', [])
            
            # Check if anyone is currently playing (not all finished for the day)
            # A player is "playing" if their thru < 18 for the current round
            players_on_course = 0
            players_finished = 0
            current_round = live_data.get('current_round', 1)
            
            for player in live_stats:
                thru = player.get('thru')
                if thru is not None:
                    if thru < 18:
                        players_on_course += 1
                    else:
                        players_finished += 1
            
            # If no one is on the course but there are results, round is complete
            if players_on_course == 0 and players_finished > 0:
                logger.info(f"Round {current_round} complete - all {players_finished} players finished")
                # Check if we already synced recently (within 30 min) - no need to keep syncing
                if tournament.last_synced_at:
                    try:
                        last_sync = datetime.fromisoformat(tournament.last_synced_at.replace('Z', '+00:00'))
                        minutes_since = (datetime.now() - last_sync).total_seconds() / 60
                        if minutes_since < 30:
                            msg = f"Round {current_round} complete. All players finished - scores are final."
                            return RedirectResponse(f"/leaderboard?tournament_id={tournament_id}&message={quote(msg)}", status_code=303)
                    except:
                        pass
            
            _last_refresh[tournament_id] = now

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
            
            # Update last_synced_at timestamp
            db.tournaments.update(id=tournament_id, last_synced_at=datetime.now().isoformat())
        except Exception as e:
            logger.error(f"Refresh error: {e}", exc_info=True)

        return RedirectResponse(f"/leaderboard?tournament_id={tournament_id}", status_code=303)

    @app.post("/leaderboard/send-groupme")
    def send_leaderboard_groupme(request, tournament_id: int):
        """Send current leaderboard standings to GroupMe."""
        db = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/leaderboard", status_code=303)

        try:
            from services.groupme import GroupMeClient

            # Get tournament
            tournament = None
            for t in db.tournaments():
                if t.id == tournament_id:
                    tournament = t
                    break

            if not tournament:
                return RedirectResponse("/leaderboard", status_code=303)

            # Get bot_id from app_settings first, then fall back to config
            bot_id = None
            for setting in db.app_settings():
                if setting.key == 'groupme_bot_id':
                    bot_id = setting.value
                    break

            if not bot_id:
                from config import GROUPME_BOT_ID
                bot_id = GROUPME_BOT_ID

            if not bot_id:
                return RedirectResponse(f"/leaderboard?tournament_id={tournament_id}", status_code=303)

            # Get standings
            all_picks = [p for p in db.picks() if p.tournament_id == tournament_id]
            standings = [s for s in db.pickem_standings() if s.tournament_id == tournament_id]
            standings.sort(key=lambda s: s.rank if s.rank else 999)

            users_by_id = {u.id: u for u in db.users()}

            # Build message
            from routes.utils import calculate_tournament_purse
            purse = calculate_tournament_purse(tournament, all_picks)

            message_lines = [f"🏌️ {tournament.name} - Top 10"]
            if purse:
                message_lines.append(f"💰 Purse: ${purse}")
            message_lines.append("")

            # Add top 10 standings
            for i, standing in enumerate(standings[:10]):
                if i >= 10:
                    break
                user = users_by_id.get(standing.user_id)
                player_name = user.display_name if user else f"User {standing.user_id}"
                rank = standing.rank if standing.rank else (i + 1)
                score = standing.best_two_total if standing.best_two_total is not None else "DQ"

                # Format score
                from routes.utils import format_score
                score_str = format_score(score) if isinstance(score, int) else str(score)

                message_lines.append(f"{rank}. {player_name} - {score_str}")

            message = "\n".join(message_lines)

            # Send message
            client = GroupMeClient(bot_id)
            client.send_message(message)

        except Exception as e:
            logger.error(f"Failed to send leaderboard to GroupMe: {e}", exc_info=True)

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
