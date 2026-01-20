# Golf Pick'em - Project Status

## Tech Stack
- **Framework**: FastHTML (Python HTMX)
- **Database**: SQLite
- **External API**: DataGolf API
- **Auth**: Session-based with SHA-256 password hashing

## Current Branch: `refactor`

## Architecture Overview
```
golf-pickem/
├── app.py              # App entry point (~45 lines) - init & route registration
├── config.py           # Environment config
├── components/         # Reusable UI (page_shell, card, alert)
│   └── layout.py       # Page layout components
├── db/                 # Database layer & models
│   ├── __init__.py     # DB initialization
│   └── models.py       # Table definitions
├── routes/             # Route handlers (modular)
│   ├── __init__.py     # Route exports
│   ├── utils.py        # Shared helpers (auth decorators, formatters)
│   ├── auth.py         # Login, register, logout
│   ├── home.py         # Home/dashboard, static files
│   ├── picks.py        # Pick management (view, edit, delete)
│   ├── leaderboard.py  # Leaderboard display, score refresh
│   └── admin.py        # Admin dashboard, sync, field management
├── services/           # Business logic
│   ├── auth.py         # AuthService
│   ├── datagolf.py     # DataGolf API client
│   └── scoring.py      # ScoringService
├── static/             # CSS
└── data/               # SQLite DB
```

## Completed
- [x] Project restructure from monolithic main.py to modular architecture
- [x] Database layer with models (users, sessions, tournaments, golfers, picks, etc.)
- [x] Authentication system (login, register, sessions, invite-only)
- [x] Admin dashboard (sync tournaments, manage fields, generate invites)
- [x] Pick'em game logic (4-tier picks, best 2 of 4 scoring)
- [x] DataGolf API integration (tournaments, golfers, live results)
- [x] Leaderboard with live scoring and thru info (shows "F" for finished, hole number for in-progress)
- [x] Reusable UI components
- [x] Multiple entries per user per tournament
- [x] DQ logic for entries with <2 valid picks (instead of penalty scoring)
- [x] Redesigned picks page with summary/edit mode flow
- [x] Tournament selector on leaderboard (view active or completed tournaments)
- [x] Status badges on leaderboard (Live/Final)
- [x] **Split app.py routes into separate route modules** (home, picks, leaderboard, admin)
- [x] **Tournament sync validation** - Prevents syncing incorrect tournament data by validating API event_name against selected tournament
- [x] **Production-ready logging** - Replaced all print() statements with proper logging for debugging and monitoring
- [x] **Mobile-first CSS implementation** - Card layouts, expandable leaderboard entries, touch-optimized UI

## In Progress
- [ ] _None currently_

## Next Steps / Backlog
- [ ] **Admin bulk edit for existing users' GroupMe names** - Add admin UI to set `groupme_name` for existing users who registered before this field was required. Could be a simple form on the admin dashboard with dropdowns/inputs for each user without a GroupMe name.
- [ ] **PostgreSQL/Supabase integration** - Replace SQLite with Postgres for production; wire `DATABASE_URL`, migrations, and deployment docs
- [ ] **Upgrade password hashing to bcrypt** - Current implementation uses SHA-256 with salt, which works but bcrypt/argon2 is more secure for password storage (resistant to GPU attacks, configurable work factor). Low priority for MVP but should be done before public launch.
- [ ] **Automatic tournament status updates** - Set tournaments to "active" on Thursday (tournament start) and "completed" after Sunday. Consider Tuesday-Monday as "tournament week" for picks.
- [ ] Add input validation layer
- [ ] Improve error handling (currently silent in sync operations)
- [ ] Add tests
- [ ] Optimize DB queries (currently fetches all then filters)
- [ ] Fix column naming (tier*_position stores scores, not positions)
- [ ] Add database migrations system
- [ ] Commit refactor branch changes
- [ ] Add entry limits (max entries per user per tournament)

## Data Sync Architecture

### Current Flow
```
DataGolf API  ──(manual trigger)──►  SQLite DB  ──(reads)──►  Leaderboard
```

**Two admin sync operations:**
1. **`/admin/sync`** - Syncs players, rankings, tournaments, tournament field
   - Run occasionally (weekly or when new tournament starts)
   - Populates: `golfer`, `tournament`, `tournament_field` tables

