"""Home and dashboard routes."""
from fasthtml.common import *

from components.layout import page_shell, card
from routes.utils import get_current_user, get_db


def setup_home_routes(app):
    """Register home routes."""
    rt = app.route

    @rt("/")
    def home(request):
        db = get_db()
        user = get_current_user(request)

        if not user:
            return page_shell(
                "Welcome",
                Div(
                    H1("Golf Pick'em League"),
                    P("Pick your golfers. Climb the leaderboard. Beat your friends."),
                    Div(
                        A("Login", href="/login", cls="btn btn-primary btn-lg"),
                        cls="cta-buttons"
                    ),
                    cls="hero"
                )
            )

        # Get current tournament
        tournaments = [t for t in db.tournaments() if t.status == 'active']
        current = tournaments[0] if tournaments else None

        # Get user's picks for current tournament
        user_pick = None
        if current:
            picks = [p for p in db.picks() if p.user_id == user.id and p.tournament_id == current.id]
            user_pick = picks[0] if picks else None

        return page_shell(
            "Dashboard",
            Div(
                H1(f"Welcome, {user.groupme_name or user.username}"),
                card(
                    "Current Tournament",
                    P(current.name if current else "No active tournament"),
                    A("Make Picks", href="/picks", cls="btn btn-primary") if current else None,
                    A("View Leaderboard", href="/leaderboard", cls="btn btn-secondary"),
                ) if current else card(
                    "No Active Tournament",
                    P("Check back when the next tournament starts."),
                ),
                cls="dashboard"
            ),
            user=user
        )

    @rt("/static/{fname:path}")
    def static_file(fname: str):
        return FileResponse(f"static/{fname}")

    @rt("/profile")
    def profile_page(request, error: str = None, success: str = None):
        """Profile page for editing user's GroupMe name."""
        db = get_db()
        user = get_current_user(request)

        if not user:
            return RedirectResponse("/login", status_code=303)

        from components.layout import alert

        error_msg = alert(error, "error") if error else None
        success_msg = alert(success, "success") if success else None

        return page_shell(
            "Profile",
            Div(
                H1("Profile Settings"),
                error_msg,
                success_msg,
                card(
                    "GroupMe Name",
                    Form(
                        P("This is how your name appears on the leaderboard, in GroupMe notifications, and how you log in."),
                        Div(
                            Label("GroupMe Name", fr="groupme_name"),
                            Input(
                                type="text",
                                name="groupme_name",
                                id="groupme_name",
                                value=user.groupme_name or "",
                                required=True,
                                placeholder="Your GroupMe display name"
                            ),
                            cls="form-group"
                        ),
                        Button("Update Name", type="submit", cls="btn btn-primary"),
                        action="/profile",
                        method="post"
                    )
                ),
                cls="profile-page"
            ),
            user=user
        )

    @rt("/profile")
    def update_profile(request, groupme_name: str):
        """Update user's GroupMe name."""
        db = get_db()
        user = get_current_user(request)

        if not user:
            return RedirectResponse("/login", status_code=303)

        if not groupme_name or not groupme_name.strip():
            return RedirectResponse("/profile?error=GroupMe name cannot be empty", status_code=303)

        # Verify GroupMe membership if configured
        from services.groupme import GroupMeClient
        from config import GROUPME_ACCESS_TOKEN, GROUPME_GROUP_ID

        if GROUPME_ACCESS_TOKEN and GROUPME_GROUP_ID:
            client = GroupMeClient()
            is_member = client.verify_member(groupme_name, GROUPME_GROUP_ID, GROUPME_ACCESS_TOKEN)
            if not is_member:
                return RedirectResponse("/profile?error=GroupMe name not found in group. Please check spelling.", status_code=303)

        # Update user's groupme_name (and also update display_name for backwards compatibility)
        db.user.update(
            id=user.id,
            groupme_name=groupme_name,
            display_name=groupme_name
        )

        return RedirectResponse("/profile?success=Profile updated successfully", status_code=303)

