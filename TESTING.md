# Local Testing Guide - GroupMe Integration & Money Tracking

## Setup

### 1. Ensure You're on the `groupme` Branch
```bash
git checkout groupme
git pull origin groupme
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Local Environment

Create a `.env` file in the project root with test values:
```bash
# Required
DATAGOLF_API_KEY=your_test_key_here  # Use your actual key
SECRET_KEY=test-secret-key-change-in-production

# Optional - only needed for GroupMe member verification
# Leave these blank to skip verification during testing
GROUPME_BOT_ID=
GROUPME_ACCESS_TOKEN=
GROUPME_GROUP_ID=
```

### 4. Start the Application
```bash
python app.py
```

Navigate to http://localhost:8000

---

## Test Scenarios

### A. Registration & GroupMe Name

**Test 1: Register without GroupMe name** (should work)
1. Go to `/register` with valid invite code
2. Fill form, leave "GroupMe Name" blank
3. Click "Create Account"
4. ✅ Should succeed

**Test 2: Register with GroupMe name** (verification skipped if env vars not set)
1. Go to `/register` with valid invite code
2. Fill form, enter any GroupMe name
3. Click "Create Account"
4. ✅ Should succeed (verification only runs if GROUPME_ACCESS_TOKEN & GROUPME_GROUP_ID are set)

---

### B. Tournament Pricing

**Test 3: Set tournament pricing**
1. Log in as admin
2. Go to Admin Dashboard → Tournaments table
3. Click "Pricing" button on any tournament
4. Enter Single Entry Price: `50`
5. Enter 3-Entry Package: `120`
6. Click "Save Pricing"
7. ✅ Should see green success message: "Pricing updated"
8. Page should refresh showing updated pricing

**Test 4: Validate negative pricing** (should fail)
1. From pricing page, try to enter: `-50`
2. Click "Save Pricing"
3. ✅ Should see error: "Entry price must be positive"

**Test 5: Clear pricing**
1. From pricing page, change price to: `0`
2. Click "Save Pricing"
3. ✅ Price should show as "Not set" in purse summary

**Test 6: Purse calculation display**
1. Set tournament pricing to `$50`
2. Create 3 picks for that tournament
3. Go to leaderboard
4. ✅ Should see `💰 Purse: $150` in header (3 entries × $50)

---

### C. GroupMe Settings (Admin Panel)

**Test 7: View GroupMe settings**
1. Log in as admin
2. Go to Admin Dashboard
3. Scroll to "GroupMe Settings" card
4. ✅ Should show:
   - "Not configured" or masked bot_id
   - Form to enter bot ID
   - Test button only shows if bot_id is set

**Test 8: Save bot ID**
1. In GroupMe Settings, enter any test bot ID: `test_bot_123`
2. Click "Save Bot ID"
3. ✅ Should see green success: "GroupMe bot ID saved"
4. Page reloads, should show masked ID: `test_...123`

**Test 9: Test message (without real GroupMe)**
1. Set a test bot ID first (Test 8)
2. Click "Send Test Message"
3. ✅ Should see error: "Failed to send test message" (expected without real bot)
4. Check logs - should show: `ERROR Failed to send GroupMe message`

---

### D. Pick Notifications (GroupMe Messages)

**Test 10: Create pick and verify notification attempt**
1. Ensure at least one tournament is active
2. Go to `/picks`
3. Create a new entry with picks
4. Click "Save Entry"
5. ✅ Should:
   - Save successfully
   - Not crash (even if GroupMe disabled)
   - Check application logs - should see: `ERROR Failed to send pick notification` if bot_id not set (expected)

**Test 11: Update pick and verify notification attempt**
1. From picks summary, click "Edit" on an entry
2. Change a golfer selection
3. Click "Save Entry"
4. ✅ Should:
   - Update successfully
   - Check logs for notification attempt

**Test 12: With a real bot ID (optional - skip if no real bot)**
1. If you have a real GroupMe bot, set GROUPME_BOT_ID in `.env`
2. Restart app
3. Create/update a pick
4. ✅ Check your GroupMe group - should see message like:
   ```
   🏌️ YourName created Entry 1 for Tournament Name
   Tier 1: Golfer Name
   Tier 2: Golfer Name
   Tier 3: Golfer Name
   Tier 4: Golfer Name
   💰 Total Purse: $150
   ```

---

### E. Leaderboard Features

**Test 13: Manual send to GroupMe (button)**
1. Go to leaderboard
2. ✅ Admin users should see "Send to GroupMe" button
3. Non-admin users should NOT see it
4. Click button
5. ✅ Should redirect, check logs for attempt

**Test 14: Final leaderboard auto-send (optional - requires tournament completion)**
1. This requires tournament status to change to 'completed'
2. Normally triggered by `POST /admin/update-statuses` when round >= 5
3. ✅ Check logs for: `Sent final leaderboard for {tournament}` or error

---

## Logging Output to Watch

When testing, tail the application logs:

```bash
# Terminal 1: Start app
python app.py

# Terminal 2: Watch for GroupMe activity
tail -f <logfile>  # Or check console output
```

Look for these log messages:

**Success logs:**
- `GroupMe message sent: 🏌️ ...`
- `GroupMe member verified: {name}`
- `Test GroupMe message sent successfully`
- `Sent final leaderboard for {tournament}`

**Expected error logs (when bot not configured):**
- `GroupMe bot_id not configured, skipping message send`
- `Failed to send GroupMe message`
- `GroupMe member not found` (if verification enabled and name wrong)

---

## Edge Cases to Test

**Test 15: Missing fields**
- Register without username → should fail
- Try pricing without entering numbers → field validation should prevent
- Try bot ID save without entering anything → should fail with "Bot ID cannot be empty"

**Test 16: Database consistency**
- Create tournament, set pricing
- Create picks
- Edit tournament pricing
- ✅ Verify leaderboard still shows correct purse

**Test 17: User feedback messages**
- After successful save → green message appears
- After error → red message appears
- Messages disappear on navigation → check URL params

---

## Testing Checklist

- [ ] Registration works with/without GroupMe name
- [ ] Pricing validation rejects negative numbers
- [ ] Purse displays correctly on leaderboard
- [ ] Admin settings UI shows/hides correctly
- [ ] Bot ID can be saved and masked
- [ ] Pick creation/updates don't crash (even without bot)
- [ ] Success/error messages display
- [ ] Non-admin users can't access admin features
- [ ] All forms preserve user input on validation failures

---

## Troubleshooting

**Issue: "ModuleNotFoundError: No module named 'fasthtml'"**
```bash
pip install -r requirements.txt
```

**Issue: GroupMe requests timing out**
- GroupMeClient has 10s timeout - verify GroupMe API is accessible
- Check internet connection

**Issue: Database errors (new fields not found)**
- SQLite auto-creates tables on startup
- If upgrading existing DB, new fields should be added automatically
- If issues persist, delete `data/golf_pickem.db` and restart

**Issue: Logging not showing GroupMe messages**
- Check that logging is configured in your app
- GroupMe errors are caught and logged, not re-raised

---

## When Ready to Merge

Once all tests pass:

```bash
git checkout main
git merge groupme --no-ff -m "Merge: GroupMe integration and money tracking"
git push origin main
```

Then update deployment:
1. Set any GroupMe env vars in production
2. Restart application
3. Monitor logs for any issues