2. **`/admin/sync-results`** - Syncs live scores for active tournament
   - Run during tournaments to update leaderboard
   - Fetches from `preds/live-tournament-stats` endpoint
   - Updates: `tournament_result` table (score_to_par, position, thru, status)
   - Recalculates: `pickem_standing` table

### DataGolf API Endpoints Used
| Endpoint | Purpose | When to Call |
|----------|---------|--------------|
| `get-player-list` | All players with IDs | Initial setup |
| `preds/get-dg-rankings` | Player skill ratings | Weekly |
| `get-schedule` | Tournament schedule | Start of season |
| `field-updates` | Tournament field & tiers | Before tournament |
| `preds/live-tournament-stats` | Live scores, positions, thru | During tournament |

### Options for More Frequent Updates

**Option 1: Background Cron Job (Recommended)**
- Add a scheduled task that runs `/admin/sync-results` every 5-10 minutes during tournament hours (Thu-Sun, 7am-8pm ET)
- Could use: Python `schedule` library, system cron, or a task queue like Celery
- Pros: Simple, respects API limits, keeps DB as source of truth
- Cons: Requires background process

**Option 2: On-Demand API Fetch with Cache**
- Fetch from DataGolf API when viewing leaderboard, cache for 2-5 minutes
- Pros: Always fresh data, no background job needed
- Cons: Slower page loads, harder to manage API rate limits

**Option 3: Hybrid Approach**
- Keep DB as source of truth, but add "Refresh" button on leaderboard
- Show "Last updated: X minutes ago" timestamp
- Users can manually refresh if needed

