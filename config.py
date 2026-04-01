"""
Centralized configuration for Tiger Trade Bot.

⚠️  SECURITY: Never commit real credentials.
Use environment variables (.env) or local override config.
"""

import os
import sys
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Tiger Broker API Credentials
TIGER_ID = os.environ.get("TIGER_ID", "YOUR_TIGER_ID")  # From Tiger Developer Console
ACCOUNT_ID = os.environ.get(
    "ACCOUNT_ID", "YOUR_PAPER_ACCOUNT_ID"
)  # 17-digit paper trading account
PRIVATE_KEY_PATH = os.environ.get("PRIVATE_KEY_PATH", "./keys/rsa_private_key.pem")

# Trading Environment
SANDBOX_MODE = os.environ.get("SANDBOX_MODE", "True").lower() in ("true", "1", "yes")

# Market Settings
DEFAULT_MARKET = os.environ.get("DEFAULT_MARKET", "US")  # "US" or "SG" or "HK"
DEFAULT_TZ = os.environ.get("DEFAULT_TZ", "America/New_York")

# Risk Parameters
MAX_POSITION_SIZE = float(
    os.environ.get("MAX_POSITION_SIZE", "10000")
)  # USD per position
DAILY_LOSS_LIMIT = float(
    os.environ.get("DAILY_LOSS_LIMIT", "500")
)  # Stop trading if daily loss exceeds this
MAX_ORDER_RETRIES = int(os.environ.get("MAX_ORDER_RETRIES", "3"))

# Logging
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_DIR = os.environ.get("LOG_DIR", "./logs")

# WebSocket
WS_ENABLED = os.environ.get("WS_ENABLED", "True").lower() in ("true", "1", "yes")
WS_RECONNECT_INTERVAL = int(os.environ.get("WS_RECONNECT_INTERVAL", "5"))  # seconds

# Optional: Override with local config (not tracked in git)
try:
    from config_local import *
except ImportError:
    pass


# Web Server (Health & Metrics)
HEALTH_PORT = int(os.environ.get("HEALTH_PORT", "8080"))
METRICS_PORT = int(os.environ.get("METRICS_PORT", "9090"))

# Database
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./trades.db")


# .env Validation
def validate_config():
    missing = []
    if TIGER_ID == "YOUR_TIGER_ID" or not TIGER_ID:
        missing.append("TIGER_ID")
    if ACCOUNT_ID == "YOUR_PAPER_ACCOUNT_ID" or not ACCOUNT_ID:
        missing.append("ACCOUNT_ID")

    if missing:
        print(
            f"❌ Missing required configuration in .env: {', '.join(missing)}",
            file=sys.stderr,
        )
        print(
            "Please create a .env file with these variables or export them in your environment.",
            file=sys.stderr,
        )
        sys.exit(1)
