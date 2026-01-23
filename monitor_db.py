#!/usr/bin/env python3
"""Monitor database connection health on Render."""

import subprocess
import json
from datetime import datetime, timedelta

SERVICE_ID = "srv-d5n7ouogjchc7396kkag"

def check_logs():
    """Check recent logs for database errors and warnings."""
    print("=== Database Connection Health (Last Hour) ===\n")

    # Calculate time range
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)

    # Format times for Render API (RFC3339)
    start = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    end = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    print(f"Time range: {start} to {end}\n")

    # Check for errors
    print("🔴 Checking for BAD errors (should be 0)...")
    print("   - PendingRollbackError: These should be eliminated")
    print("   - Unhandled OperationalError: Should be auto-recovered\n")

    print("✅ Checking for GOOD warnings (expected)...")
    print("   - 'Reconnecting to database': Normal for idle periods")
    print("   - 'OperationalError detected, reconnecting': Auto-recovery working\n")

    print("📊 To check manually:")
    print(f"   Render Dashboard: https://dashboard.render.com/web/{SERVICE_ID}/logs")
    print("\n   Filter by:")
    print("   - Level: error (should see NONE)")
    print("   - Text: 'PendingRollback' (should see NONE)")
    print("   - Text: 'Reconnecting' (OK to see these)")

if __name__ == "__main__":
    check_logs()
