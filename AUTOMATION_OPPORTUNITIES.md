# Golf Pick'em Automation Opportunities

This document outlines potential automations to reduce manual admin work for tournament management.

## Current State

**Manual Admin Tasks Required:**
1. Initial tournament data sync from DataGolf
2. Tournament activation (upcoming → active)
3. Tournament field population and tier assignment
4. Picks locking at tournament start
5. Live score synchronization during tournament
6. Tournament completion (active → completed)

**Current Automatic Features:**
- Leaderboard auto-sync (10-minute intervals on page load)

---

## Automation Opportunity 1: Automatic Tournament Activation

**Current:** Manual click "Set Active" or "Update Statuses"

**Proposed Rule:**
- Run daily at 6 AM
- Activate any tournament with status = 'upcoming' if current date >= Tuesday of tournament week
- Change status: 'upcoming' → 'active'

**Questions to Consider:**
- Is Tuesday the right trigger day?
- What time should this run (6 AM or different)?
- Any other conditions before activating?

**Priority:** HIGH - Eliminates weekly manual step

---

## Automation Opportunity 2: Automatic Picks Locking

**Current:** Manual click "Lock" or "Update Statuses"

**Proposed Rule:**
- Run hourly (or more frequently?)
- Lock picks for any tournament with status = 'active' AND picks_locked = False if current date >= tournament start_date
- Prevents picks after tournament starts

**Questions to Consider:**
- Lock exactly at start_date or earlier (e.g., 1 hour before)?
- How often should we check? Hourly? Every 15 minutes?
- Any grace period for late picks?

**Priority:** HIGH - Critical for fairness

---

## Automation Opportunity 3: Automatic Tournament Completion

**Current:** Manual click "Mark Complete" or "Update Statuses"

**Proposed Rule:**
- Run every 2 hours on Sunday/Monday
- Check DataGolf API for current round
- Complete tournament if round >= 5 (tournament over)
- Auto-send final leaderboard to GroupMe

**Questions to Consider:**
- Is every 2 hours the right frequency?
- Only check Sunday/Monday or every day?
- Fallback if DataGolf API is down (e.g., auto-complete Monday evening)?

**Priority:** HIGH - Timely results for users

---

## Automation Opportunity 4: Automatic Field Assignment

**Current:** Manual navigate to field page and click "Auto-Assign Tiers from DataGolf"

**Proposed Rule:**
- Trigger when tournament becomes active
- Fetch field from DataGolf
- Create missing golfers
- Auto-assign tiers by DG skill:
  - Tier 1: Top 6
  - Tier 2: Next 18 (7-24)
  - Tier 3: Next 36 (25-60)
  - Tier 4: Remaining

**Challenges:**
- DataGolf field may not be available until closer to tournament start
- May need to run multiple times as field updates with WDs/adds

**Questions to Consider:**
- Happen automatically when tournament activates?
- Or scheduled job Wednesday/Thursday?
- What if field isn't available yet - keep trying or notify admin?

**Priority:** MEDIUM - Timing challenges make this tricky

---

## Automation Opportunity 5: Increased Auto-Sync Frequency

**Current:** Leaderboard auto-syncs every 10 minutes when someone views page

**Proposed Rule:**
- Background job runs every 5 minutes
- Only syncs tournaments with status = 'active'
- Independent of page loads

**Concerns:**
- More frequent DataGolf API calls (may hit rate limits)
- Is 5 minutes worth it vs 10 minutes?

**Questions to Consider:**
- Is current 10-minute sync sufficient?
- If more frequent, should it be 5 minutes or something else?
- Should frequency vary by round (e.g., more frequent on Sunday)?

**Priority:** MEDIUM - Nice to have, but API rate limits are a concern

---

## Automation Opportunity 6: Automatic Pricing Setup

**Current:** Manual set entry_price and three_entry_price per tournament

**Proposed Rule:**
- Store default pricing in app settings
- Auto-populate when tournament is created
- Can override per tournament if needed

**Questions to Consider:**
- Does pricing stay consistent across tournaments?
- Worth automating or prefer manual control?

**Priority:** LOW - Simple manual task

---

## Automation Opportunity 7: Scheduled Admin Reports

**Current:** None

**Proposed Feature:**
- Daily email/Slack/GroupMe message with:
  - Upcoming tournaments this week
  - Active tournaments needing attention
  - Pick counts per tournament
  - Completed tournaments

**Questions to Consider:**
- Is this useful or just noise?
- What info in a daily report?
- Email, Slack, GroupMe, or skip entirely?

**Priority:** LOW - Optional visibility feature

---

## Technical Implementation Options

### Option 1: APScheduler (Recommended)
**Best for:** Current scale, simple setup

**Pros:**
- Easy to add to existing FastHTML app
- No external dependencies
- Runs in-process

**Cons:**
- Lost if app crashes (no job persistence)
- Single instance only

**Example:**
```python
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(activate_tournaments, 'cron', hour=6)
scheduler.add_job(lock_picks, 'cron', minute=0)
scheduler.add_job(complete_tournaments, 'cron', hour='*/2', day_of_week='sun,mon')
scheduler.start()
```

### Option 2: Celery
**Best for:** Larger scale, distributed tasks

**Requires:** Redis/RabbitMQ, separate worker process

**Pros:**
- Job persistence across restarts
- Distributed workers
- Retry logic

**Cons:**
- More complex setup
- Additional infrastructure
- Overkill for current scale

### Option 3: Render Cron Jobs
**Best for:** Serverless scheduled tasks

**Pros:**
- No code changes to main app
- Render handles scheduling

**Cons:**
- Limited to cron syntax
- Cold starts
- Separate deployments

---

## Next Steps

1. Review these automation opportunities
2. Prioritize which ones you want
3. Decide on specific rules/timing for each
4. Choose implementation approach (APScheduler recommended)
5. Implement in priority order
6. Test in development with mock DataGolf responses
7. Deploy to production with conservative scheduling
8. Monitor logs and adjust as needed

---

## Notes

- See `/Users/zachshirah/.claude/plans/unified-strolling-backus.md` for detailed technical documentation
- All automations should handle DataGolf API failures gracefully
- Consider admin alerting for repeated job failures
- Test job timing in development before deploying
