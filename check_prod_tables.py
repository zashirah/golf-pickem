#!/usr/bin/env python3
"""Check what tables exist in production database."""

import os
from pathlib import Path
from dotenv import load_dotenv
import sqlalchemy as sa
from sqlalchemy import create_engine

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

PROD_URL = os.environ.get('PROD_DATABASE_URL')

if not PROD_URL:
    print("Error: PROD_DATABASE_URL not set")
    exit(1)

print(f"Connecting to production database...")

try:
    engine = create_engine(PROD_URL, pool_pre_ping=True)

    with engine.connect() as conn:
        # List all tables in public schema
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name;
        """
        result = conn.execute(sa.text(query))
        tables = [row[0] for row in result]

        print(f"\nFound {len(tables)} tables in production:")
        for table in tables:
            print(f"  - {table}")

        if not tables:
            print("\n⚠️  No tables found! The database might be empty.")
            print("    Have the tables been created on production yet?")

except Exception as e:
    print(f"Error connecting to production: {e}")
    import traceback
    traceback.print_exc()
