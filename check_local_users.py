#!/usr/bin/env python3
"""Check users in local test database."""

import sqlalchemy as sa
from fastsql import Database

LOCAL_URL = 'sqlite:///data/golf_pickem_test.db'

db = Database(LOCAL_URL)

print("Users in local test database:")
print("-" * 60)

query = "SELECT id, username, display_name, groupme_name, is_admin FROM user"
result = list(db.conn.execute(sa.text(query)))

for row in result:
    row_dict = dict(row._mapping)
    print(f"ID: {row_dict['id']}")
    print(f"  Username: {row_dict['username']}")
    print(f"  Display Name: {row_dict['display_name']}")
    print(f"  GroupMe Name: {row_dict['groupme_name']}")
    print(f"  Is Admin: {row_dict['is_admin']}")
    print()

print(f"Total users: {len(result)}")
print("\nNote: Passwords are hashed, so you'll need to know the original password")
print("or create a new user to test locally.")
