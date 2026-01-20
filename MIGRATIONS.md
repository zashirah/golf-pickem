# Database Migrations

## Overview
This document describes database schema migrations for the Golf Pick'em application.

## Migration 001: Add GroupMe and Pricing Fields
**Date:** 2026-01-19
**Status:** ✅ Applied to local database

### Purpose
Adds support for:
- GroupMe integration and user identification
- Tournament entry pricing and purse tracking

### Changes

#### User Table
- **Added:** `groupme_name` (TEXT, nullable)
  - Stores the user's GroupMe display name
  - Used for group membership verification and notifications
  - Optional - users can leave blank if not in GroupMe group

#### Tournament Table
- **Added:** `datagolf_name` (TEXT, nullable)
  - Exact event name from DataGolf API
  - Used for matching tournaments with live scoring data
  - Populated during sync operations

- **Added:** `last_synced_at` (TEXT, nullable)
  - ISO timestamp of last results sync
  - Used to avoid excessive API calls
  - Auto-synced every 10+ minutes on active tournaments

- **Added:** `entry_price` (INTEGER, nullable)
  - Price in cents for single entry
  - Used to calculate tournament purse
  - Leave NULL/0 for free tournaments

- **Added:** `three_entry_price` (INTEGER, nullable)
  - Price in cents for 3-entry package
  - For reference only - manual tracking needed
  - Leave NULL/0 if not offered

### Running Migrations

#### Local Development (SQLite)
The migration has already been applied to your local database.

If you need to run it again on a fresh database:
```bash
sqlite3 data/golf_pickem.db < migrations/001_add_groupme_and_pricing_fields.sql
```

#### Production (PostgreSQL via Supabase)

**Option 1: Using Supabase SQL Editor (Recommended)**
1. Go to Supabase Dashboard → SQL Editor
2. Create new query
3. Copy contents of `migrations/001_add_groupme_and_pricing_fields.postgresql.sql`
4. Paste into editor
5. Click "Run"

**Option 2: Using psql CLI**
```bash
psql -U postgres \
  -h {YOUR_SUPABASE_HOST} \
  -d postgres \
  < migrations/001_add_groupme_and_pricing_fields.postgresql.sql
```

**Option 3: Using Render Dashboard (if using Render Postgres)**
1. Go to Render Dashboard → PostgreSQL instance
2. Click "Connect" → "External Connection String"
3. Copy connection string
4. Run migration via psql (Option 2)

### Verifying Migration

#### SQLite
```bash
sqlite3 data/golf_pickem.db "PRAGMA table_info(user);"
sqlite3 data/golf_pickem.db "PRAGMA table_info(tournament);"
```

#### PostgreSQL (via psql)
```bash
psql -c "\d \"user\"" {CONNECTION_STRING}
psql -c "\d \"tournament\"" {CONNECTION_STRING}
```

Or in Supabase SQL Editor:
```sql
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'user' ORDER BY ordinal_position;

SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'tournament' ORDER BY ordinal_position;
```

### Rollback (if needed)

#### SQLite
```bash
sqlite3 data/golf_pickem.db
sqlite> ALTER TABLE "user" DROP COLUMN groupme_name;
sqlite> ALTER TABLE "tournament" DROP COLUMN datagolf_name;
sqlite> ALTER TABLE "tournament" DROP COLUMN last_synced_at;
sqlite> ALTER TABLE "tournament" DROP COLUMN entry_price;
sqlite> ALTER TABLE "tournament" DROP COLUMN three_entry_price;
```

#### PostgreSQL
```sql
ALTER TABLE "user" DROP COLUMN groupme_name;
ALTER TABLE "tournament" DROP COLUMN datagolf_name;
ALTER TABLE "tournament" DROP COLUMN last_synced_at;
ALTER TABLE "tournament" DROP COLUMN entry_price;
ALTER TABLE "tournament" DROP COLUMN three_entry_price;
```

### Data Safety Notes
- ✅ All new columns are **nullable** - existing data is unaffected
- ✅ No columns were **removed** - backward compatible
- ✅ No existing data was **modified**
- ✅ Rollback is safe - just removes unused columns

### Next Steps
1. ✅ Local database migrated
2. Run migration against production (Supabase) before deploying code
3. Deploy application code
4. Monitor logs for any schema-related errors
5. Verify GroupMe features work in production

### Future Migrations
- Create `migrations/002_*.sql` files following the same naming convention
- Update this document with new migration details
- Apply in order (001, 002, etc.)
