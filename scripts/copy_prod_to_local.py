#!/usr/bin/env python3
"""Copy production database to local SQLite for testing."""

import os
from fastsql import Database

# Connect to production (read-only)
PROD_URL = os.environ.get('PROD_DATABASE_URL')  # Supabase pooler URL
LOCAL_URL = 'sqlite:///data/golf_pickem_test.db'

def copy_table(prod_db, local_db, table_name):
    """Copy all rows from prod table to local table."""
    rows = list(prod_db[table_name]())
    if rows:
        local_db[table_name].insert_all(rows)
        print(f"Copied {len(rows)} rows from {table_name}")
    else:
        print(f"No rows to copy from {table_name}")

# Tables to copy (in dependency order)
TABLES = [
    'users',
    'app_settings',
    'tournaments',
    'golfers',
    'tournament_field',
    'picks',
    'tournament_results',
    'pickem_standings',
    'sessions',  # Optional
]

def main():
    if not PROD_URL:
        print("Error: PROD_DATABASE_URL environment variable not set")
        print("Usage: export PROD_DATABASE_URL='postgresql://...'")
        return

    print(f"Copying from production to {LOCAL_URL}...")
    print("-" * 60)

    # Run copy
    prod_db = Database(PROD_URL)
    local_db = Database(LOCAL_URL)

    for table in TABLES:
        try:
            copy_table(prod_db, local_db, table)
        except Exception as e:
            print(f"Error copying {table}: {e}")

    print("-" * 60)
    print("Database copy complete!")
    print(f"\nTo use the test database, run:")
    print(f"  export DATABASE_URL='{LOCAL_URL}'")
    print(f"  python app.py")

if __name__ == "__main__":
    main()
