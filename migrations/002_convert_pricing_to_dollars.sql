-- Migration: Convert pricing from cents to dollars and set defaults
-- Date: 2026-01-20
-- Description: Update all existing tournament pricing to use dollar amounts instead of cents.
--              Set all tournaments to default values: $15 for 1 entry, $35 for 3 entries.

UPDATE tournament 
SET entry_price = 15, 
    three_entry_price = 35;
