"""Admin routes."""
import logging
from datetime import datetime

from fasthtml.common import *
from starlette.responses import RedirectResponse

from components.layout import page_shell, card
from routes.utils import get_current_user, get_db, get_auth_service

logger = logging.getLogger(__name__)


def _get_groupme_bot_id(db_module) -> str:
    """Get GroupMe bot ID from app_settings."""
    for setting in db_module.app_settings():
        if setting.key == 'groupme_bot_id':
            return setting.value
    return None


def _mask_bot_id(bot_id: str) -> str:
    """Mask bot ID for display, showing only first and last 4 chars."""
    if not bot_id:
        return ""
    if len(bot_id) <= 8:
        return "****"
    return f"{bot_id[:4]}...{bot_id[-4:]}"



def filter_and_sort_tournaments(tournaments, tab='active'):
    """
    Filter and sort tournaments by tab.

    Active/Upcoming tab: Filter by status in ('active', 'upcoming'), sort soonest first,
    with active tournaments prioritized at the top.

    Completed tab: Filter by status = 'completed', sort newest first (reverse chronological).
    """
    if tab == 'completed':
        # Filter completed tournaments
        filtered = [t for t in tournaments if t.status == 'completed']
        # Sort by start_date newest first (most recent at top)
        def sort_key(t):
            if not t.start_date:
                return datetime.min
            try:
                return datetime.fromisoformat(t.start_date.replace('Z', '+00:00'))
            except:
                try:
                    return datetime.fromisoformat(t.start_date)
                except:
                    return datetime.min

        filtered.sort(key=sort_key, reverse=True)
    else:
        # Active/Upcoming tab (default)
        filtered = [t for t in tournaments if t.status in ('active', 'upcoming')]

        # Separate active and upcoming
        active = [t for t in filtered if t.status == 'active']
        upcoming = [t for t in filtered if t.status == 'upcoming']

        # Sort upcoming by start_date soonest first
        def sort_key(t):
            if not t.start_date:
                return datetime.max
            try:
                return datetime.fromisoformat(t.start_date.replace('Z', '+00:00'))
            except:
                try:
                    return datetime.fromisoformat(t.start_date)
                except:
                    return datetime.max

        upcoming.sort(key=sort_key)
        # Active tournaments appear first, then upcoming
        filtered = active + upcoming

    return filtered


def tournament_tabs(current_tab='active'):
    """
    Return tab navigation component for tournament tabs.

    Returns a Div with tab links for Active/Upcoming and Completed tabs.
    """
    return Div(
        A(
            "Active/Upcoming",
            href="/admin?tab=active",
            cls=f"tab {'tab-active' if current_tab == 'active' else ''}"
        ),
        A(
            "Completed",
            href="/admin?tab=completed",
            cls=f"tab {'tab-active' if current_tab == 'completed' else ''}"
        ),
        cls="tabs"
    )


