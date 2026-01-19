"""Database initialization and connection."""
from fastsql import Database
from config import DATA_DIR, DATABASE_URL
import logging
import socket
from urllib.parse import urlparse, urlunparse

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
    # Resolve hostname to IPv4 address and replace in connection string
    parsed = urlparse(DATABASE_URL)
    hostname = parsed.hostname

    try:
        # Get IPv4 address for the hostname
        ipv4_addr = socket.getaddrinfo(hostname, None, socket.AF_INET)[0][4][0]
        logger.info(f"Resolved {hostname} to IPv4: {ipv4_addr}")

        # Replace hostname with IPv4 address in netloc
        if parsed.port:
            new_netloc = f"{parsed.username}:{parsed.password}@{ipv4_addr}:{parsed.port}" if parsed.password else f"{parsed.username}@{ipv4_addr}:{parsed.port}"
        else:
            new_netloc = f"{parsed.username}:{parsed.password}@{ipv4_addr}" if parsed.password else f"{parsed.username}@{ipv4_addr}"

        # Reconstruct URL with IPv4 address
        modified_url = urlunparse((
            parsed.scheme,
            new_netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))

        logger.info(f"Using IPv4 connection string")
        db = Database(modified_url)
    except Exception as e:
        logger.error(f"Failed to resolve hostname to IPv4: {e}, trying original URL")
        db = Database(DATABASE_URL)
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
