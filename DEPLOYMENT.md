# Golf Pick'em - Deployment Guide

## Local Development

### Prerequisites
- Python 3.11+
- Docker & Docker Compose (for containerized testing)

### Setup

1. **Clone the repository and install dependencies:**
   ```bash
   git clone https://github.com/zashirah/golf-pickem.git
   cd golf-pickem
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your DATAGOLF_API_KEY and SECRET_KEY
   ```

3. **Run the development server:**
   ```bash
   python app.py
   ```
   App will be available at http://localhost:8000

## Docker Development

### Build and Run Locally

```bash
# Using docker-compose (recommended for development)
docker-compose up

# Or build and run manually
docker build -t golf-pickem .
docker run -p 8000:8000 \
  -e DATAGOLF_API_KEY=your_key_here \
  -e SECRET_KEY=your_secret \
  -v $(pwd)/data:/app/data \
  golf-pickem
```

App will be available at http://localhost:8000

## Production Deployment with Supabase

Supabase provides a free PostgreSQL database, solving the persistent storage problem. **Note:** The current MVP build still runs on SQLite. PostgreSQL/Supabase support must be implemented before treating this as production-ready. Until then, Render deploys will have non-persistent data.

### Setup Supabase

1. **Create a new project:**
   - Go to [supabase.com](https://supabase.com)
   - Sign in with your account
   - Click "New Project"
   - Choose a project name (e.g., `golf-pickem`)
   - Set a database password (save this!)
   - Choose a region close to you
   - Click "Create new project" (takes ~2 minutes)

2. **Get your database URL:**
   - In Supabase dashboard, go to Settings → Database
   - Copy the "Connection string" (URI format)
   - Should look like: `postgresql://postgres:[PASSWORD]@db.[REGION].supabase.co:5432/postgres`
   - Update `PASSWORD` in the URL to match your database password

3. **Update your .env (local testing with Supabase):**
   ```bash
   DATABASE_URL=postgresql://postgres:your_password@db.region.supabase.co:5432/postgres
   DATAGOLF_API_KEY=your_key
   SECRET_KEY=your_secret
   ```

4. **Test locally with Supabase:**
   ```bash
   python app.py
   ```
   The app will create all tables in your Supabase database automatically.

### Deploy to Render with Supabase

1. **Push your code to GitHub:**
   ```bash
   git add .
   git commit -m "Deploy: add Supabase PostgreSQL support"
   git push origin refactor
   ```

2. **Merge to main:**
   ```bash
   git checkout main
   git merge refactor
   git push origin main
   ```

3. **Deploy to Render (SQLite for now):**
   - Go to [render.com](https://render.com)
   - Create a new account if needed, connect your GitHub
   - Click "New Web Service"
   - Select your golf-pickem repository
   - Choose the `main` branch
   - Configure settings:
     - Name: `golf-pickem`
     - Runtime: Python 3
     - Build Command: `pip install -r requirements.txt`
      - Start Command: `python app.py` (Render sets `PORT`; app now binds to `0.0.0.0` automatically)
    - Add environment variables:
       - `DATAGOLF_API_KEY`: Your DataGolf API key
       - `SECRET_KEY`: Generate with `openssl rand -hex 32`
       - `DATABASE_URL`: (planned) Supabase connection string — **not yet used by the app; pending Postgres support**
   - Click "Create Web Service"

4. **Verify deployment:**
   - Render will show build progress
   - Once deployed, your app is live at `https://golf-pickem.render.app`
   - Check Render logs if there are issues

### Why Supabase?

- ✅ **Free tier**: Generous free PostgreSQL database
- ✅ **Persistent storage**: Data survives app redeploys
- ✅ **Scalable**: Easy to upgrade if needed
- ✅ **Easy backups**: Supabase handles automatic backups
- ✅ **Real-time capabilities**: Future feature option
- ✅ **Works with Render/Railway/Heroku**: Any platform

---

## Alternative: Other Platforms

### Option: Railway.app (with PostgreSQL)

1. **Initialize Railway:**
   ```bash
   npm i -g @railway/cli
   railway login
   railway init
   ```

2. **Add PostgreSQL:**
   ```bash
   railway add --postgres
   ```

3. **Deploy:**
   ```bash
   railway up
   ```

Railway automatically sets `DATABASE_URL` for PostgreSQL. Just add `DATAGOLF_API_KEY` and `SECRET_KEY`.

### Option: Self-hosted (VPS like DigitalOcean, AWS EC2, Linode)

1. **SSH into your server:**
   ```bash
   ssh root@your_server_ip
   ```

2. **Install PostgreSQL:**
   ```bash
   apt-get update
   apt-get install -y postgresql postgresql-contrib python3.11 python3-pip git
   ```

3. **Create database:**
   ```bash
   sudo -u postgres createdb golf_pickem
   sudo -u postgres createuser golf_user
   # Set password for golf_user
   ```

4. **Clone and setup app:**
   ```bash
   git clone https://github.com/zashirah/golf-pickem.git
   cd golf-pickem
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

5. **Set environment:**
   ```bash
   export DATABASE_URL="postgresql://golf_user:password@localhost:5432/golf_pickem"
   export DATAGOLF_API_KEY="your_key"
   export SECRET_KEY="your_secret"
   ```

6. **Use systemd for auto-restart:**
   ```bash
   sudo nano /etc/systemd/system/golf-pickem.service
   ```

---

## Monitoring & Logging

**Render logs:**
```bash
render logs -s golf-pickem
```

**Railway logs:**
```bash
railway logs
```

**Supabase logs:**
- View in Supabase dashboard under "Database" → "Logs"

The app uses Python's `logging` module for debug output.

---

## Database Setup Details

The app automatically creates all necessary tables on first run:
- `users` - User accounts
- `sessions` - Active sessions
- `tournaments` - Tournament definitions
- `golfers` - Golfer data
- `tournament_field` - Field entries (golfer + tier for tournament)
- `picks` - User picks for tournament
- `tournament_results` - Live scores from DataGolf
- `pickem_standings` - Calculated scores and leaderboard

No manual database setup needed - just set `DATABASE_URL` and run!

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | No (dev) | PostgreSQL connection string. If not set, uses SQLite. |
| `DATAGOLF_API_KEY` | Yes | Your DataGolf API key from datagolf.com |
| `SECRET_KEY` | Yes | Random secret for session encryption. Generate with `openssl rand -hex 32` |

---

## Quick Start Checklist

- [ ] Create Supabase account and project
- [ ] Get PostgreSQL connection string from Supabase
- [ ] Test locally: `DATABASE_URL=... python app.py`
- [ ] Push code to GitHub
- [ ] Deploy to Render with environment variables
- [ ] Test at production URL
- [ ] Share link with users!

---

For questions or issues, check:
- [FastHTML docs](https://fasthtml.docs.answer.ai)
- [Supabase docs](https://supabase.com/docs)
- [Render docs](https://render.com/docs)

