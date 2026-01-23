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


