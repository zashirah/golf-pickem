-- Database Cleanup Script for Golf Pick'em
-- Run this in Supabase SQL Editor to clean up duplicate tables
-- 
-- The app uses SINGULAR table names (created by fastsql from class names):
--   user, session, app_setting, tournament, golfer, tournament_field, pick, tournament_result, pickem_standing
--
-- If plural tables exist, they are duplicates that should be dropped.

-- Step 1: Check what tables exist
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Step 2: Drop duplicate PLURAL tables (if they exist)
-- Uncomment and run these if you see plural versions:
-- DROP TABLE IF EXISTS users CASCADE;
-- DROP TABLE IF EXISTS sessions CASCADE;
-- DROP TABLE IF EXISTS app_settings CASCADE;
-- DROP TABLE IF EXISTS tournaments CASCADE;
-- DROP TABLE IF EXISTS golfers CASCADE;
-- DROP TABLE IF EXISTS tournament_fields CASCADE;
-- DROP TABLE IF EXISTS picks CASCADE;
-- DROP TABLE IF EXISTS tournament_results CASCADE;
-- DROP TABLE IF EXISTS pickem_standings CASCADE;

-- Step 3: Add unique constraints for upserts (if not exist)
-- These prevent duplicate entries and enable ON CONFLICT upserts

-- Golfer unique constraint
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'golfer_datagolf_id_unique') THEN
        ALTER TABLE golfer ADD CONSTRAINT golfer_datagolf_id_unique UNIQUE (datagolf_id);
    END IF;
END $$;

-- Tournament unique constraint
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tournament_datagolf_id_unique') THEN
        ALTER TABLE tournament ADD CONSTRAINT tournament_datagolf_id_unique UNIQUE (datagolf_id);
    END IF;
END $$;

-- Step 4: Clear data tables for fresh sync (optional - uncomment if needed)
-- TRUNCATE TABLE golfer CASCADE;
-- TRUNCATE TABLE tournament CASCADE;
-- TRUNCATE TABLE pick CASCADE;
-- TRUNCATE TABLE tournament_field CASCADE;
-- TRUNCATE TABLE tournament_result CASCADE;
-- TRUNCATE TABLE pickem_standing CASCADE;

-- Keep user and session data:
-- DO NOT truncate: user, session, app_setting
