#!/bin/bash
# Quick database health check for Render logs

echo "=== Database Connection Health Check ==="
echo ""

# Check for BAD errors (shouldn't see these anymore)
echo "🔴 PendingRollbackError (BAD - should be 0):"
gh api repos/zashirah/golf-pickem/actions/runs --jq '.workflow_runs[0].created_at' 2>/dev/null || echo "  (install gh CLI for more features)"

echo ""
echo "Use Render dashboard to check logs for:"
echo "  ❌ PendingRollbackError - should be GONE"
echo "  ❌ OperationalError exceptions - should be GONE"
echo "  ✅ 'Reconnecting to database' warnings - EXPECTED and OK"
echo ""
echo "Dashboard: https://dashboard.render.com/web/srv-d5n7ouogjchc7396kkag/logs"