def setup_admin_routes(app):
    """Register admin routes."""

    @app.get("/admin")
    def admin_page(request, error: str = None, success: str = None, tab: str = 'active'):
        db = get_db()
        auth_service = get_auth_service()
        user = get_current_user(request)

        if not user:
            return RedirectResponse("/login", status_code=303)
        if not user.is_admin:
            return page_shell("Access Denied", card("", P("Admin access required.")), user=user)

        invite_secret = auth_service.get_invite_secret()
        invite_path = f"/register?invite={invite_secret}"
        # Get the full URL including protocol and host
        invite_url = f"{request.url.scheme}://{request.url.netloc}{invite_path}"

        tournaments = list(db.tournaments())
        tournaments = filter_and_sort_tournaments(tournaments, tab)
        users = list(db.users())

        # Import alert for message display
        from components.layout import alert

        # Build message list
        messages = []
        if error:
            messages.append(alert(error, "error"))
        if success:
            messages.append(alert(success, "success"))

        return page_shell(
            "Admin",
            Div(
                H1("Admin Dashboard"),
                *messages,

                card(
                    "Invite Link",
                    P("Share this link for new users to register:"),
                    Div(
                        Code(invite_url, id="invite-url", cls="invite-code", style="cursor: pointer;"),
                        Button("📋 Copy", type="button", cls="btn btn-sm", 
                               onclick=f"navigator.clipboard.writeText('{invite_url}').then(() => {{ const btn = event.target; btn.textContent = '✓ Copied!'; setTimeout(() => btn.textContent = '📋 Copy', 2000); }})"),
                        style="display: flex; gap: 10px; align-items: center;"
                    ),
                    Form(
                        Button("Reset Invite Link", type="submit", cls="btn btn-secondary btn-sm"),
                        action="/admin/reset-invite",
                        method="post"
                    ),
                ),

                card(
                    "Tournaments",
                    tournament_tabs(tab),
                    Table(
                        Thead(Tr(Th("Name"), Th("Status"), Th("Picks"), Th("Pricing"), Th("Actions"))),
                        Tbody(*[Tr(
                            Td(t.name),
                            Td(
                                Span(t.status.title(), cls=f"badge badge-{t.status}"),
                                " ⭐" if t.status == 'active' else ""
                            ),
                            Td(
                                Span("Locked", cls="badge badge-locked") if t.picks_locked else Span("Open", cls="badge badge-open")
                            ),
                            Td(
                                (f"${t.entry_price}" if t.entry_price else "-") +
                                (" | " if (t.entry_price and t.three_entry_price) else "") +
                                (f"3-pack: ${t.three_entry_price}" if t.three_entry_price else "")
                            ),
                            Td(
                                A("Field", href=f"/admin/tournament/{t.id}/field", cls="btn btn-sm"),
                                A("Pricing", href=f"/admin/tournament/{t.id}/pricing", cls="btn btn-sm"),
                                Form(
                                    Button("Unlock" if t.picks_locked else "Lock", type="submit", cls="btn btn-sm"),
                                    Input(type="hidden", name="tournament_id", value=str(t.id)),
                                    action="/admin/toggle-lock",
                                    method="post",
                                    style="display:inline"
                                ),
                                Form(
                                    Button("Set Active", type="submit", cls="btn btn-sm btn-success"),
                                    Input(type="hidden", name="tournament_id", value=str(t.id)),
                                    action="/admin/set-active",
                                    method="post",
                                    style="display:inline"
                                ) if t.status != 'active' else "",
                                Form(
                                    Button("Sync Results", type="submit", cls="btn btn-sm btn-primary"),
                                    Input(type="hidden", name="tournament_id", value=str(t.id)),
                                    action="/admin/sync-results",
                                    method="post",
                                    style="display:inline"
                                ) if t.status == 'active' else "",
                                Form(
                                    Button("Mark Complete", type="submit", cls="btn btn-sm btn-warning"),
                                    Input(type="hidden", name="tournament_id", value=str(t.id)),
                                    action="/admin/mark-completed",
                                    method="post",
                                    style="display:inline"
                                ) if t.status == 'active' else "",
                            )
                        ) for t in tournaments]),
                        cls="admin-table"
                    ) if tournaments else P("No tournaments. Sync from DataGolf."),
                    Div(
                        Form(
                            Button("Sync from DataGolf", type="submit", cls="btn btn-primary"),
                            action="/admin/sync",
                            method="post",
                            style="display:inline; margin-right:10px;"
                        ),
                        Form(
                            Button("Update Statuses", type="submit", cls="btn btn-secondary"),
                            action="/admin/update-statuses",
                            method="post",
                            style="display:inline; margin-right:10px;"
                        ),
                        Form(
                            Button("Recalculate All Standings", type="submit", cls="btn btn-secondary"),
                            action="/admin/recalculate-all-standings",
                            method="post",
                            style="display:inline;"
                        ),
                    ),
                ),

                card(
                    "Users",
                    Table(
                        Thead(Tr(Th("GroupMe Name"), Th("Admin"), Th("Actions"))),
                        Tbody(*[Tr(
                            Td(u.groupme_name or u.username or "-"),
                            Td("Yes" if u.is_admin else "No"),
                            Td(
                                Form(
                                    Input(type="hidden", name="user_id", value=str(u.id)),
                                    Button("Delete", type="submit", cls="btn btn-sm btn-danger",
                                           onclick="return confirm('Are you sure you want to delete this user? This will also delete all their picks and standings.');"),
                                    action="/admin/delete-user",
                                    method="post",
                                    style="display:inline"
                                ) if not u.is_admin else "",
                            )
                        ) for u in users]),
                        cls="admin-table"
                    ),
                ),

                card(
                    "GroupMe Settings",
                    Div(
                        P("Configure GroupMe bot for notifications."),
                        P(
                            Strong("Current Bot ID: "),
                            Code(_mask_bot_id(_get_groupme_bot_id(db))) if _get_groupme_bot_id(db) else "Not configured"
                        ),
                        Form(
                            Div(
                                Label("New Bot ID", For="bot_id"),
                                Input(
                                    type="text",
                                    id="bot_id",
                                    name="bot_id",
                                    placeholder="Enter new bot ID to update",
                                ),
                                cls="form-group"
                            ),
                            Button("Save Bot ID", type="submit", cls="btn btn-primary"),
                            action="/admin/groupme/set-bot-id",
                            method="post",
                            style="display:inline; margin-right:10px;"
                        ),
                        Form(
                            Button("Send Test Message", type="submit", cls="btn btn-secondary"),
                            action="/admin/groupme/test",
                            method="post",
                            style="display:inline;"
                        ) if _get_groupme_bot_id(db) else "",
                        cls="groupme-settings"
                    )
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

    @app.post("/admin/delete-user")
    def delete_user(request, user_id: int):
        """Delete a user and all their associated data."""
        db = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        try:
            # Get the user to delete
            users_to_delete = [u for u in db.users() if u.id == user_id]
            if not users_to_delete:
                return RedirectResponse("/admin?error=User not found", status_code=303)

            user_to_delete = users_to_delete[0]

            # Prevent deleting admin users
            if user_to_delete.is_admin:
                return RedirectResponse("/admin?error=Cannot delete admin users", status_code=303)

            # Delete associated data
            # Delete picks
            picks_to_delete = [p for p in db.picks() if p.user_id == user_id]
            for pick in picks_to_delete:
                db.picks.delete(pick.id)

            # Delete standings
            standings_to_delete = [s for s in db.pickem_standings() if s.user_id == user_id]
            for standing in standings_to_delete:
                db.pickem_standings.delete(standing.id)

            # Delete sessions
            sessions_to_delete = [s for s in db.sessions() if s.user_id == user_id]
            for session in sessions_to_delete:
                db.sessions.delete(session.id)

            # Finally delete the user
            db.users.delete(user_id)

            logger.info(f"Admin {user.groupme_name} deleted user {user_to_delete.groupme_name} (id={user_id})")
            return RedirectResponse("/admin?success=User deleted successfully", status_code=303)

        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}", exc_info=True)
            return RedirectResponse("/admin?error=Failed to delete user", status_code=303)


    @app.post("/admin/update-statuses")
    def update_tournament_statuses(request):
        """Update tournament statuses based on dates and DataGolf data."""
        db_module = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        from services.datagolf import DataGolfClient
        from etl.tournament_state import activate_tournaments, complete_tournaments

        client = DataGolfClient()

        try:
            activate_tournaments(db_module)
            complete_tournaments(db_module, client)
            logger.info("Tournament status update complete")
        except Exception as e:
            logger.error(f"Error updating tournament statuses: {e}", exc_info=True)

        return RedirectResponse("/admin", status_code=303)

    @app.post("/admin/toggle-lock")
    def toggle_lock(request, tournament_id: int):
        db = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        # Find tournament and toggle lock
        from sqlalchemy import text
        tournament = None
        for t in db.tournaments():
            if t.id == tournament_id:
                tournament = t
                break

        if tournament:
            # Use raw SQL to avoid updating the primary key which causes table locks
            with db.db.engine.begin() as conn:
                conn.execute(
                    text("UPDATE tournament SET picks_locked = :locked WHERE id = :id"),
                    {"locked": not tournament.picks_locked, "id": tournament_id}
                )

        return RedirectResponse("/admin", status_code=303)

    @app.post("/admin/set-active")
    def set_active_tournament(request, tournament_id: int):
        """Manually set a tournament as the active tournament."""
        db = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        # Set the selected tournament as active, revert others to upcoming
        for t in db.tournaments():
            if t.id == tournament_id:
                # Set this one as active
                db.tournaments.update(id=t.id, status='active')
                logger.info(f"Set {t.name} as active tournament")
            elif t.status == 'active':
                # Revert other active tournaments back to upcoming (not completed)
                # Tournaments should only be marked completed when they actually finish
                db.tournaments.update(id=t.id, status='upcoming')
                logger.info(f"Set {t.name} back to upcoming (no longer active)")

        return RedirectResponse("/admin", status_code=303)

    @app.post("/admin/mark-completed")
    def mark_tournament_completed(request, tournament_id: int):
        """Manually mark a tournament as completed."""
        db = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        # Find and mark tournament as completed
        for t in db.tournaments():
            if t.id == tournament_id:
                if t.status != 'completed':
                    db.tournaments.update(id=t.id, status='completed')
                    logger.info(f"Admin {user.groupme_name} marked {t.name} as completed")
                    # Auto-send final leaderboard to GroupMe
                    _send_final_leaderboard_groupme(db, tournament_id)
                break

        return RedirectResponse("/admin", status_code=303)

    @app.post("/admin/recalculate-all-standings")
    def recalculate_all_standings(request):
        """Recalculate standings for all tournaments (backfill tiebreaker data)."""
        db = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        from services.scoring import ScoringService

        scoring = ScoringService(db)

        count = 0
        try:
            for tournament in db.tournaments():
                if tournament.status in ('active', 'completed'):
                    scoring.calculate_standings(tournament.id)
                    count += 1

            logger.info(f"Recalculated standings for {count} tournaments")
            return RedirectResponse(f"/admin?success=Recalculated+{count}+tournaments", status_code=303)
        except Exception as e:
            logger.error(f"Error recalculating standings: {e}", exc_info=True)
            return RedirectResponse(f"/admin?error=Error+recalculating+standings", status_code=303)

    @app.post("/admin/sync-results")
    def sync_results(request, tournament_id: int):
        db_module = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        from services.datagolf import DataGolfClient
        from services.scoring import ScoringService
        from etl.results import sync_results as etl_sync_results

        client = DataGolfClient()
        scoring = ScoringService(db_module)

        tournament = None
        for t in db_module.tournaments():
            if t.id == tournament_id:
                tournament = t
                break

        if not tournament:
            return RedirectResponse("/admin?error=Tournament+not+found", status_code=303)

        try:
            result = etl_sync_results(db_module, client, tournament)
            scoring.calculate_standings(tournament_id)
            logger.info(f"Synced {result['result_count']} results for tournament {tournament_id}")
        except ValueError as e:
            logger.warning(str(e))
            error_param = str(e).replace(' ', '+').replace("'", '')
            return RedirectResponse(f"/admin?error={error_param}", status_code=303)
        except Exception as e:
            logger.error(f"Sync results error: {e}", exc_info=True)

        return RedirectResponse("/admin", status_code=303)

    @app.post("/admin/sync")
    def sync_datagolf(request):
        db_module = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        from services.datagolf import DataGolfClient
        from etl.golfers import sync_golfers
        from etl.tournaments import sync_tournaments

        client = DataGolfClient()

        try:
            golfer_result = sync_golfers(db_module, client)
            tournament_result = sync_tournaments(db_module, client)
            logger.info(
                f"Sync complete: {golfer_result['golfer_count']} players, "
                f"{tournament_result['tournament_count']} tournaments"
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
                A(
                    Button("Auto-Assign Tiers from DataGolf", type="button", cls="btn btn-primary"),
                    href=f"/admin/tournament/{tid}/field/auto-confirm"
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

    @app.get("/admin/tournament/{tid}/field/auto-confirm")
    def auto_assign_confirm_page(request, tid: int):
        """Show confirmation page before auto-assigning tiers."""
        db_module = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        from services.datagolf import DataGolfClient

        tournament = None
        for t in db_module.tournaments():
            if t.id == tid:
                tournament = t
                break

        if not tournament:
            return RedirectResponse("/admin", status_code=303)

        client = DataGolfClient()
        
        try:
            field_data = client.get_field_updates()
            dg_event_name = field_data.get('event_name', 'Unknown')
            field_players = field_data.get('field', [])
            
            # Check if tournament matches
            is_match = tournament.datagolf_name and tournament.datagolf_name == dg_event_name
            
            # Get golfers from DB to see which are missing
            golfers_by_dg_id = {g.datagolf_id: g for g in db_module.golfers()}
            
            matched = []
            missing = []
            for p in field_players:
                dg_id = str(p.get('dg_id', ''))
                player_name = p.get('player_name', 'Unknown')
                if dg_id in golfers_by_dg_id:
                    matched.append((golfers_by_dg_id[dg_id], p))
                else:
                    missing.append(p)
            
            # Sort matched by skill for tier preview
            matched.sort(key=lambda x: x[0].dg_skill or 0, reverse=True)
            
            # Build tier preview
            tier_counts = {1: 0, 2: 0, 3: 0, 4: 0}
            for i, (g, p) in enumerate(matched):
                if i < 6:
                    tier_counts[1] += 1
                elif i < 24:
                    tier_counts[2] += 1
                elif i < 60:
                    tier_counts[3] += 1
                else:
                    tier_counts[4] += 1
            
            match_status = Div(
                Span("✅ Tournament matches DataGolf event", cls="text-success") if is_match else
                Span(f"⚠️ Tournament mismatch! DB: '{tournament.datagolf_name or tournament.name}' vs DataGolf: '{dg_event_name}'", cls="text-warning"),
                cls="match-status"
            )
            
            # Build missing players section conditionally
            missing_section = []
            if missing:
                missing_children = [H3(f"Players to be Created ({len(missing)})")]
                missing_children.append(Ul(*[Li(f"{p.get('player_name', 'Unknown')} ({p.get('country', 'Unknown')})") for p in missing[:20]]))
                if len(missing) > 20:
                    missing_children.append(P(f"...and {len(missing) - 20} more"))
                missing_section.append(Div(*missing_children, cls="missing-players"))

            return page_shell(
                "Confirm Auto-Assign Tiers",
                Div(
                    H1("Confirm Auto-Assign Tiers"),
                    match_status,
                    Div(
                        H3("Tournament Details"),
                        P(Strong("Target Tournament: "), tournament.name),
                        P(Strong("DataGolf Event: "), dg_event_name),
                        P(Strong("Start Date: "), tournament.start_date or "Unknown"),
                        cls="tournament-info"
                    ),
                    Div(
                        H3("Field Summary"),
                        P(f"Total players in DataGolf field: {len(field_players)}"),
                        P(f"Players found in database: {len(matched)}"),
                        *([ P(f"Players to be created: {len(missing)}", cls="text-info") ] if missing else []),
                        cls="field-summary"
                    ),
                    Div(
                        H3("Tier Distribution Preview"),
                        Ul(
                            Li(f"Tier 1: {tier_counts[1]} golfers (top 6)"),
                            Li(f"Tier 2: {tier_counts[2]} golfers (next 18)"),
                            Li(f"Tier 3: {tier_counts[3]} golfers (next 36)"),
                            Li(f"Tier 4: {tier_counts[4]} golfers (rest)")
                        ),
                        cls="tier-preview"
                    ),
                    *missing_section,
                    Div(
                        Form(
                            Button("✓ Confirm & Assign Tiers", type="submit", cls="btn btn-primary"),
                            action=f"/admin/tournament/{tid}/field/auto",
                            method="post",
                            style="display: inline-block; margin-right: 10px;"
                        ) if is_match else Span(
                            "Cannot assign tiers - tournament doesn't match current DataGolf event. ",
                            "Tier assignment is only available during the tournament's week.",
                            cls="text-danger"
                        ),
                        A("← Cancel", href=f"/admin/tournament/{tid}/field", cls="btn btn-secondary"),
                        cls="actions",
                        style="margin-top: 20px;"
                    ),
                    cls="confirm-page"
                ),
                user=user
            )
        except Exception as e:
            logger.error(f"Error fetching field data: {e}", exc_info=True)
            return page_shell(
                "Error",
                Div(
                    H1("Error Fetching Field Data"),
                    P(f"Could not fetch field data from DataGolf: {str(e)}"),
                    A("← Back", href=f"/admin/tournament/{tid}/field", cls="btn btn-secondary")
                ),
                user=user
            )

    @app.post("/admin/tournament/{tid}/field/auto")
    def auto_assign_tiers(request, tid: int):
        db_module = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        from services.datagolf import DataGolfClient
        from etl.field import auto_assign_field

        client = DataGolfClient()

        try:
            result = auto_assign_field(db_module, client, tid)
            logger.info(
                f"Auto-assigned {result['assigned_count']} golfers "
                f"({result['created_count']} created) for tournament {tid}"
            )
        except ValueError as e:
            logger.warning(f"Auto-assign field error: {e}")
            return RedirectResponse(f"/admin/tournament/{tid}/field?error=mismatch", status_code=303)
        except Exception as e:
            logger.error(f"Auto-assign error: {e}", exc_info=True)

        return RedirectResponse(f"/admin/tournament/{tid}/field", status_code=303)

    @app.get("/admin/tournament/{tid}/pricing")
    def tournament_pricing_page(request, tid: int, error: str = None, success: str = None):
        """Edit tournament entry pricing."""
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

        # Get entry count for this tournament
        picks = list(db.picks())
        entries_for_tournament = [p for p in picks if p.tournament_id == tid]
        entry_count = len(entries_for_tournament)

        entry_price = tournament.entry_price or 15
        three_entry_price = tournament.three_entry_price or 35
        total_purse = entry_count * entry_price if entry_price > 0 else 0

        # Import alert for messages
        from components.layout import alert

        # Build message list
        messages = []
        if error:
            messages.append(alert(error, "error"))
        if success:
            messages.append(alert(success, "success"))

        return page_shell(
            "Tournament Pricing",
            Div(
                H1(f"Pricing: {tournament.name}"),
                *messages,
                card(
                    "Entry Pricing",
                    Form(
                        Div(
                            Label("Single Entry Price ($)", For="entry_price"),
                            Input(
                                type="number",
                                id="entry_price",
                                name="entry_price",
                                value=str(entry_price) if entry_price else "",
                                placeholder="Default: $15",
                                min="0",
                                step="1"
                            ),
                            cls="form-group"
                        ),
                        Div(
                            Label("3-Entry Package Price ($)", For="three_entry_price"),
                            Input(
                                type="number",
                                id="three_entry_price",
                                name="three_entry_price",
                                value=str(three_entry_price) if three_entry_price else "",
                                placeholder="Default: $35",
                                min="0",
                                step="1"
                            ),
                            cls="form-group"
                        ),
                        Button("Save Pricing", type="submit", cls="btn btn-primary"),
                        action=f"/admin/tournament/{tid}/pricing",
                        method="post"
                    )
                ),
                card(
                    "Purse Summary",
                    Div(
                        P(Strong(f"Total Entries: "), f"{entry_count}"),
                        P(Strong(f"Price per Entry: "), f"${entry_price}" if entry_price > 0 else "Not set"),
                        P(Strong(f"Total Purse: "), f"${total_purse}" if entry_price > 0 else "No pricing set"),
                        cls="purse-info"
                    )
                ),
                A("← Back to Admin", href="/admin", cls="btn btn-secondary", style="margin-top: 20px;"),
                cls="pricing-page"
            ),
            user=user
        )

    @app.post("/admin/tournament/{tid}/pricing")
    def update_tournament_pricing(request, tid: int, entry_price: int = None, three_entry_price: int = None):
        """Update tournament pricing."""
        db = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        # Find tournament
        tournament = None
        for t in db.tournaments():
            if t.id == tid:
                tournament = t
                break

        if not tournament:
            return RedirectResponse("/admin", status_code=303)

        # Validate pricing (must be positive or empty/zero to clear)
        if entry_price is not None and entry_price < 0:
            return RedirectResponse(f"/admin/tournament/{tid}/pricing?error=Entry price must be positive", status_code=303)
        if three_entry_price is not None and three_entry_price < 0:
            return RedirectResponse(f"/admin/tournament/{tid}/pricing?error=3-entry price must be positive", status_code=303)

        # Update pricing fields (0 or empty clears the price)
        update_data = {}
        if entry_price is not None:
            update_data['entry_price'] = int(entry_price) if entry_price > 0 else None
        if three_entry_price is not None:
            update_data['three_entry_price'] = int(three_entry_price) if three_entry_price > 0 else None

        if update_data:
            db.tournaments.update(id=tid, **update_data)
            logger.info(f"Updated pricing for tournament {tid}: {update_data}")
            return RedirectResponse(f"/admin/tournament/{tid}/pricing?success=Pricing updated", status_code=303)

        return RedirectResponse(f"/admin/tournament/{tid}/pricing", status_code=303)

    @app.post("/admin/groupme/set-bot-id")
    def set_groupme_bot_id(request, bot_id: str = None):
        """Update GroupMe bot ID."""
        db = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/admin", status_code=303)

        if bot_id and bot_id.strip():
            bot_id = bot_id.strip()
            # Find existing setting or create new one
            settings = list(db.app_settings())
            existing = [s for s in settings if s.key == 'groupme_bot_id']

            if existing:
                db.app_settings.update(id=existing[0].id, value=bot_id)
            else:
                db.app_settings.insert(key='groupme_bot_id', value=bot_id)

            logger.info(f"Updated GroupMe bot_id (length: {len(bot_id)})")
            return RedirectResponse("/admin?success=GroupMe bot ID saved", status_code=303)

        return RedirectResponse("/admin?error=Bot ID cannot be empty", status_code=303)

    @app.post("/admin/groupme/test")
    def test_groupme_message(request):
        """Send test message to GroupMe."""
        db = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/admin", status_code=303)

        try:
            from services.groupme import GroupMeClient

            client = GroupMeClient(db_module=db)
            if not client.bot_id:
                return RedirectResponse("/admin?error=No GroupMe bot ID configured", status_code=303)

            message = "🏌️ Test message from Golf Pick'em Admin"
            success = client.send_message(message)

            if success:
                logger.info("Test GroupMe message sent successfully")
                return RedirectResponse("/admin?success=Test message sent to GroupMe", status_code=303)
            else:
                logger.warning("Test GroupMe message failed to send")
                return RedirectResponse("/admin?error=Failed to send test message", status_code=303)

        except Exception as e:
            logger.error(f"Failed to send test GroupMe message: {e}", exc_info=True)
            return RedirectResponse("/admin?error=Error sending test message", status_code=303)


    @app.get("/admin/picks-debug")
    def picks_debug(request, tournament_id: int = None):
        """Diagnostic: show pick golfer IDs vs tournament_result scores to find mismatches."""
        db = get_db()
        user = get_current_user(request)
        if not user or not user.is_admin:
            return RedirectResponse("/", status_code=303)

        tournaments = [t for t in db.tournaments() if t.status in ('active', 'completed')]
        tournaments.sort(key=lambda t: t.start_date or '', reverse=True)
        if not tournaments:
            return page_shell("Picks Debug", P("No tournaments."), user=user)

        tournament = next((t for t in tournaments if t.id == tournament_id), tournaments[0])

        golfers_by_id = {g.id: g for g in db.golfers()}
        users_by_id = {u.id: u for u in db.users()}
        results_by_golfer = {r.golfer_id: r for r in db.tournament_results() if r.tournament_id == tournament.id}
        picks = [p for p in db.picks() if p.tournament_id == tournament.id]

        # Find duplicate golfer names
        from collections import defaultdict
        name_to_ids = defaultdict(list)
        for g in db.golfers():
            name_to_ids[g.name].append(g.id)
        dupes = {name: ids for name, ids in name_to_ids.items() if len(ids) > 1}

        rows = []
        for pick in sorted(picks, key=lambda p: (users_by_id.get(p.user_id, type('', (), {'username': ''})()).username, getattr(p, 'entry_number', 1) or 1)):
            u = users_by_id.get(pick.user_id)
            entry_num = getattr(pick, 'entry_number', 1) or 1
            name = (u.groupme_name or u.username) if u else '?'

            def cell_info(golfer_id):
                if not golfer_id:
                    return Td('-'), Td('-'), Td('-'), Td('-')
                g = golfers_by_id.get(golfer_id)
                g_name = g.name if g else f'ID:{golfer_id}'
                dg_id = g.datagolf_id if g else '?'
                result = results_by_golfer.get(golfer_id)
                score = result.score_to_par if result else None
                status = result.status if result else 'no result'
                is_dupe = g_name in dupes
                style = 'background:#fee' if is_dupe else ''
                score_str = str(score) if score is not None else 'None'
                return (
                    Td(f'{g_name}{"*" if is_dupe else ""}', style=style),
                    Td(str(golfer_id)),
                    Td(dg_id or ''),
                    Td(f'{score_str} ({status})', style='' if score is not None else 'color:red'),
                )

            t1 = cell_info(pick.tier1_golfer_id)
            t2 = cell_info(pick.tier2_golfer_id)
            t3 = cell_info(pick.tier3_golfer_id)
            t4 = cell_info(pick.tier4_golfer_id)

            rows.append(Tr(
                Td(f'{name} ({entry_num})'),
                *t1, *t2, *t3, *t4
            ))

        dupe_section = []
        if dupes:
            dupe_section = [
                H3('Duplicate golfer names (highlighted in red above)'),
                Ul(*[Li(f'{name}: IDs = {ids}') for name, ids in dupes.items()])
            ]

        return page_shell(
            'Picks Debug',
            H2(f'{tournament.name} — picks golfer debug'),
            *dupe_section,
            P('Columns: User | T1 name | T1 db_id | T1 dg_id | T1 score | T2... | T3... | T4...'),
            P('score=None (red) means no tournament_result for that golfer_id. * = duplicate name.'),
            Div(
                Table(
                    Thead(Tr(
                        Th('Entry'),
                        Th('T1 Name'), Th('T1 ID'), Th('T1 dg_id'), Th('T1 Score'),
                        Th('T2 Name'), Th('T2 ID'), Th('T2 dg_id'), Th('T2 Score'),
                        Th('T3 Name'), Th('T3 ID'), Th('T3 dg_id'), Th('T3 Score'),
                        Th('T4 Name'), Th('T4 ID'), Th('T4 dg_id'), Th('T4 Score'),
                    )),
                    Tbody(*rows),
                    style='font-size:0.8rem;border-collapse:collapse;width:100%'
                ),
                style='overflow-x:auto'
            ),
            user=user
        )


def _send_final_leaderboard_groupme(db_module, tournament_id):
    """Send final leaderboard to GroupMe when tournament completes."""
    from etl.tournament_state import send_final_leaderboard_groupme
    send_final_leaderboard_groupme(db_module, tournament_id)
