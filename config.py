"""Application configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "golf_pickem.db"

# Database - Uses fastsql with SQLAlchemy connection strings
# Local development: SQLite (no DATABASE_URL set)
# Production: PostgreSQL via Supabase/Render (set DATABASE_URL env var)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH}")

# DataGolf API
DATAGOLF_API_KEY = os.getenv("DATAGOLF_API_KEY", "")

# GroupMe Integration
GROUPME_BOT_ID = os.getenv("GROUPME_BOT_ID", "")
GROUPME_ACCESS_TOKEN = os.getenv("GROUPME_ACCESS_TOKEN", "")  # For API verification
GROUPME_GROUP_ID = os.getenv("GROUPME_GROUP_ID", "")  # Group to verify membership

# App settings
APP_NAME = "Golf Pick'em"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
SESSION_DAYS = 30
