#!/usr/bin/env python3
"""Mark some tournaments as completed for testing season leaderboard."""

from fastsql import Database
import sqlalchemy as sa

LOCAL_URL = 'sqlite:///data/golf_pickem_test.db'
db = Database(LOCAL_URL)

print("Marking tournaments as completed for testing...")
print("-" * 60)

# Check current status
query = "SELECT id, name, status FROM tournament ORDER BY id"
tournaments = list(db.conn.execute(sa.text(query)))

print("\nCurrent tournament statuses:")
for row in tournaments:
    r = dict(row._mapping)
    print(f"  {r['id']}: {r['name']} - {r['status']}")

# Mark first 3 tournaments as completed
tournaments_to_complete = [1, 2]  # Sony Open and American Express

print(f"\nMarking tournaments {tournaments_to_complete} as completed...")

for tid in tournaments_to_complete:
    update_query = "UPDATE tournament SET status = 'completed' WHERE id = :tid"
    db.conn.execute(sa.text(update_query), {'tid': tid})

db.conn.commit()

# Verify
print("\nUpdated tournament statuses:")
tournaments = list(db.conn.execute(sa.text(query)))
for row in tournaments:
    r = dict(row._mapping)
    status = r['status']
    icon = "✓" if status == 'completed' else " "
    print(f"  {icon} {r['id']}: {r['name']} - {r['status']}")

# Check if there are standings for completed tournaments
print("\nChecking pickem_standings for completed tournaments...")
standings_query = """
SELECT t.id, t.name, COUNT(ps.id) as standing_count
FROM tournament t
LEFT JOIN pickem_standing ps ON t.id = ps.tournament_id
WHERE t.status = 'completed'
GROUP BY t.id, t.name
"""
standings = list(db.conn.execute(sa.text(standings_query)))

for row in standings:
    r = dict(row._mapping)
    print(f"  Tournament {r['id']}: {r['name']} - {r['standing_count']} standings")

print("\n" + "=" * 60)
print("✓ Test data ready!")
print("=" * 60)
print("\nNow visit http://localhost:8000/season-leaderboard to see the aggregated stats!")
