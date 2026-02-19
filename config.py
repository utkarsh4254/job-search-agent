"""
config.py — Configuration (Free Stack)
All secrets come from environment variables — never hardcoded.
"""
import os

GROQ_API_KEY        = os.environ.get("GROQ_API_KEY",   "")
GEMINI_API_KEY      = os.environ.get("GEMINI_API_KEY", "")
ADZUNA_APP_ID       = os.environ.get("ADZUNA_APP_ID",  "YOUR_ADZUNA_APP_ID")
ADZUNA_APP_KEY      = os.environ.get("ADZUNA_APP_KEY", "YOUR_ADZUNA_APP_KEY")
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "YOUR_GOOGLE_MAPS_API_KEY")

DEFAULT_KEYWORDS         = os.environ.get("SEARCH_KEYWORDS", "software engineer")
DEFAULT_LOCATION         = os.environ.get("SEARCH_LOCATION", "")
DEFAULT_INDUSTRY         = os.environ.get("SEARCH_INDUSTRY", "tech startup")
MONITOR_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", "30"))

COMPANIES_TO_WATCH = []
