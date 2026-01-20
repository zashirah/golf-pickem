"""Picks routes - user pick management."""
from datetime import datetime

from fasthtml.common import *
from starlette.responses import RedirectResponse

from components.layout import page_shell, card, alert
from routes.utils import get_current_user, get_db, get_active_tournament


def setup_picks_routes(app):
    """Register picks routes."""

    @app.get("/picks")
    def picks_page(request, entry: int = None, edit: int = None):
        db = get_db()
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)

        # Get active tournament
        tournament = get_active_tournament()
        if not tournament:
            return page_shell(
                "Picks",
                card("No Active Tournament", P("Check back when a tournament starts.")),
                user=user
            )

        # Get all of user's entries for this tournament
        all_user_picks = [p for p in db.picks() if p.user_id == user.id and p.tournament_id == tournament.id]
        all_user_picks.sort(key=lambda p: getattr(p, 'entry_number', 1) or 1)

        # Calculate next available entry number
        existing_entries = [getattr(p, 'entry_number', 1) or 1 for p in all_user_picks]
        next_entry = max(existing_entries) + 1 if existing_entries else 1

        # Determine if we're in edit mode
        is_edit_mode = False
        current_entry = 1

        if not all_user_picks:
            # No picks yet - auto edit mode
            is_edit_mode = True
            current_entry = 1
        elif edit is not None:
            # Edit mode requested
            is_edit_mode = True
            current_entry = edit
        elif entry is not None:
            # Legacy support - treat entry param as edit
            is_edit_mode = True
            current_entry = entry

        # Find pick for current entry (if editing existing)
        user_pick = None
        if is_edit_mode:
            for p in all_user_picks:
                if (getattr(p, 'entry_number', 1) or 1) == current_entry:
                    user_pick = p
                    break

        golfers_by_id = {g.id: g for g in db.golfers()}

        def get_golfer_name(golfer_id):
            g = golfers_by_id.get(golfer_id)
            return g.name if g else "-"

        locked_msg = None
        if tournament.picks_locked:
            locked_msg = alert("Picks are locked for this tournament.", "info")

        # ========== SUMMARY VIEW ==========
        if not is_edit_mode:
            return _render_summary_view(
                tournament, all_user_picks, next_entry, locked_msg,
                get_golfer_name, user
            )

        # ========== EDIT MODE ==========
        return _render_edit_view(
            tournament, all_user_picks, current_entry, user_pick,
            locked_msg, golfers_by_id, user, db
        )

    @app.post("/picks")
    def submit_picks(request, entry: int = 1, tier1: int = None, tier2: int = None,
                     tier3: int = None, tier4: int = None):
        db = get_db()
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)

        # Get active tournament
        tournament = get_active_tournament()
        if not tournament:
            return RedirectResponse("/picks", status_code=303)

        if tournament.picks_locked:
            return RedirectResponse("/picks", status_code=303)

        # Check for existing picks for this specific entry
        existing = [p for p in db.picks()
                    if p.user_id == user.id
                    and p.tournament_id == tournament.id
                    and (getattr(p, 'entry_number', 1) or 1) == entry]

        is_update = bool(existing)
        action = "updated" if is_update else "created"

        if existing:
            # Update existing entry
            db.picks.update(
                id=existing[0].id,
                entry_number=entry,
                tier1_golfer_id=tier1,
                tier2_golfer_id=tier2,
                tier3_golfer_id=tier3,
                tier4_golfer_id=tier4,
                updated_at=datetime.now().isoformat()
            )
        else:
            # Create new entry
            db.picks.insert(
                user_id=user.id,
                tournament_id=tournament.id,
                entry_number=entry,
                tier1_golfer_id=tier1,
                tier2_golfer_id=tier2,
                tier3_golfer_id=tier3,
                tier4_golfer_id=tier4,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )

        # Send GroupMe notification
        _send_pick_notification(db, user, tournament, entry, tier1, tier2, tier3, tier4, action)

        return RedirectResponse("/picks", status_code=303)

    @app.post("/picks/delete")
    def delete_entry(request, entry: int):
        db = get_db()
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)

        # Get active tournament
        tournament = get_active_tournament()
        if not tournament:
            return RedirectResponse("/picks", status_code=303)

        if tournament.picks_locked:
            return RedirectResponse("/picks", status_code=303)

        # Find and delete the pick
        existing = [p for p in db.picks()
                    if p.user_id == user.id
                    and p.tournament_id == tournament.id
                    and (getattr(p, 'entry_number', 1) or 1) == entry]

        if existing:
            db.picks.delete(existing[0].id)

            # Also delete the standing if exists
            standing = [s for s in db.pickem_standings()
                        if s.user_id == user.id
                        and s.tournament_id == tournament.id
                        and (getattr(s, 'entry_number', 1) or 1) == entry]
            if standing:
                db.pickem_standings.delete(standing[0].id)

        return RedirectResponse("/picks", status_code=303)


