"""Page layout components."""
from fasthtml.common import *


def page_head():
    """Common head elements."""
    return (
        Meta(charset="utf-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1"),
        Link(rel="stylesheet", href="/static/style.css"),
    )


def nav_header(user=None):
    """Top navigation bar."""
    if user:
        nav_items = [
            A("Picks", href="/picks", cls="nav-link"),
            A("Leaderboard", href="/leaderboard", cls="nav-link"),
        ]
        if user.is_admin:
            nav_items.append(A("Admin", href="/admin", cls="nav-link"))

        return Header(
            Div(
                A("Golf Pick'em", href="/", cls="logo"),
                Nav(*nav_items, cls="nav-links"),
                Div(
                    Span(user.display_name or user.username, cls="user-name"),
                    A("Logout", href="/logout", cls="btn btn-sm"),
                    cls="user-section"
                ),
                cls="header-content"
            ),
            cls="site-header"
        )

    return Header(
        Div(
            A("Golf Pick'em", href="/", cls="logo"),
            A("Login", href="/login", cls="btn btn-primary"),
            cls="header-content"
        ),
        cls="site-header"
    )


def page_footer():
    """Site footer."""
    return Footer(
        P("Golf Pick'em League"),
        cls="site-footer"
    )


def page_shell(title: str, *content, user=None):
    """Complete page wrapper."""
    return Html(
        Head(
            Title(f"{title} - Golf Pick'em"),
            *page_head()
        ),
        Body(
            nav_header(user),
            Main(*content, cls="container"),
            page_footer()
        )
    )


def alert(message: str, type: str = "info"):
    """Alert message box. Types: info, success, error."""
    return Div(message, cls=f"alert alert-{type}")


def card(title: str, *content, cls: str = ""):
    """Card component."""
    return Div(
        H3(title, cls="card-title") if title else None,
        *content,
        cls=f"card {cls}"
    )
