-- Migration: Add GroupMe and pricing fields
-- Date: 2026-01-19
-- Adds support for GroupMe integration and tournament pricing

-- SQLite
-- To run: sqlite3 data/golf_pickem.db < migrations/001_add_groupme_and_pricing_fields.sql

-- Add groupme_name to user table
ALTER TABLE "user" ADD COLUMN [groupme_name] TEXT;

-- Add missing fields to tournament table
ALTER TABLE "tournament" ADD COLUMN [datagolf_name] TEXT;
ALTER TABLE "tournament" ADD COLUMN [last_synced_at] TEXT;
ALTER TABLE "tournament" ADD COLUMN [entry_price] INTEGER;
ALTER TABLE "tournament" ADD COLUMN [three_entry_price] INTEGER;
