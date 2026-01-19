"""Database initialization and connection."""
from fastsql import Database
from config import DATA_DIR, DATABASE_URL
import logging
import os

logger = logging.getLogger(__name__)

# Initialize database using fastsql (MiniDataAPI spec)
# Local development: SQLite (default when DATABASE_URL not set)
# Production: PostgreSQL (when DATABASE_URL is set to postgresql://...)

# Ensure data directory exists for SQLite
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Log which database we're using
if DATABASE_URL.startswith("postgresql"):
    logger.info("Using PostgreSQL database")

    # Force IPv4-only for connections (Render doesn't support IPv6)
    # Supabase connection pooler uses IPv4-only port 6543
    modified_url = DATABASE_URL.replace(':5432', ':6543').replace('?', '?')

    # If no port specified in URL, use pooler port
    if ':5432' not in DATABASE_URL and ':6543' not in DATABASE_URL:
        # Add pooler mode if connecting via pooler
        separator = '&' if '?' in modified_url else '?'
        modified_url = f"{modified_url}{separator}pgbouncer=true"

    logger.info("Using Supabase IPv4 connection pooler (port 6543)")
    db = Database(modified_url)
else:
    logger.info(f"Using SQLite database: {DATABASE_URL}")
    db = Database(DATABASE_URL)

# Table references (initialized in models.py)
users = None
sessions = None
app_settings = None
tournaments = None
golfers = None
tournament_field = None
picks = None
tournament_results = None
pickem_standings = None


def init_db():
    """Initialize all database tables."""
    from db.models import create_tables
    global users, sessions, app_settings, tournaments, golfers
    global tournament_field, picks, tournament_results, pickem_standings

    tables = create_tables(db)
    users = tables['users']
    sessions = tables['sessions']
    app_settings = tables['app_settings']
    tournaments = tables['tournaments']
    golfers = tables['golfers']
    tournament_field = tables['tournament_field']
    picks = tables['picks']
    tournament_results = tables['tournament_results']
    pickem_standings = tables['pickem_standings']

    return tables
