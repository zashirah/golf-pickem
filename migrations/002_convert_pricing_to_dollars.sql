-- Migration: Convert pricing from cents to dollars
-- Date: 2026-01-20
-- Description: Convert all existing tournament pricing from cents to dollars,
--              preserving any custom pricing that has already been configured.

UPDATE tournament 
SET entry_price = entry_price / 100,
    three_entry_price = three_entry_price / 100
WHERE entry_price IS NOT NULL;
