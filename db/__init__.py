"""Database initialization and connection."""
from fastsql import Database
from config import DATA_DIR, DATABASE_URL
import logging
import sqlalchemy as sa

logger = logging.getLogger(__name__)


class PostgresDatabase(Database):
    """Custom Database subclass with connection pooling options for PostgreSQL.

    Handles Supabase free tier idle connection timeouts by:
    - pool_pre_ping: Testing connections before use (detects stale connections)
    - pool_recycle: Recycling connections every 5 minutes to prevent idle timeout
    """

    def __init__(self, conn_str, pool_pre_ping=True, pool_recycle=300):
        self.conn_str = conn_str
        self.engine = sa.create_engine(
            conn_str,
            pool_pre_ping=pool_pre_ping,
            pool_recycle=pool_recycle,
        )
        self.meta = sa.MetaData()
        self.meta.reflect(bind=self.engine)
        self.meta.bind = self.engine
        self.conn = self.engine.connect()
        self.meta.conn = self.conn
        self._tables = {}


# Initialize database using fastsql (MiniDataAPI spec)
# Local development: SQLite (default when DATABASE_URL not set)
# Production: PostgreSQL (when DATABASE_URL is set to postgresql://...)
#
# NOTE: For Render deployment, use the Supabase Supavisor pooler connection string
# (aws-0-{region}.pooler.supabase.com) which supports IPv4, not the direct connection
# (db.{project}.supabase.co) which uses IPv6.

# Ensure data directory exists for SQLite
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Log which database we're using
if DATABASE_URL.startswith("postgresql"):
    logger.info("Using PostgreSQL database with connection pooling (pool_pre_ping=True, pool_recycle=300)")
    db = PostgresDatabase(DATABASE_URL)
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
