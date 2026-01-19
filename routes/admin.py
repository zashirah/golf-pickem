"""Admin routes."""
import logging
from datetime import datetime

from fasthtml.common import *
from starlette.responses import RedirectResponse

from components.layout import page_shell, card
from routes.utils import get_current_user, get_db, get_auth_service

logger = logging.getLogger(__name__)


def _normalize_tournament_name(name: str) -> str:
    """Normalize tournament name for comparison."""
    if not name:
        return ""
    # Lowercase and remove common variations
    normalized = name.lower().strip()
    # Remove "the " prefix
    if normalized.startswith("the "):
        normalized = normalized[4:]
    # Remove common suffixes/variations
    for suffix in [" presented by mastercard", " pga tour"]:
        normalized = normalized.replace(suffix, "")
    return normalized


def _tournament_names_match(db_name: str, api_name: str) -> bool:
    """Check if tournament names match (fuzzy comparison)."""
    norm_db = _normalize_tournament_name(db_name)
    norm_api = _normalize_tournament_name(api_name)

    # Exact match after normalization
    if norm_db == norm_api:
        return True

    # Check if one contains the other (for partial matches)
    if norm_db in norm_api or norm_api in norm_db:
        return True

    return False


def setup_admin_routes(app):
    """Register admin routes."""

    @app.get("/admin")
    def admin_page(request, error: str = None):
        db = get_db()
        auth_service = get_auth_service()
        user = get_current_user(request)

        if not user:
            return RedirectResponse("/login", status_code=303)
        if not user.is_admin:
            return page_shell("Access Denied", card("", P("Admin access required.")), user=user)

        invite_secret = auth_service.get_invite_secret()
        invite_url = f"/register?invite={invite_secret}"

        tournaments = list(db.tournaments())
        users = list(db.users())

        # Import alert for error display
        from components.layout import alert
        error_msg = alert(error, "error") if error else None

        return page_shell(
            "Admin",
            Div(
                H1("Admin Dashboard"),
                error_msg,

                card(
                    "Invite Link",
                    P("Share this link for new users to register:"),
                    Code(invite_url, cls="invite-code"),
                    Form(
                        Button("Reset Invite Link", type="submit", cls="btn btn-secondary btn-sm"),
                        action="/admin/reset-invite",
                        method="post"
                    ),
                ),

                card(
                    "Tournaments",
                    Table(
                        Thead(Tr(Th("Name"), Th("Status"), Th("Picks"), Th("Actions"))),
                        Tbody(*[Tr(
                            Td(t.name),
                            Td(t.status),
                            Td(
                                Span("Locked", cls="badge badge-locked") if t.picks_locked else Span("Open", cls="badge badge-open")
                            ),
                            Td(
                                A("Field", href=f"/admin/tournament/{t.id}/field", cls="btn btn-sm"),
                                Form(
                                    Button("Unlock" if t.picks_locked else "Lock", type="submit", cls="btn btn-sm"),
                                    Input(type="hidden", name="tournament_id", value=str(t.id)),
                                    action="/admin/toggle-lock",
                                    method="post",
                                    style="display:inline"
                                ),
                                Form(
                                    Button("Sync Results", type="submit", cls="btn btn-sm btn-primary"),
                                    Input(type="hidden", name="tournament_id", value=str(t.id)),
                                    action="/admin/sync-results",
                                    method="post",
                                    style="display:inline"
                                ) if t.status == 'active' else None,
                            )
                        ) for t in tournaments]),
                        cls="admin-table"
                    ) if tournaments else P("No tournaments. Sync from DataGolf."),
                    Form(
                        Button("Sync from DataGolf", type="submit", cls="btn btn-primary"),
                        action="/admin/sync",
                        method="post"
                    ),
                ),

                card(
                    "Users",
                    Table(
                        Thead(Tr(Th("Username"), Th("Display Name"), Th("Admin"))),
                        Tbody(*[Tr(
                            Td(u.username),
                            Td(u.display_name or "-"),
                            Td("Yes" if u.is_admin else "No")
                        ) for u in users]),
                        cls="admin-table"
                    ),
                ),

                cls="admin-page"
            ),
            user=user
        )

    @app.post("/admin/reset-invite")
    def reset_invite(request):
        auth_service = get_auth_service()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        auth_service.reset_invite_secret()
        return RedirectResponse("/admin", status_code=303)

    @app.post("/admin/toggle-lock")
    def toggle_lock(request, tournament_id: int):
        db = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        # Find tournament and toggle lock
        for t in db.tournaments():
            if t.id == tournament_id:
                db.tournaments.update(id=t.id, picks_locked=not t.picks_locked)
                break

        return RedirectResponse("/admin", status_code=303)

    @app.post("/admin/sync-results")
    def sync_results(request, tournament_id: int):
        db = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        from services.datagolf import DataGolfClient
        from services.scoring import ScoringService

        client = DataGolfClient()
        scoring = ScoringService(db)

        # Get the tournament we're trying to sync
        tournament = None
        for t in db.tournaments():
            if t.id == tournament_id:
                tournament = t
                break

        if not tournament:
            return RedirectResponse("/admin?error=Tournament+not+found", status_code=303)

        try:
            # Fetch live stats
            live_data = client.get_live_stats()

            # Validate that the API is returning data for the correct tournament
            api_event_name = live_data.get('event_name', '')
            if not _tournament_names_match(tournament.name, api_event_name):
                error_msg = f"Tournament mismatch: DataGolf is returning data for '{api_event_name}', not '{tournament.name}'. Sync cancelled."
                logger.warning(error_msg)
                return RedirectResponse(f"/admin?error=Tournament+mismatch:+API+returning+{api_event_name.replace(' ', '+')}", status_code=303)

            live_stats = live_data.get('live_stats', [])

            # Get golfer lookup
            golfers_by_dg_id = {g.datagolf_id: g for g in db.golfers()}

            for player in live_stats:
                dg_id = str(player.get('dg_id', ''))
                golfer = golfers_by_dg_id.get(dg_id)

                if not golfer:
                    continue

                # Parse position (could be "1", "T5", "CUT", etc.)
                pos_str = player.get('position', '')
                position = None
                status = 'active'

                if pos_str:
                    # Remove "T" prefix for tied positions
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

                # Upsert result
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

            # Calculate standings
            scoring.calculate_standings(tournament_id)

        except Exception as e:
            logger.error(f"Sync results error: {e}", exc_info=True)

        return RedirectResponse("/admin", status_code=303)

    @app.post("/admin/sync")
    def sync_datagolf(request):
        db = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        from services.datagolf import DataGolfClient

        client = DataGolfClient()

        try:
            # Sync players
            players = client.get_player_list()
            rankings = client.get_rankings()

            # Create skill lookup
            skill_by_id = {}
            for r in rankings:
                dg_id = str(r.get('dg_id', ''))
                skill_by_id[dg_id] = r.get('dg_skill_estimate', 0)

            for p in players:
                dg_id = str(p.get('dg_id', ''))
                name = p.get('player_name', '')
                country = p.get('country', '')

                existing = [g for g in db.golfers() if g.datagolf_id == dg_id]

                if existing:
                    db.golfers.update(
                        id=existing[0].id,
                        name=name,
                        country=country,
                        dg_skill=skill_by_id.get(dg_id, 0),
                        updated_at=datetime.now().isoformat()
                    )
                else:
                    db.golfers.insert(
                        datagolf_id=dg_id,
                        name=name,
                        country=country,
                        dg_skill=skill_by_id.get(dg_id, 0),
                        updated_at=datetime.now().isoformat()
                    )

            # Sync schedule
            schedule = client.get_schedule()
            for event in schedule[:10]:  # Just recent/upcoming
                event_id = str(event.get('event_id', ''))
                name = event.get('event_name', '')
                start = event.get('start_date', '')

                existing = [t for t in db.tournaments() if t.datagolf_id == event_id]

                if not existing:
                    db.tournaments.insert(
                        datagolf_id=event_id,
                        name=name,
                        start_date=start,
                        status='upcoming',
                        created_at=datetime.now().isoformat()
                    )

        except Exception as e:
            logger.error(f"Sync error: {e}", exc_info=True)

        return RedirectResponse("/admin", status_code=303)

    @app.get("/admin/tournament/{tid}/field")
    def tournament_field_page(request, tid: int):
        db = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        tournament = None
        for t in db.tournaments():
            if t.id == tid:
                tournament = t
                break

        if not tournament:
            return RedirectResponse("/admin", status_code=303)

        # Get current field
        field = [f for f in db.tournament_field() if f.tournament_id == tid]
        golfers_by_id = {g.id: g for g in db.golfers()}

        field_by_tier = {1: [], 2: [], 3: [], 4: []}
        for f in field:
            g = golfers_by_id.get(f.golfer_id)
            if g:
                field_by_tier[f.tier].append((f, g))

        for tier in field_by_tier:
            field_by_tier[tier].sort(key=lambda x: x[1].dg_skill or 0, reverse=True)

        def tier_table(tier_num):
            golfers = field_by_tier.get(tier_num, [])
            return Div(
                H3(f"Tier {tier_num} ({len(golfers)} golfers)"),
                Table(
                    Thead(Tr(Th("Name"), Th("Country"), Th("Skill"), Th("Move"))),
                    Tbody(*[Tr(
                        Td(g.name),
                        Td(g.country or ""),
                        Td(f"{g.dg_skill:.2f}" if g.dg_skill else "-"),
                        Td(
                            Form(
                                Select(
                                    Option("1", value="1", selected=(tier_num == 1)),
                                    Option("2", value="2", selected=(tier_num == 2)),
                                    Option("3", value="3", selected=(tier_num == 3)),
                                    Option("4", value="4", selected=(tier_num == 4)),
                                    name="tier"
                                ),
                                Input(type="hidden", name="field_id", value=str(f.id)),
                                Button("Move", type="submit", cls="btn btn-sm"),
                                action=f"/admin/tournament/{tid}/field/move",
                                method="post",
                                cls="move-form"
                            )
                        )
                    ) for f, g in golfers]),
                    cls="tier-table"
                ) if golfers else P("No golfers in this tier"),
                cls="tier-section"
            )

        return page_shell(
            "Tournament Field",
            Div(
                H1(f"Field: {tournament.name}"),
                Form(
                    Button("Auto-Assign Tiers from DataGolf", type="submit", cls="btn btn-primary"),
                    action=f"/admin/tournament/{tid}/field/auto",
                    method="post"
                ),
                Div(
                    tier_table(1),
                    tier_table(2),
                    tier_table(3),
                    tier_table(4),
                    cls="tiers-grid"
                ),
                cls="field-admin-page"
            ),
            user=user
        )

    @app.post("/admin/tournament/{tid}/field/move")
    def move_golfer_tier(request, tid: int, field_id: int, tier: int):
        db = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        db.tournament_field.update(id=field_id, tier=tier)
        return RedirectResponse(f"/admin/tournament/{tid}/field", status_code=303)

    @app.post("/admin/tournament/{tid}/field/auto")
    def auto_assign_tiers(request, tid: int):
        db = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        from services.datagolf import DataGolfClient

        tournament = None
        for t in db.tournaments():
            if t.id == tid:
                tournament = t
                break

        if not tournament:
            return RedirectResponse("/admin", status_code=303)

        client = DataGolfClient()

        try:
            # Get current field from DataGolf
            field_data = client.get_field_updates()
            field_players = field_data.get('field', [])

            # Get all golfers from DB
            golfers_by_dg_id = {g.datagolf_id: g for g in db.golfers()}

            # Clear existing field for this tournament
            for f in db.tournament_field():
                if f.tournament_id == tid:
                    db.tournament_field.delete(f.id)

            # Sort by skill and assign tiers
            field_with_skill = []
            for p in field_players:
                dg_id = str(p.get('dg_id', ''))
                golfer = golfers_by_dg_id.get(dg_id)
                if golfer:
                    field_with_skill.append(golfer)

            field_with_skill.sort(key=lambda g: g.dg_skill or 0, reverse=True)

            # Assign tiers: Top 6, next 18, next 36, rest
            for i, golfer in enumerate(field_with_skill):
                if i < 6:
                    tier = 1
                elif i < 24:  # 6 + 18
                    tier = 2
                elif i < 60:  # 24 + 36
                    tier = 3
                else:
                    tier = 4

                db.tournament_field.insert(
                    tournament_id=tid,
                    golfer_id=golfer.id,
                    tier=tier,
                    created_at=datetime.now().isoformat()
                )

        except Exception as e:
            logger.error(f"Auto-assign error: {e}", exc_info=True)

        return RedirectResponse(f"/admin/tournament/{tid}/field", status_code=303)
