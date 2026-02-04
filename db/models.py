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
    third_best_score: Optional[int] = None  # 3rd lowest score (None if < 3 made cut)
    has_third_made_cut: Optional[bool] = None  # True if 3rd golfer made cut
    fourth_best_score: Optional[int] = None  # 4th lowest score (None if < 4 made cut)
    has_fourth_made_cut: Optional[bool] = None  # True if 4th golfer made cut
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

    # Add UNIQUE constraints to datagolf_id to prevent duplicates on sync
    # This must be done after table creation
    _add_unique_constraints(db)

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


def _add_unique_constraints(db):
    """Add UNIQUE constraints to datagolf_id columns to prevent duplicates.

    This is safe to call multiple times - SQLite will skip if constraint already exists,
    and PostgreSQL will check if it exists before creating.
    """
    import logging
    from sqlalchemy import text

    logger = logging.getLogger(__name__)

    try:
        with db.engine.connect() as conn:
            # For SQLite, check if constraint exists before creating
            # For PostgreSQL, use ON CONFLICT in upsert instead (doesn't need this constraint)
            from config import DATABASE_URL

            if DATABASE_URL.startswith("sqlite"):
                # SQLite: Add unique constraint on datagolf_id for golfer table
                try:
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_golfer_datagolf_id ON golfer(datagolf_id) WHERE datagolf_id IS NOT NULL"))
                    logger.info("Created UNIQUE index on golfer.datagolf_id")
                except Exception as e:
                    logger.debug(f"Index on golfer.datagolf_id already exists or error: {e}")

                # SQLite: Add unique constraint on datagolf_id for tournament table
                try:
                    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_tournament_datagolf_id ON tournament(datagolf_id) WHERE datagolf_id IS NOT NULL"))
                    logger.info("Created UNIQUE index on tournament.datagolf_id")
                except Exception as e:
                    logger.debug(f"Index on tournament.datagolf_id already exists or error: {e}")

            conn.commit()
    except Exception as e:
        logger.warning(f"Could not create UNIQUE constraints: {e}. Upserts may create duplicates.")


