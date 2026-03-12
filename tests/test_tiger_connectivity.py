"""
End-to-End connectivity test for Tiger Open API.

This script verifies:
- Your RSA private key is valid
- Your Tiger ID is recognized
- Your account can be accessed

Usage:
    python tests/test_tiger_connectivity.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.trade.trade_client import TradeClient
from config import TIGER_ID, ACCOUNT_ID, PRIVATE_KEY_PATH, SANDBOX_MODE


def test_tiger_connection():
    """Test basic connectivity to Tiger Open API."""
    print("🔍 Testing Tiger Open API connection...")
    print(f"   Tiger ID: {TIGER_ID}")
    print(f"   Account: {ACCOUNT_ID}")
    print(f"   Sandbox: {SANDBOX_MODE}")
    print(f"   Key Path: {PRIVATE_KEY_PATH}")

    # Validate config
    if TIGER_ID == "YOUR_TIGER_ID" or ACCOUNT_ID == "YOUR_PAPER_ACCOUNT_ID":
        print("\n❌ ERROR: Please update config.py with your actual credentials.")
        print("   Or create config_local.py with real values.")
        return False

    if not os.path.exists(PRIVATE_KEY_PATH):
        print(f"\n❌ ERROR: Private key not found at {PRIVATE_KEY_PATH}")
        print("   Please place your rsa_private_key.pem in the keys/ directory.")
        return False

    # 1. Load Config
    client_config = TigerOpenClientConfig(sandbox_debug=SANDBOX_MODE)
    try:
        client_config.private_key = read_private_key(PRIVATE_KEY_PATH)
    except Exception as e:
        print(f"\n❌ ERROR: Failed to read private key: {e}")
        return False

    client_config.tiger_id = TIGER_ID
    client_config.account = ACCOUNT_ID

    # 2. Initialize Trade Client
    try:
        trade_client = TradeClient(client_config)
    except Exception as e:
        print(f"\n❌ ERROR: Failed to initialize TradeClient: {e}")
        return False

    # 3. Test connectivity by fetching managed accounts
    try:
        accounts = trade_client.get_managed_accounts()
        print("\n✅ TIGER API CONNECTION SUCCESSFUL")
        print(f"💰 Managed Accounts: {accounts}")
        return True
    except Exception as e:
        print(f"\n❌ CONNECTION FAILED: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Verify your Tiger ID and Account ID are correct")
        print("   - Ensure your IP is whitelisted in Tiger Developer Console")
        print("   - Check that the private key matches the one generated")
        print("   - If using sandbox mode, ensure paper trading account exists")
        return False


if __name__ == "__main__":
    success = test_tiger_connection()
    sys.exit(0 if success else 1)