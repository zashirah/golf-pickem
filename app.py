"""Golf Pick'em - Main Application.

This is the entry point for the application. It initializes the database,
services, and registers all routes from their respective modules.
"""
from fasthtml.common import *

from db import init_db
import db as db_module
from services.auth import AuthService
from routes import (
    init_routes,
    setup_auth_routes,
    setup_home_routes,
    setup_picks_routes,
    setup_leaderboard_routes,
    setup_admin_routes,
)

# Initialize database
tables = init_db()

# Initialize services
auth_service = AuthService(db_module)

# Create FastHTML app
app, rt = fast_app(
    hdrs=(Link(rel="stylesheet", href="/static/style.css"),),
    pico=False
)

# Initialize route utilities with services
init_routes(auth_service, db_module)

# Register all routes
setup_auth_routes(app, auth_service)
setup_home_routes(app)
setup_picks_routes(app)
setup_leaderboard_routes(app)
setup_admin_routes(app)


# ============ Run Server ============

if __name__ == "__main__":
    serve()
