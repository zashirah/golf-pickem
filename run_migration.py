#!/usr/bin/env python3
"""
Database migration runner for PostgreSQL
Connects to Supabase and runs migration SQL files
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_connection():
    """Create a connection to the PostgreSQL database"""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("❌ ERROR: DATABASE_URL not set in .env")
        sys.exit(1)

    try:
        # Parse the connection string
        # Format: postgresql://user:password@host:port/database
        conn = psycopg2.connect(database_url)
        print("✅ Connected to database")
        return conn
    except psycopg2.Error as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

def run_migration(conn, migration_file):
    """Execute a migration SQL file"""

    if not os.path.exists(migration_file):
        print(f"❌ Migration file not found: {migration_file}")
        sys.exit(1)

    try:
        with open(migration_file, 'r') as f:
            sql_content = f.read()

        # Remove comments and empty lines for cleaner execution
        lines = [line.strip() for line in sql_content.split('\n')]
        statements = []
        current_statement = []

        for line in lines:
            # Skip comments
            if line.startswith('--'):
                continue
            if line:
                current_statement.append(line)
                if line.endswith(';'):
                    statements.append(' '.join(current_statement))
                    current_statement = []

        # Execute each statement
        cursor = conn.cursor()
        for statement in statements:
            if statement.strip():
                print(f"\n▶️  Executing: {statement[:60]}...")
                try:
                    cursor.execute(statement)
                    conn.commit()
                    print(f"   ✅ Success")
                except psycopg2.Error as e:
                    # Check if it's an "already exists" error (which is fine)
                    if "already exists" in str(e) or "duplicate column name" in str(e):
                        print(f"   ⚠️  Column already exists (skipping)")
                        conn.rollback()
                    else:
                        print(f"   ❌ Error: {e}")
                        conn.rollback()
                        raise

        cursor.close()
        print("\n✅ Migration completed successfully!")

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        sys.exit(1)

def verify_schema(conn):
    """Verify that all columns were created"""
    cursor = conn.cursor()

    print("\n📋 Verifying schema...\n")

    # Check user table
    print("User table columns:")
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'user'
        ORDER BY ordinal_position
    """)

    user_cols = cursor.fetchall()
    for col_name, col_type in user_cols:
        marker = "✅" if col_name == "groupme_name" else "  "
        print(f"  {marker} {col_name}: {col_type}")

    # Check tournament table
    print("\nTournament table columns:")
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'tournament'
        ORDER BY ordinal_position
    """)

    tournament_cols = cursor.fetchall()
    for col_name, col_type in tournament_cols:
        new_cols = ["datagolf_name", "last_synced_at", "entry_price", "three_entry_price"]
        marker = "✅" if col_name in new_cols else "  "
        print(f"  {marker} {col_name}: {col_type}")

    cursor.close()

    # Check for required columns
    user_col_names = [col[0] for col in user_cols]
    tournament_col_names = [col[0] for col in tournament_cols]

    required_user_cols = ["groupme_name"]
    required_tournament_cols = ["datagolf_name", "last_synced_at", "entry_price", "three_entry_price"]

    missing_user = [c for c in required_user_cols if c not in user_col_names]
    missing_tournament = [c for c in required_tournament_cols if c not in tournament_col_names]

    if missing_user or missing_tournament:
        print("\n⚠️  Missing columns detected:")
        if missing_user:
            print(f"   User: {missing_user}")
        if missing_tournament:
            print(f"   Tournament: {missing_tournament}")
        return False
    else:
        print("\n✅ All required columns present!")
        return True

def main():
    """Main migration runner"""
    print("🗄️  Golf Pick'em Database Migration Runner\n")

    # Get connection
    conn = get_connection()

    try:
        # Run the PostgreSQL migration
        migration_file = "migrations/001_add_groupme_and_pricing_fields.postgresql.sql"
        print(f"\n▶️  Running migration: {migration_file}\n")
        run_migration(conn, migration_file)

        # Verify the schema
        success = verify_schema(conn)

        if success:
            print("\n🎉 Migration completed and verified successfully!")
            sys.exit(0)
        else:
            print("\n❌ Migration verification failed")
            sys.exit(1)

    finally:
        conn.close()

if __name__ == "__main__":
    main()
