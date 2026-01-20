"""Database initialization and connection."""
from fastsql import Database
from config import DATA_DIR, DATABASE_URL
import logging
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError, DBAPIError, PendingRollbackError

logger = logging.getLogger(__name__)


class ResilientConnection:
    """Proxy wrapper that automatically handles connection failures."""

    def __init__(self, engine):
        self.engine = engine
        self._conn = engine.connect()

    def _reconnect(self):
        """Close stale connection and get fresh one."""
        logger.warning("Reconnecting to database due to connection error")
        try:
            self._conn.close()
        except Exception:
            pass
        self._conn = self.engine.connect()

    def execute(self, *args, **kwargs):
        """Execute with automatic retry on connection errors."""
        try:
            return self._conn.execute(*args, **kwargs)
        except (OperationalError, DBAPIError, PendingRollbackError) as e:
            logger.warning(f"Database error: {e}, attempting reconnect...")
            try:
                self._conn.rollback()
            except Exception:
                pass
            self._reconnect()
            # Retry once with fresh connection
            return self._conn.execute(*args, **kwargs)

    def __getattr__(self, name):
        """Delegate all other attributes to the underlying connection."""
        return getattr(self._conn, name)


class PostgresDatabase(Database):
    """Custom Database subclass with robust connection handling for PostgreSQL.

    Handles Supabase free tier idle connection timeouts using a resilient
    connection wrapper that automatically detects and recovers from stale connections.
    """

    def __init__(self, conn_str, pool_pre_ping=True, pool_recycle=300):
        self.conn_str = conn_str

        # Create engine with connection pooling
        self.engine = sa.create_engine(
            conn_str,
            pool_pre_ping=pool_pre_ping,
            pool_recycle=pool_recycle,
        )

        self.meta = sa.MetaData()
        self.meta.reflect(bind=self.engine)
        self.meta.bind = self.engine

        # Use resilient connection wrapper instead of direct connection
        self.conn = ResilientConnection(self.engine)
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
