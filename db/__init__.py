"""Database initialization and connection."""
from fastsql import Database
from config import DATA_DIR, DATABASE_URL
import logging
import socket

logger = logging.getLogger(__name__)

# Initialize database using fastsql (MiniDataAPI spec)
# Local development: SQLite (default when DATABASE_URL not set)
# Production: PostgreSQL (when DATABASE_URL is set to postgresql://...)

# Ensure data directory exists for SQLite
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Log which database we're using
if DATABASE_URL.startswith("postgresql"):
    logger.info("Using PostgreSQL database")

    # Force IPv4 for PostgreSQL connections (Render only supports IPv4)
    # This prevents "Network is unreachable" errors with IPv6 addresses from Supabase
    original_getaddrinfo = socket.getaddrinfo

    def getaddrinfo_ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
        """Force IPv4 resolution for database connections."""
        return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

    socket.getaddrinfo = getaddrinfo_ipv4_only
    db = Database(DATABASE_URL)
    socket.getaddrinfo = original_getaddrinfo  # Restore original
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
