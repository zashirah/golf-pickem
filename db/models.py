"""Database table definitions."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    id: int
    username: str
    password_hash: str
    display_name: Optional[str] = None
    groupme_name: Optional[str] = None
    is_admin: bool = False
    created_at: Optional[str] = None


@dataclass
class Session:
    id: int
    user_id: int
    token: str
    expires_at: str
    created_at: Optional[str] = None


@dataclass
class AppSetting:
    id: int
    key: str
    value: str


@dataclass
class Tournament:
    id: int
    datagolf_id: Optional[str] = None
    datagolf_name: Optional[str] = None  # Exact event name from DataGolf API for matching
    name: str = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: str = "upcoming"  # upcoming, active, completed
    picks_locked: bool = False
    last_synced_at: Optional[str] = None  # When results were last synced from DataGolf
    entry_price: Optional[int] = None  # Price for 1 entry (in dollars)
    three_entry_price: Optional[int] = None  # Discounted price for 3 entries (in dollars)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Golfer:
    id: int
    datagolf_id: Optional[str] = None
    name: str = ""
    country: Optional[str] = None
    owgr: Optional[int] = None
    dg_skill: Optional[float] = None
    updated_at: Optional[str] = None


@dataclass
class TournamentField:
    id: int
    tournament_id: int
    golfer_id: int
    tier: int  # 1-4
    odds: Optional[float] = None
    created_at: Optional[str] = None


@dataclass
class Pick:
    id: int
    user_id: int
    tournament_id: int
    entry_number: int = 1  # Supports multiple entries per user per tournament
    tier1_golfer_id: Optional[int] = None
    tier2_golfer_id: Optional[int] = None
    tier3_golfer_id: Optional[int] = None
    tier4_golfer_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class TournamentResult:
    id: int
    tournament_id: int
    golfer_id: int
    position: Optional[int] = None  # None = missed cut/WD
    score_to_par: Optional[int] = None
    status: str = "active"  # active, cut, wd, dq, finished
    round_num: Optional[int] = None
    thru: Optional[int] = None
    updated_at: Optional[str] = None


@dataclass
class PickemStanding:
    id: int
    tournament_id: int
    user_id: int
    entry_number: int = 1  # Matches pick entry_number
    tier1_position: Optional[int] = None
    tier2_position: Optional[int] = None
    tier3_position: Optional[int] = None
    tier4_position: Optional[int] = None
    best_two_total: Optional[int] = None
    rank: Optional[int] = None
    updated_at: Optional[str] = None


def create_tables(db):
    """Create all database tables and return table references."""

    users = db.create(
        User,
        pk='id',
        transform=True
    )

    sessions = db.create(
        Session,
        pk='id',
        transform=True
    )

    app_settings = db.create(
        AppSetting,
        pk='id',
        transform=True
    )

    tournaments = db.create(
        Tournament,
        pk='id',
        transform=True
    )

    golfers = db.create(
        Golfer,
        pk='id',
        transform=True
    )

    tournament_field = db.create(
        TournamentField,
        pk='id',
        transform=True
    )

    picks = db.create(
        Pick,
        pk='id',
        transform=True
    )

    tournament_results = db.create(
        TournamentResult,
        pk='id',
        transform=True
    )

    pickem_standings = db.create(
        PickemStanding,
        pk='id',
        transform=True
    )

    return {
        'users': users,
        'sessions': sessions,
        'app_settings': app_settings,
        'tournaments': tournaments,
        'golfers': golfers,
        'tournament_field': tournament_field,
        'picks': picks,
        'tournament_results': tournament_results,
        'pickem_standings': pickem_standings
    }


def create_season_standings_view(db):
    """Create or replace the season_standings_view for aggregating season-long stats.

    This VIEW dynamically aggregates user performance across all tournaments in a calendar year,
    tracking total score, wins, top finishes, average position, and total winnings.
    """
    import sqlalchemy as sa

    # Determine database type from connection string
    is_postgres = hasattr(db, 'conn_str') and db.conn_str.startswith('postgresql')

    # Use appropriate date extraction function
    year_expr = "EXTRACT(YEAR FROM t.start_date)::text" if is_postgres else "strftime('%Y', t.start_date)"

    # Drop existing view if it exists (for idempotency)
    drop_sql = "DROP VIEW IF EXISTS season_standings_view;"

    # Create VIEW with dynamic aggregation
    create_sql = f"""
CREATE VIEW season_standings_view AS
SELECT
    {year_expr} as season_year,
    u.id as user_id,
    u.display_name,

    -- Core stats
    COUNT(DISTINCT ps.tournament_id) as tournaments_played,
    COUNT(ps.id) as total_entries,
    SUM(CASE WHEN ps.best_two_total IS NOT NULL THEN ps.best_two_total ELSE 0 END) as total_score,

    -- Finish counts
    SUM(CASE WHEN ps.rank = 1 THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN ps.rank <= 3 THEN 1 ELSE 0 END) as top3_finishes,
    SUM(CASE WHEN ps.rank <= 5 THEN 1 ELSE 0 END) as top5_finishes,
    SUM(CASE WHEN ps.rank <= 10 THEN 1 ELSE 0 END) as top10_finishes,

    -- Performance metrics
    AVG(CAST(ps.rank AS {'DECIMAL' if is_postgres else 'FLOAT'})) as average_position,
    MIN(ps.rank) as best_finish,

    -- Winnings (sum of purses for tournaments won)
    SUM(
        CASE WHEN ps.rank = 1 AND t.entry_price IS NOT NULL
        THEN t.entry_price * (SELECT COUNT(*) FROM picks WHERE tournament_id = t.id)
        ELSE 0 END
    ) as total_winnings

FROM users u
JOIN pickem_standings ps ON u.id = ps.user_id
JOIN tournaments t ON ps.tournament_id = t.id
WHERE t.status = 'completed'
  AND ps.best_two_total IS NOT NULL
GROUP BY season_year, u.id, u.display_name
ORDER BY total_score ASC;
"""

    try:
        # Execute drop and create using SQLAlchemy text()
        db.conn.execute(sa.text(drop_sql))
        db.conn.execute(sa.text(create_sql))
        print("Created season_standings_view successfully")
    except Exception as e:
        print(f"Error creating season_standings_view: {e}")
        raise
