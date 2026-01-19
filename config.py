"""Application configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent
DATABASE_PATH = BASE_DIR / "data" / "golf_pickem.db"

# DataGolf API
DATAGOLF_API_KEY = os.getenv("DATAGOLF_API_KEY", "")

# App settings
APP_NAME = "Golf Pick'em"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
SESSION_DAYS = 30
