from __future__ import annotations
from pathlib import Path

def get_data_dir() -> Path:
    """
    Return a writable data directory for caches/settings.
    On macOS, prefer ~/Library/Application Support/bcfeed.
    Otherwise, fall back to a hidden folder in the user's home.
    """
    home = Path.home()
    app_support = home / "Library" / "Application Support" / "bcfeed"
    if app_support.parent.exists():  # likely macOS
        base = app_support
    else:
        base = home / ".bcfeed"
    base.mkdir(parents=True, exist_ok=True)
    return base

DATA_DIR = get_data_dir()
GMAIL_CREDENTIALS_FILE = "credentials.json"
GMAIL_TOKEN_FILE = "token.pickle"
VIEWED_PATH = DATA_DIR / "viewed_state.json"
STARRED_PATH = DATA_DIR / "starred_state.json"
RELEASE_CACHE_PATH = DATA_DIR / "release_cache.json"
EMPTY_DATES_PATH = DATA_DIR / "no_results_dates.json"
SCRAPE_STATUS_PATH = DATA_DIR / "scrape_status.json"
EMBED_CACHE_PATH = DATA_DIR / "embed_cache.json"
TOKEN_PATH = DATA_DIR / GMAIL_TOKEN_FILE
CREDENTIALS_PATH = DATA_DIR / GMAIL_CREDENTIALS_FILE
DASHBOARD_PATH = Path(__file__).resolve().with_name("dashboard.html")
DASHBOARD_CSS_PATH = Path(__file__).resolve().with_name("dashboard.css")
DASHBOARD_JS_PATH = Path(__file__).resolve().with_name("dashboard.js")
README_PATH = Path(__file__).resolve().with_name("README.md")
SETUP_PATH = Path(__file__).resolve().with_name("SETUP.md")
GMAIL_SETUP_PATH = Path(__file__).resolve().with_name("GMAIL_SETUP.md")
