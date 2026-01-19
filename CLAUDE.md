# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Golf Pick'em is a fantasy golf application where users pick one golfer from each of four tiers for PGA tournaments. Scoring uses the best 2 of 4 picks (lowest combined score-to-par wins). Built with FastHTML (Python HTMX framework), with SQLite for local development and PostgreSQL for production.

## Commands

```bash
# Development server
python app.py                    # Runs on http://localhost:8000

# Docker
docker-compose up                # Containerized development
docker build -t golf-pickem .    # Build image

# Dependencies
pip install -r requirements.txt
```

## Architecture

### Entry Point
`app.py` (~50 lines) initializes the database, services, and registers routes via `setup_*_routes(app)` functions.

### Route Module Pattern
Routes are in `routes/` with each module exporting a `setup_*_routes(app)` function:
- `routes/utils.py` - Shared helpers: `get_current_user()`, `get_db()`, `require_auth` decorator, `require_admin` decorator, `format_score()`
- `routes/auth.py` - Login, register, logout
- `routes/home.py` - Dashboard, static files
- `routes/picks.py` - Pick management (view, edit, delete)
- `routes/leaderboard.py` - Leaderboard display
- `routes/admin.py` - Admin dashboard, DataGolf sync operations

Route utilities are initialized via `init_routes(auth_service, db_module)` with dependency injection.

### Database Layer
- `db/__init__.py` - Database initialization using fastsql (MiniDataAPI spec), exposes table references as module-level variables (e.g., `db.users()`, `db.tournaments()`)
- `db/models.py` - Dataclass models (User, Tournament, Pick, etc.) and `create_tables(db)` function
- Uses fastsql with SQLAlchemy: SQLite locally, PostgreSQL in production
- Tables auto-created on startup

### Services
- `services/auth.py` - AuthService: session management, password hashing (SHA-256)
- `services/scoring.py` - ScoringService: calculates best-2-of-4 standings
- `services/datagolf.py` - DataGolf API client for tournaments, players, live scores

### Components
- `components/layout.py` - `page_shell()`, `card()`, reusable UI components

## Key Data Flow

**DataGolf API sync (manual via admin):**
1. `/admin/sync` - Syncs players, rankings, tournaments, tournament field (run weekly or when tournament starts)
2. `/admin/sync-results` - Syncs live scores for active tournament, recalculates standings

**Scoring logic:**
- Each pick has 4 golfers (one per tier)
- Best 2 scores (lowest score-to-par) count
- Entries with <2 valid picks show as "DQ"

## Database Tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts |
| `sessions` | Active sessions |
| `tournaments` | Tournament definitions (status: upcoming/active/completed) |
| `golfers` | Player data from DataGolf |
| `tournament_field` | Golfer + tier assignments per tournament |
| `picks` | User picks (supports multiple entries via `entry_number`) |
| `tournament_results` | Live scores (score_to_par, position, thru, status) |
| `pickem_standings` | Calculated leaderboard positions |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATAGOLF_API_KEY` | Yes | DataGolf API key |
| `SECRET_KEY` | Yes | Session encryption secret |
| `DATABASE_URL` | No | SQLAlchemy connection string. Default: `sqlite:///data/golf_pickem.db`. For PostgreSQL: `postgresql://user:pass@host:5432/dbname` (URL-encode special chars in password) |
| `PORT` | No | Server port (default: 8000) |

## Known Tech Debt

- Column naming: `tier*_position` in `pickem_standings` stores scores, not positions
- No migration system for schema changes
- No test suite
