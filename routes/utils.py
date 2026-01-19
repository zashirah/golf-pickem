"""Route utilities and shared helpers."""
from starlette.responses import RedirectResponse

from components.layout import page_shell, card

# Global references - set during app initialization
_auth_service = None
_db_module = None


def init_routes(auth_service, db_module):
    """Initialize route utilities with required services."""
    global _auth_service, _db_module
    _auth_service = auth_service
    _db_module = db_module


def get_db():
    """Get database module."""
    return _db_module


def get_auth_service():
    """Get authentication service."""
    return _auth_service


def get_current_user(request):
    """Get current user from session cookie."""
    token = request.cookies.get('session')
    return _auth_service.get_user_from_token(token)


def require_auth(func):
    """Decorator to require authentication."""
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        return func(request, user, *args, **kwargs)
    return wrapper


def require_admin(func):
    """Decorator to require admin role."""
    def wrapper(request, *args, **kwargs):
        user = get_current_user(request)
        if not user:
            return RedirectResponse("/login", status_code=303)
        if not user.is_admin:
            return page_shell("Access Denied", card("", "Admin access required."), user=user)
        return func(request, user, *args, **kwargs)
    return wrapper


def format_score(score):
    """Format golf score with +/- sign."""
    if score is None:
        return "MC"
    if score == 0:
        return "E"
    if score > 0:
        return f"+{score}"
    return str(score)  # Negative numbers already have minus sign


def get_active_tournament():
    """Get the currently active tournament, if any."""
    tournaments = [t for t in _db_module.tournaments() if t.status == 'active']
    return tournaments[0] if tournaments else None
