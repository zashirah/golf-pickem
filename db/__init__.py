"""Database initialization and connection."""
from fasthtml.common import database
from config import DATABASE_PATH, DATABASE_URL
import logging
import os

logger = logging.getLogger(__name__)

# Initialize database
# For local development: use SQLite (ignore DATABASE_URL)
# For production on Render: DATABASE_URL will be set, but FastHTML's database() won't handle PostgreSQL URLs
# We'll stick with SQLite for FastHTML compatibility and migrate to PostgreSQL later if needed

if DATABASE_URL and 'DATABASE_URL' in os.environ and os.environ.get('RENDER'):
    # On Render production with explicit PostgreSQL setup needed
    logger.warning("PostgreSQL not yet supported - using SQLite. Update planned.")
    os.makedirs(DATABASE_PATH.parent, exist_ok=True)
    db = database(str(DATABASE_PATH))
else:
    # Local development or initial setup - use SQLite
    logger.info(f"Using SQLite database at {DATABASE_PATH}")
    os.makedirs(DATABASE_PATH.parent, exist_ok=True)
    db = database(str(DATABASE_PATH))

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
