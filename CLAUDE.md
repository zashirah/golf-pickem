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
- `services/groupme.py` - GroupMeClient: bot messaging and group member verification

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
| `users` | User accounts (includes `groupme_name` for GroupMe notifications) |
| `sessions` | Active sessions |
| `tournaments` | Tournament definitions (status: upcoming/active/completed, includes `entry_price` and `three_entry_price` for money tracking) |
| `golfers` | Player data from DataGolf |
| `tournament_field` | Golfer + tier assignments per tournament |
| `picks` | User picks (supports multiple entries via `entry_number`) |
| `tournament_results` | Live scores (score_to_par, position, thru, status) |
| `pickem_standings` | Calculated leaderboard positions |
| `app_settings` | Key-value store for runtime configuration (e.g., `groupme_bot_id`) |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATAGOLF_API_KEY` | Yes | DataGolf API key |
| `SECRET_KEY` | Yes | Session encryption secret |
| `DATABASE_URL` | No | SQLAlchemy connection string. Default: `sqlite:///data/golf_pickem.db`. For PostgreSQL: `postgresql://user:pass@host:5432/dbname` (URL-encode special chars in password) |
| `PORT` | No | Server port (default: 8000) |
| `GROUPME_BOT_ID` | No | GroupMe bot ID for sending messages (optional, can also be set via admin UI) |
| `GROUPME_ACCESS_TOKEN` | No | GroupMe API access token for member verification during registration |
| `GROUPME_GROUP_ID` | No | GroupMe group ID to verify membership |

## Deployment Notes

### Render + Supabase

**Important:** Render's free tier only supports IPv4, but Supabase direct connections use IPv6. You must use the **Supavisor pooler** connection string:

- ❌ Direct (IPv6): `postgresql://postgres:pass@db.{project}.supabase.co:5432/postgres`
- ✅ Pooler (IPv4): `postgresql://postgres.{project}:pass@aws-0-{region}.pooler.supabase.com:6543/postgres`

Get the pooler connection string from Supabase Dashboard → Connect → Transaction/Session pooler.

## GroupMe Integration

Golf Pick'em can send notifications to a GroupMe group for pick creation/updates and leaderboard announcements.

### Setup

1. **Create a GroupMe Bot:**
   - Go to https://dev.groupme.com/
   - Create a new bot and get the `bot_id`
   - Add the bot to your group

2. **Get API Credentials (for member verification):**
   - At https://dev.groupme.com/, get your personal `access_token`
   - Find your group ID from the GroupMe app/API

3. **Set Environment Variables:**
   ```bash
   GROUPME_BOT_ID=your_bot_id_here          # Optional: can set via admin UI
   GROUPME_ACCESS_TOKEN=your_access_token   # For member verification
   GROUPME_GROUP_ID=your_group_id           # For member verification
   ```

### Features

**Automatic Notifications:**
- Pick creation/update: `🏌️ {user} created/updated Entry N`
- Includes all 4 tier picks and current tournament purse
- Sent after every pick submission

**Manual Leaderboard Send:**
- Admin dashboard has "Send to GroupMe" button
- Formats top 10 standings with scores
- Includes tournament name and purse

**Auto-Send Final Leaderboard:**
- When tournament status changes to completed
- Prefixed with `🏁 FINAL LEADERBOARD:`
- Shows top 10 finishers with final scores

**Member Verification:**
- Registration form requires GroupMe name
- Verifies user is in the configured group
- Blocks registration if name not found (can proceed if verification fails)

### Admin Configuration

- Admin Dashboard → GroupMe Settings section
- Display current bot ID
- Form to update bot ID (stored in `app_settings` table)
- "Send Test Message" button to verify setup
- Bot ID takes priority over `GROUPME_BOT_ID` env var

## Money Tracking

Track tournament entry prices and calculate total purse for payouts.

### Setup

1. **Set Tournament Pricing:**
   - Admin Dashboard → Tournaments table → "Pricing" button per tournament
   - Enter `Single Entry Price` (e.g., $50)
   - Optionally enter `3-Entry Package Price` (e.g., $120)

2. **Manual Price Entry:**
   - Visit `/admin/tournament/{tid}/pricing`
   - Enter prices and save

### Features

**Purse Calculation:**
- Automatically calculated: `total_entries × entry_price = purse`
- Displayed on leaderboard header: `💰 Purse: ${amount}`
- Shown in GroupMe notifications (both pick and leaderboard messages)
- Helper function: `calculate_tournament_purse(tournament, picks)`

**Admin Pricing UI:**
- Tournament table shows current pricing: `$50 | 3-pack: $120`
- Per-tournament pricing configuration page
- Live purse preview based on current entry count

**Purse Display:**
- Leaderboard header shows total purse
- Pick creation messages include purse
- Manual and auto-send leaderboard messages include purse

### Money Management Notes

- Pricing is optional (can run free tournaments)
- 3-entry package price is for reference only (manual tracking of who bought 3-packs)
- Purse calculation uses single entry price × entry count
- Admin must manually track 3-pack purchases and adjust payouts accordingly

## Known Tech Debt

- Column naming: `tier*_position` in `pickem_standings` stores scores, not positions
- No migration system for schema changes
- No test suite
