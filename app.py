"""Golf Pick'em - Main Application.

This is the entry point for the application. It initializes the database,
services, and registers all routes from their respective modules.
"""
import os
import logging

from fasthtml.common import *

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
from routes.season_leaderboard import setup_season_leaderboard_routes

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
setup_season_leaderboard_routes(app)
setup_admin_routes(app)


# ============ Run Server ============

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    serve(host="0.0.0.0", port=port)
