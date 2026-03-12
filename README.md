# 🐯📈 tiger_trade_bot

A lightweight, direct-connection trading bot for **Tiger Brokers** using the Tiger Open Platform API. Optimized for high performance and low memory footprint on **Raspberry Pi 4**.

## 🚀 AI-Powered Development

Built with **OpenCode Superpowers** to ensure logic accuracy and automated testing.

### Superpower Skills Applied:
- **/superpowers:brainstorm** - Defined risk-managed position sizing for SG/US markets.
- **/superpowers:write-plan** - Mapped out the asynchronous websocket handler for real-time price action.
- **/superpowers:execute-plan** - Generated the `tigeropen` SDK boilerplate and E2E test scripts.

## 🛠 Prerequisites

### 1. Developer Credentials

You must obtain your credentials from the [Tiger Open Platform Console](https://developer.itigerup.com/):
- **Tiger ID:** Your unique developer identifier.
- **Account ID:** Your Paper Trading account number (a 17-digit string).
- **Private Key:** Generate an RSA key pair on the console. Save the **PKCS#1** private key as `keys/rsa_private_key.pem`.

### 2. Environment Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/tiger_trade_bot.git
cd tiger_trade_bot

# Install Tiger Open API SDK
pip install tigeropen pandas
```

## 🧪 End-to-End (E2E) Test

Tiger connects directly via REST/Websockets. Use this script to verify your tiger_id and RSA key.

**File:** `tests/test_tiger_connectivity.py`

```python
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.trade.trade_client import TradeClient

def test_tiger_connection():
    # 1. Load Config
    client_config = TigerOpenClientConfig(sandbox_debug=True)  # Set to True for Paper Trading
    client_config.private_key = read_private_key('./keys/rsa_private_key.pem')
    client_config.tiger_id = 'YOUR_TIGER_ID'
    client_config.account = 'YOUR_PAPER_ACCOUNT_ID'

    # 2. Initialize Trade Client
    trade_client = TradeClient(client_config)

    # 3. Fetch Managed Accounts (Test Connectivity)
    try:
        accounts = trade_client.get_managed_accounts()
        print("✅ TIGER API CONNECTION SUCCESSFUL")
        print(f"💰 Managed Accounts: {accounts}")
    except Exception as e:
        print(f"❌ CONNECTION FAILED: {e}")

if __name__ == "__main__":
    test_tiger_connection()
```

## 📂 Project Structure

```
tiger_trade_bot/
├── keys/                  # Secure storage for your rsa_private_key.pem (Added to .gitignore)
├── strategy/              # AI-optimized strategies (e.g., Gap Trading, Mean Reversion)
├── logs/                  # Daily execution logs for audit trails
├── config.py              # Centralized configuration for Tiger ID and Account IDs
├── tests/
│   └── test_tiger_connectivity.py
└── README.md
```

## ⚠️ Safety Protocols

- **Sandbox Mode:** The bot is initialized with `sandbox_debug=True` to ensure all trades stay in the Paper Trading environment.
- **Resource Efficiency:** No local gateway is needed, making this ideal for the 4GB/8GB Raspberry Pi 4.
- **IP Whitelisting:** Remember to add your Pi's public IP or GCP VM IP to the Tiger Developer Console whitelist.

---

### How to get your Tiger Credentials:

1. **Login:** Go to [developer.itigerup.com](https://developer.itigerup.com/).
2. **Registration:** Complete the "Developer Registration" (requires a funded Tiger account).
3. **RSA Key:** Click **"Generate Key"**.
   - **Crucial:** Copy the **Private Key** immediately and save it as a `.pem` file. Tiger does *not* store this for you; if you lose it, you have to regenerate it.
4. **IP Whitelist:** Tiger is strict. You **must** add your current IP address (from your Pi or GCP) to their "White List" section on that same page, or the API will reject your connection.

---

*Developed using OpenCode Superpowers Framework.*