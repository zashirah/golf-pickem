"""Routes package."""
from routes.utils import init_routes
from routes.auth import setup_auth_routes
from routes.home import setup_home_routes
from routes.picks import setup_picks_routes
from routes.leaderboard import setup_leaderboard_routes
from routes.admin import setup_admin_routes

__all__ = [
    'init_routes',
    'setup_auth_routes',
    'setup_home_routes',
    'setup_picks_routes',
    'setup_leaderboard_routes',
    'setup_admin_routes',
]
