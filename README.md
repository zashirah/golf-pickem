# Golf Pick'em

A web application for running a golf pick'em pool where users select golfers across different tiers and compete for the best combined score. Features live scoring integration with DataGolf API and automated GroupMe notifications.

## Features

- 🏌️ **Tournament Management** - Create and manage golf tournaments with customizable entry pricing
- 🎯 **Tiered Pick System** - Four-tier golfer selection system for balanced competition
- 📊 **Live Leaderboards** - Real-time scoring with automatic sync from DataGolf API
- 💰 **Automated Payouts** - Track purse, calculate payouts based on entry counts
- 📱 **GroupMe Integration** - Automatic notifications for picks, leaderboards, and tournament updates
- 👥 **User Management** - Invite-only registration with GroupMe name verification
- 📈 **Best 2 of 4 Scoring** - Top 2 golfers count toward final score with DQ handling
- 🔐 **Admin Dashboard** - Complete tournament, field, and user management interface

## Tech Stack

- **Backend**: Python with [FastHTML](https://fastht.ml/) framework
- **Database**: PostgreSQL (production) / SQLite (local development)
- **APIs**: 
  - DataGolf API for live tournament data and scoring
  - GroupMe API for bot messaging and member verification
- **Deployment**: Render.com with automatic deployments
- **Styling**: Custom CSS with mobile-responsive design

## Prerequisites

- Python 3.11+
- PostgreSQL (for production) or SQLite (for local development)
- DataGolf API key
- GroupMe bot credentials (optional for notifications)

## Environment Variables

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:port/database  # Production (Supabase/Render)
# DATABASE_URL will use SQLite locally if not set

# Session Security
SESSION_SECRET=your-secret-key-here

# DataGolf API
DATAGOLF_API_KEY=your-datagolf-api-key

# GroupMe Integration (optional)
GROUPME_BOT_ID=your-bot-id
GROUPME_ACCESS_TOKEN=your-access-token
GROUPME_GROUP_ID=your-group-id

# Invite Code (set a secure code for user registration)
INVITE_CODE=your-invite-code
```

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd golf-pickem
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the app**
   - Open http://localhost:8000
   - Register with the invite code
   - First user becomes admin automatically

## Project Structure

```
golf-pickem/
├── app.py                  # Main application entry point
├── config.py              # Environment configuration
├── requirements.txt       # Python dependencies
├── render.yaml           # Render deployment config
│
├── db/
│   ├── __init__.py       # Database initialization
│   └── models.py         # Data models (User, Tournament, Pick, etc.)
│
├── routes/
│   ├── __init__.py       # Route registration
│   ├── admin.py          # Admin dashboard & management
│   ├── auth.py           # Login/registration
│   ├── home.py           # Home page & about
│   ├── leaderboard.py    # Leaderboard & scoring
│   ├── picks.py          # Pick management
│   └── utils.py          # Shared utilities
│
├── services/
│   ├── auth.py           # Authentication service
│   ├── datagolf.py       # DataGolf API client
│   ├── groupme.py        # GroupMe API client
│   └── scoring.py        # Scoring calculation logic
│
├── components/
│   └── layout.py         # Reusable UI components
│
├── static/
│   └── style.css         # Application styles
│
└── migrations/           # Database migrations
    └── 001_add_groupme_and_pricing_fields.postgresql.sql
```

## Database Setup

The application automatically creates tables on first run. For production with PostgreSQL, you may need to run migrations:

```bash
# For local SQLite - automatic
python app.py

# For PostgreSQL - run migrations if needed
# See migrations/ directory for SQL scripts
```

### Key Tables

- **users** - User accounts with GroupMe integration
- **tournaments** - Golf tournament details and settings
- **golfers** - Golfer master list from DataGolf
- **tournament_field** - Golfers assigned to tournament tiers
- **picks** - User picks (supports multiple entries)
- **tournament_results** - Live scoring data from DataGolf
- **pickem_standings** - Calculated standings per entry
- **app_settings** - Application configuration (e.g., GroupMe bot ID)

## Admin Features

Access the admin dashboard at `/admin` (requires admin privileges):

- **Tournament Management**: Create tournaments, set pricing, lock picks
- **Field Management**: Import golfers from DataGolf, assign tiers
- **User Management**: View users, delete accounts, manage admins
- **Scoring Control**: Manual sync, complete tournaments
- **GroupMe Settings**: Configure bot ID, send leaderboard messages
- **Invite Code**: Generate and manage registration invites

## Scoring System

- Users pick 4 golfers (one from each tier)
- **Best 2 of 4** scores count toward final total
- Lower scores are better (strokes to par)
- Missed cut/DQ = +10 penalty
- Ties split prize money
- Auto-sync every 10+ minutes during active tournaments

## GroupMe Integration

The app can automatically post to GroupMe:

1. **Set up a GroupMe bot** in your group
2. Configure bot ID in admin settings or environment variables
3. Notifications are sent for:
   - New picks submitted
   - Pick updates/deletions
   - Leaderboard updates (manual trigger)
   - Tournament completion

Bot ID in database (`app_settings` table) takes priority over environment variable.

## Development

### Running Locally

```bash
# Activate virtual environment
source venv/bin/activate

# Run with auto-reload
python app.py
```

The app will:
- Use SQLite database at `data/golf_pickem.db`
- Run on http://localhost:8000
- Auto-reload on file changes

### Adding Features

1. Create/modify routes in `routes/`
2. Add models to `db/models.py`
3. Update services in `services/`
4. Style with `static/style.css`
5. Test locally before deploying

## Deployment

The app is configured for Render.com deployment via `render.yaml`:

1. **Connect GitHub repository** to Render
2. **Set environment variables** in Render dashboard
3. **Deploy** - automatic from main branch

### Production Checklist

- [ ] Set secure `SESSION_SECRET`
- [ ] Configure PostgreSQL database URL
- [ ] Add DataGolf API key
- [ ] Set up GroupMe bot (optional)
- [ ] Set strong invite code
- [ ] Test registration flow
- [ ] Verify live scoring sync

## API Integrations

### DataGolf API

Used for:
- Tournament schedules and details
- Live scoring and leaderboard data
- Golfer statistics and rankings

Rate limiting: Automatic sync throttled to 10+ minute intervals

### GroupMe API

Used for:
- Bot messaging to group
- Member verification during registration

Optional but recommended for full feature set.

## Troubleshooting

**Tables don't scroll on mobile**
- Clear browser cache, CSS was recently updated

**GroupMe messages not sending**
- Check bot ID in admin settings
- Verify bot is added to GroupMe group
- Check app logs for errors

**Scoring not updating**
- Verify DataGolf API key is valid
- Check tournament name matches DataGolf exactly
- Manual sync available in admin dashboard

**Registration not working**
- Verify invite code matches environment variable
- Check GroupMe verification settings if enabled

## Contributing

This is a private project, but contributions are welcome:

1. Create a feature branch
2. Make changes with clear commit messages
3. Test thoroughly locally
4. Submit pull request

## License

Private project - All rights reserved

## Support

For issues or questions, contact the project maintainer.