### API Considerations
- DataGolf API is a paid service ([datagolf.com/api-access](https://datagolf.com/api-access))
- Rate limits not publicly documented - check your subscription tier
- Live stats endpoint updates frequently during tournament play

## Known Issues / Tech Debt
1. ~~All routes in single app.py file (~900 lines)~~ **FIXED** - Routes now split into modules
2. No migration system for schema changes
3. Limited error handling in API sync operations
4. Scoring columns misnamed (`tier*_position` stores scores)
5. No input validation - FastHTML extracts params directly

## Session Notes
_Add notes here at the end of each session to provide context for the next one._

### Session: 2026-01-18
- Created PROJECT_STATUS.md for cross-session continuity
- Reviewed full codebase structure after refactor
- App is functional with modular architecture in place

### Session: 2026-01-19 (Morning)
- Fixed leaderboard scoring bug (was showing position instead of score_to_par)
- Added "thru" info to leaderboard (shows "F" for finished, hole number for in-progress)
- Created dev test users (Alice, Bob, Charlie) with simulated picks
- **Implemented multiple entries feature:**
  - Added `entry_number` field to picks and pickem_standings tables
  - Updated ScoringService to handle multiple entries per user
  - Leaderboard shows entry numbers when user has multiple entries (e.g., "zach (2)")

### Session: 2026-01-19 (Continued)
- **Fixed DQ scoring logic:** Entries with <2 valid picks now show "DQ" instead of penalty score
- **Redesigned picks page UX:**
  - Summary view: Shows entries in a table with Edit/Delete buttons
  - Edit mode: Only shows tier options when clicking Edit or "+ New Entry"
  - After save: Returns to summary view (not leaderboard)
  - New users auto-enter edit mode for first entry
  - Added "< Back to My Picks" navigation
  - Delete entry functionality (can't delete last entry)
- **Added tournament selector to leaderboard:**
  - Dropdown to switch between active/completed tournaments
  - Defaults to active tournament
  - Shows "(Live)" indicator for active tournaments
  - Status badges: "Live" (green, pulsing) and "Final" (gray)
- **Future feature noted:** Automatic tournament status updates based on dates (Tuesday-Monday tournament week)

**Current test data:**
- 4 users: zach (admin), Alice, Bob, Charlie
- zach has 3 entries for Sony Open (Entry 3 is DQ - only MacIntyre valid)
- Sony Open marked as "completed", American Express marked as "active"
- Leaderboard dropdown shows both tournaments

**Key URLs:**
- `/picks` - Summary view of your entries
- `/picks?edit=1` - Edit Entry 1
- `/picks?edit=4` - Create new Entry 4
- `/leaderboard` - Default to active tournament
- `/leaderboard?tournament_id=1` - View specific tournament

### Session: 2026-01-19 (Evening)
- **Major refactor: Split app.py into modular route files**
  - Created `routes/utils.py` - Shared helpers (auth decorators, `get_current_user`, `format_score`, `get_active_tournament`)
  - Created `routes/home.py` - Home page, dashboard, static files
  - Created `routes/picks.py` - All pick management (view, edit, submit, delete)
  - Created `routes/leaderboard.py` - Leaderboard display, score refresh
  - Created `routes/admin.py` - Admin dashboard, sync operations, field management
  - Updated `routes/__init__.py` - Exports all setup functions
  - Reduced `app.py` from ~1162 lines to ~45 lines (init + route registration only)
- **Architecture improvements:**
  - Route utilities initialized via `init_routes()` with dependency injection
  - Each route module has a `setup_*_routes(app)` function
  - Consistent use of `get_db()` and `get_current_user()` helpers
  - Better separation of concerns

### Session: 2026-01-19 (Late Evening)
- **Fixed critical tournament sync bug:**
  - DataGolf API returns data for current live tournament, not selected tournament
  - Added `_tournament_names_match()` helper with fuzzy matching for validation
  - Sync operations now validate API `event_name` matches selected tournament before updating DB
  - Prevents incorrect data (e.g., Sony Open scores populating American Express results)
  - Cleared 120 incorrect results from test American Express tournament
- **Production readiness improvements:**
  - Replaced all `print()` statements with proper `logging` module
  - Added `.gitignore` entries for Python cache, environment files, data files
  - Improved error handling in sync operations with detailed log messages
- **UI/UX enhancements:**
  - Changed "MC" display to "-" for tournaments that haven't started
  - Enabled deleting last pick (removed restriction)
  - Added Save button at top of picks form for easier access
  - Added `data_tier` attributes to picks table cells for mobile labels
- **Mobile-first CSS implementation:**
  - Added `.mobile-only` and `.desktop-only` visibility classes with 768px breakpoint
  - Implemented card layouts for mobile: header, buttons, picks, entries, leaderboard
  - Created expandable leaderboard cards using native `<details>`/`<summary>` elements
  - Mobile cards show: rank, player name, total score (collapsed), golfer details (expandable)
  - Removed conflicting old table-to-card transformation CSS
  - Optimized for 375px mobile width with proper touch targets and spacing

### Session: 2026-01-19 (GroupMe Feature Completion)
- **Applied PostgreSQL migration to production:**
  - Ran migration 001 manually against Supabase database
  - Added `groupme_name` column to user table
  - Added pricing fields (`entry_price`, `three_entry_price`) to tournament table
  - Updated MIGRATIONS.md to reflect production deployment
- **Made GroupMe name required for new users:**
  - Removed `display_name` field from registration form
  - Made `groupme_name` required with GroupMe membership verification
  - Set `display_name` = `groupme_name` in DB for backwards compatibility
  - Existing users without `groupme_name` display username as fallback
- **Replaced `display_name` with `groupme_name` throughout UI:**
  - Updated welcome message, nav header, leaderboard, pick notifications
  - All user displays now use `groupme_name or username` fallback pattern
  - Ensures existing users without GroupMe names still display correctly
- **Added profile page for editing GroupMe name:**
  - New `/profile` route accessible via clicking username in nav
  - Form to update GroupMe name with live verification against GroupMe API
  - Updates both `groupme_name` and `display_name` for consistency
  - Shows success/error messages after update
- **Admin improvements:**
  - Added "GroupMe Name" column to admin Users table
  - Shows "-" for users without GroupMe names (helps identify who needs values added)
- **Documented future feature:** Admin bulk edit for existing users' GroupMe names in PROJECT_STATUS.md backlog

**Architecture changes:**
- Registration now enforces GroupMe membership verification
- Profile page uses same verification logic for updates
- Navigation header username is now clickable link to profile
- All display names consolidated to use `groupme_name` as primary field

**Note:** `display_name` column kept in database for backwards compatibility but UI now primarily uses `groupme_name`.

---
*Last updated: 2026-01-19*
