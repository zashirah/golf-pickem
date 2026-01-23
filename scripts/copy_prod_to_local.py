#!/usr/bin/env python3
"""Copy production database to local SQLite for testing."""

import os
from pathlib import Path
from dotenv import load_dotenv
from fastsql import Database

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Connect to production (read-only)
PROD_URL = os.environ.get('PROD_DATABASE_URL')  # Supabase pooler URL
LOCAL_URL = 'sqlite:///data/golf_pickem_test.db'

def copy_table(prod_db, local_db, table_name):
    """Copy all rows from prod table to local table."""
    import sqlalchemy as sa

    # Query production table directly
    try:
        # Need to quote table name in case it's a reserved word (like 'user')
        query = f'SELECT * FROM "{table_name}"'
        rows = list(prod_db.conn.execute(sa.text(query)))

        if rows:
            # Convert rows to dicts - explicitly extract all column values
            row_dicts = []
            for row in rows:
                row_dict = {}
                for key in row._mapping.keys():
                    row_dict[key] = row._mapping[key]
                row_dicts.append(row_dict)

            # Insert into local database using raw SQL for reliability
            if row_dicts:
                # Get column names from first row
                columns = list(row_dicts[0].keys())
                placeholders = ', '.join([f':{col}' for col in columns])
                cols_str = ', '.join(columns)

                insert_query = f'INSERT INTO "{table_name}" ({cols_str}) VALUES ({placeholders})'

                for row_dict in row_dicts:
                    local_db.conn.execute(sa.text(insert_query), row_dict)

                # Commit the transaction
                local_db.conn.commit()

                print(f"Copied {len(row_dicts)} rows from {table_name}")
        else:
            print(f"No rows to copy from {table_name}")
    except Exception as e:
        print(f"Error copying {table_name}: {e}")

# Tables to copy (in dependency order)
# Note: fastsql creates singular table names from dataclass names
TABLES = [
    'user',
    'app_setting',
    'tournament',
    'golfer',
    'tournament_field',
    'pick',
    'tournament_result',
    'pickem_standing',
    'session',  # Optional
]

def main():
    if not PROD_URL:
        print("Error: PROD_DATABASE_URL environment variable not set")
        print("Usage: export PROD_DATABASE_URL='postgresql://...'")
        return

    print(f"Copying from production to {LOCAL_URL}...")
    print("-" * 60)

    # Initialize local database with tables first
    print("Initializing local database tables...")
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from db.models import create_tables
    local_db = Database(LOCAL_URL)
    create_tables(local_db)
    print("✓ Local tables created\n")

    # Connect to production
    prod_db = Database(PROD_URL)

    for table in TABLES:
        try:
            copy_table(prod_db, local_db, table)
        except Exception as e:
            print(f"Error copying {table}: {e}")

    print("-" * 60)
    print("✓ Database copy complete!")
    print(f"\nTo use the test database, run:")
    print(f"  export DATABASE_URL='{LOCAL_URL}'")
    print(f"  python app.py")

if __name__ == "__main__":
    main()
