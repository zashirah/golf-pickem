-- Add last_synced_at column to tournament table
ALTER TABLE tournament ADD COLUMN IF NOT EXISTS last_synced_at TEXT;
