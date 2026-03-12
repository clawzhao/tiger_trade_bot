"""
Centralized configuration for Tiger Trade Bot.

⚠️  SECURITY: Never commit real credentials.
Use environment variables or local override config.
"""

# Tiger Broker API Credentials
TIGER_ID = "YOUR_TIGER_ID"              # From Tiger Developer Console
ACCOUNT_ID = "YOUR_PAPER_ACCOUNT_ID"    # 17-digit paper trading account
PRIVATE_KEY_PATH = "./keys/rsa_private_key.pem"

# Trading Environment
SANDBOX_MODE = True  # True = Paper Trading, False = Live Trading

# Market Settings
DEFAULT_MARKET = "US"  # "US" or "SG" or "HK"
DEFAULT_TZ = "America/New_York"

# Risk Parameters
MAX_POSITION_SIZE = 10000  # USD per position
DAILY_LOSS_LIMIT = 500     # Stop trading if daily loss exceeds this
MAX_ORDER_RETRIES = 3

# Logging
LOG_LEVEL = "INFO"
LOG_DIR = "./logs"

# WebSocket
WS_ENABLED = True
WS_RECONNECT_INTERVAL = 5  # seconds

# Optional: Override with local config (not tracked in git)
try:
    from config_local import *
except ImportError:
    pass