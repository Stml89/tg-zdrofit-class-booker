"""Configuration module for the Zdrofit bot."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set in .env file")

# API settings
ZDROFIT_API_BASE_URL = "https://zdrofit.perfectgym.pl"

# Database settings
BASE_DIR = Path(__file__).parent.parent
PROJECT_ROOT = BASE_DIR
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "data" / "zdrofit.db"))

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.getenv("LOG_DIR", str(BASE_DIR / "logs"))

# Search window (hours from now)
SEARCH_WINDOW_HOURS = int(os.getenv("SEARCH_WINDOW_HOURS", "48"))

# Available clubs mapping: club_name -> club_id
AVAILABLE_CLUBS = {
    "Zdrofit Bemowo Dywizjonu 303": 7,
    "Zdrofit Lazurowa": 75
}

# Telegram connection pool settings
TELEGRAM_CONNECT_TIMEOUT = int(os.getenv("TELEGRAM_CONNECT_TIMEOUT", "15"))
TELEGRAM_READ_TIMEOUT = int(os.getenv("TELEGRAM_READ_TIMEOUT", "15"))
TELEGRAM_WRITE_TIMEOUT = int(os.getenv("TELEGRAM_WRITE_TIMEOUT", "15"))
TELEGRAM_POOL_TIMEOUT = int(os.getenv("TELEGRAM_POOL_TIMEOUT", "30"))
TELEGRAM_POOL_SIZE = int(os.getenv("TELEGRAM_POOL_SIZE", "32"))
