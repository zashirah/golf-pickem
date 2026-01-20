-- Migration: Add GroupMe and pricing fields (PostgreSQL)
-- Date: 2026-01-19
-- Adds support for GroupMe integration and tournament pricing
--
-- For Render/Supabase:
-- psql -U postgres -h {host} -d {database} < migrations/001_add_groupme_and_pricing_fields.postgresql.sql
-- Or use Supabase SQL editor

-- Add groupme_name to user table (if not exists)
ALTER TABLE "user"
ADD COLUMN groupme_name TEXT;

-- Add missing fields to tournament table (if not exists)
ALTER TABLE "tournament"
ADD COLUMN datagolf_name TEXT,
ADD COLUMN last_synced_at TEXT,
ADD COLUMN entry_price INTEGER,
ADD COLUMN three_entry_price INTEGER;
