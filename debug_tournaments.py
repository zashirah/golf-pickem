#!/usr/bin/env python3
"""Debug script to see what tournaments are being returned by the filter function."""

import sys
sys.path.insert(0, '/Users/zachshirah/code/projects/golf-pickem')

from db import init_db
from routes.admin import filter_and_sort_tournaments

# Initialize database
init_db()

# Get database
from db import db

# Fetch all tournaments
all_tournaments = list(db.tournaments())

print("=" * 80)
print("ALL TOURNAMENTS FROM DATABASE")
print("=" * 80)
for t in all_tournaments:
    print(f"ID: {t.id:2d} | Name: {t.name:50s} | Status: {t.status:10s}")

print("\n" + "=" * 80)
print("ACTIVE/UPCOMING TAB (tab='active')")
print("=" * 80)
active_upcoming = filter_and_sort_tournaments(all_tournaments, 'active')
for i, t in enumerate(active_upcoming):
    print(f"{i+1}. ID: {t.id:2d} | Name: {t.name:50s} | Status: {t.status:10s}")

print("\n" + "=" * 80)
print("COMPLETED TAB (tab='completed')")
print("=" * 80)
completed = filter_and_sort_tournaments(all_tournaments, 'completed')
for i, t in enumerate(completed):
    print(f"{i+1}. ID: {t.id:2d} | Name: {t.name:50s} | Status: {t.status:10s}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total in DB: {len(all_tournaments)}")
print(f"Active/Upcoming: {len(active_upcoming)}")
print(f"Completed: {len(completed)}")
print(f"Sum: {len(active_upcoming) + len(completed)}")

# Check for duplicates
print("\n" + "=" * 80)
print("DUPLICATE CHECK")
print("=" * 80)
active_upcoming_ids = [t.id for t in active_upcoming]
completed_ids = [t.id for t in completed]

duplicates = set(active_upcoming_ids) & set(completed_ids)
if duplicates:
    print(f"⚠️  DUPLICATES FOUND: {duplicates}")
    for dup_id in duplicates:
        t = [t for t in all_tournaments if t.id == dup_id][0]
        print(f"   ID {dup_id}: {t.name} (Status: {t.status})")
else:
    print("✓ No duplicates - each tournament appears in only one tab")