def _render_summary_view(tournament, all_user_picks, next_entry, locked_msg,
                         get_golfer_name, user):
    """Render the picks summary view."""
    table_rows = []
    for p in all_user_picks:
        e_num = getattr(p, 'entry_number', 1) or 1
        table_rows.append(
            Tr(
                Td(f"Entry {e_num}", cls="entry-num"),
                Td(get_golfer_name(p.tier1_golfer_id), data_tier="Tier 1:"),
                Td(get_golfer_name(p.tier2_golfer_id), data_tier="Tier 2:"),
                Td(get_golfer_name(p.tier3_golfer_id), data_tier="Tier 3:"),
                Td(get_golfer_name(p.tier4_golfer_id), data_tier="Tier 4:"),
                Td(
                    Div(
                        A("Edit", href=f"/picks?edit={e_num}", cls="btn btn-sm btn-primary"),
                        Form(
                            Input(type="hidden", name="entry", value=str(e_num)),
                            Button("Delete", type="submit", cls="btn btn-sm btn-danger"),
                            action="/picks/delete",
                            method="post",
                            style="display:inline; margin-left: 0.5rem"
                        ),
                        cls="actions-cell"
                    ) if not tournament.picks_locked else None,
                    cls="actions"
                )
            )
        )

    entries_table = Table(
        Thead(
            Tr(
                Th("Entry"),
                Th("Tier 1"),
                Th("Tier 2"),
                Th("Tier 3"),
                Th("Tier 4"),
                Th("Actions") if not tournament.picks_locked else None
            )
        ),
        Tbody(*table_rows),
        cls="entries-table"
    )

    return page_shell(
        "My Picks",
        Div(
            H1(f"My Picks: {tournament.name}"),
            P("Your entries for this tournament. Best 2 of 4 scores count."),
            locked_msg,
            Div(
                entries_table,
                Div(
                    A("+ New Entry", href=f"/picks?edit={next_entry}", cls="btn btn-primary"),
                    A("View Leaderboard", href="/leaderboard", cls="btn btn-secondary"),
                    cls="picks-actions"
                ) if not tournament.picks_locked else A("View Leaderboard", href="/leaderboard", cls="btn btn-secondary"),
                cls="entries-section card"
            ),
            cls="picks-page"
        ),
        user=user
    )


def _render_edit_view(tournament, all_user_picks, current_entry, user_pick,
                      locked_msg, golfers_by_id, user, db):
    """Render the picks edit view."""
    # Get field organized by tier
    field = list(db.tournament_field())
    field_for_tournament = [f for f in field if f.tournament_id == tournament.id]

    tiers = {1: [], 2: [], 3: [], 4: []}
    for f in field_for_tournament:
        golfer = golfers_by_id.get(f.golfer_id)
        if golfer:
            tiers[f.tier].append((f, golfer))

    # Sort each tier by skill rating
    for tier in tiers:
        tiers[tier].sort(key=lambda x: x[1].dg_skill or 999, reverse=True)

    def tier_section(tier_num):
        golfers = tiers.get(tier_num, [])
        selected_id = getattr(user_pick, f'tier{tier_num}_golfer_id', None) if user_pick else None

        return Div(
            H3(f"Tier {tier_num}"),
            Div(
                *[Label(
                    Input(
                        type="radio",
                        name=f"tier{tier_num}",
                        value=str(g.id),
                        checked=(g.id == selected_id)
                    ),
                    Span(g.name, cls="golfer-name"),
                    Span(g.country or "", cls="golfer-country"),
                    Span(f"#{g.owgr}" if g.owgr else "", cls="golfer-rank"),
                    cls=f"golfer-option {'selected' if g.id == selected_id else ''}"
                ) for f, g in golfers],
                cls="tier-golfers"
            ),
            cls=f"tier-section tier-{tier_num}"
        )

    return page_shell(
        "Edit Entry",
        Div(
            Div(
                A("< Back to My Picks", href="/picks", cls="back-link") if all_user_picks else None,
                H1(f"{'Edit' if user_pick else 'New'} Entry {current_entry}"),
                P("Pick one golfer from each tier."),
                cls="edit-header"
            ),
            locked_msg,
            Form(
                Input(type="hidden", name="entry", value=str(current_entry)),
                Div(
                    Button(
                        "Save Entry",
                        type="submit",
                        cls="btn btn-primary btn-lg"
                    ),
                    A("Cancel", href="/picks", cls="btn btn-secondary btn-lg") if all_user_picks else None,
                    cls="form-actions form-actions-top"
                ),
                tier_section(1),
                tier_section(2),
                tier_section(3),
                tier_section(4),
                Div(
                    Button(
                        "Save Entry",
                        type="submit",
                        cls="btn btn-primary btn-lg"
                    ),
                    A("Cancel", href="/picks", cls="btn btn-secondary btn-lg") if all_user_picks else None,
                    cls="form-actions"
                ),
                action="/picks",
                method="post",
                id="picks-form"
            ) if not tournament.picks_locked else None,
            cls="picks-page edit-mode"
        ),
        user=user
    )


def _send_pick_notification(db, user, tournament, entry, tier1, tier2, tier3, tier4, action):
    """Send GroupMe notification for pick creation/update."""
    try:
        from services.groupme import GroupMeClient

        # Get golfer names
        golfers_by_id = {g.id: g for g in db.golfers()}
        tier1_name = golfers_by_id.get(tier1).name if tier1 and tier1 in golfers_by_id else "-"
        tier2_name = golfers_by_id.get(tier2).name if tier2 and tier2 in golfers_by_id else "-"
        tier3_name = golfers_by_id.get(tier3).name if tier3 and tier3 in golfers_by_id else "-"
        tier4_name = golfers_by_id.get(tier4).name if tier4 and tier4 in golfers_by_id else "-"

        # Calculate purse
        all_picks = [p for p in db.picks() if p.tournament_id == tournament.id]
        from routes.utils import calculate_tournament_purse
        purse = calculate_tournament_purse(tournament, all_picks)
        purse_text = f"${purse}" if purse else "Not set"

        # Build message
        display_name = user.display_name or user.username
        message = f"""🏌️ {display_name} {action.title()} Entry {entry} for {tournament.name}
Tier 1: {tier1_name}
Tier 2: {tier2_name}
Tier 3: {tier3_name}
Tier 4: {tier4_name}
💰 Total Purse: {purse_text}"""

        # Send message via GroupMeClient (will check app_settings and env var)
        client = GroupMeClient(db_module=db)
        client.send_message(message)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send pick notification: {e}", exc_info=True)
