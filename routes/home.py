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
                H1(f"Welcome, {user.display_name or user.username}"),
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
