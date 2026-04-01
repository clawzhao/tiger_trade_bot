# 🐯📈 Tiger Trade Bot - Setup Guide

Complete step-by-step instructions to obtain credentials and run the bot.

---

## 1. Register as a Tiger Developer

1. Go to: https://developer.itigerup.com/
2. Click **Sign Up** or **Register**
3. Fill in your details (email, password, phone number for verification)
4. Complete any identity verification steps (may require a funded Tiger account)
5. Once approved, log in to the Developer Console

---

## 2. Get Your Tiger ID

- In the Developer Console, look for **Developer Information** or **API Credentials**
- Your **Tiger ID** is a unique string (often alphanumeric) assigned to your developer account
- Example format: `TIGER_XXXXXXX` or a numeric string
- Copy it — you'll put this in `config_local.py` as `TIGER_ID`

---

## 3. Create a Paper Trading Account

1. In the Developer Console, navigate to **Account Management** or **Paper Trading**
2. Click **Create Paper Account** (if you don't have one)
3. You'll get a **17-digit Account ID** (e.g., `12345678901234567`)
4. Copy it — this goes in `config_local.py` as `ACCOUNT_ID`

> **Note:** This is a simulated trading account with virtual money. No real funds involved.

---

## 4. Generate RSA Key Pair

Tiger uses RSA signatures for API authentication.

1. In the Developer Console, find **API Key Management** or **Security Settings**
2. Click **Generate Key** or **Create RSA Key**
3. The console will display:
   - **Public Key** (you can ignore)
   - **Private Key** (crucial — copy it immediately)
4. **Copy the entire private key** (it's a long string starting with `-----BEGIN RSA PRIVATE KEY-----` and ending with `-----END RSA PRIVATE KEY-----`)
5. In your bot directory:
   ```bash
   cd tiger_trade_bot
   mkdir -p keys
   ```
6. Create the file `keys/rsa_private_key.pem` and paste the private key inside
   ```bash
   # Using a text editor, or:
   cat > keys/rsa_private_key.pem << 'EOF'
   -----BEGIN RSA PRIVATE KEY-----
   ...your key content here...
   -----END RSA PRIVATE KEY-----
   EOF
   ```
7. Set proper permissions (optional):
   ```bash
   chmod 600 keys/rsa_private_key.pem
   ```

> ⚠️ **Important:** Tiger does NOT store your private key. If you lose it, you must regenerate a new key pair and update any applications using it. Keep it secret — treat it like a password.

---

## 5. Whitelist Your IP Address

Tiger API only accepts requests from whitelisted IPs.

1. In the Developer Console, go to **IP Whitelist** or **Security Settings**
2. Click **Add IP** or **Add to Whitelist**
3. Enter your current public IP address:
   - If you're running on a home network, your public IP may be dynamic. Consider using a dynamic DNS service or updating the whitelist when it changes.
   - If running on a cloud VM (GCP, AWS, etc.), use that static IP.
4. Save the whitelist

> **Tip:** Find your public IP by visiting https://api.ipify.org or running:
> ```bash
> curl https://api.ipify.org
> ```

---

## 6. Configure the Bot

1. Copy the example local config:
   ```bash
   cp config_local.py.example config_local.py
   ```
2. Edit `config_local.py` with your actual values:
   ```python
   TIGER_ID = "your_tiger_id_here"
   ACCOUNT_ID = "12345678901234567"
   PRIVATE_KEY_PATH = "./keys/rsa_private_key.pem"
   ```
3. (Optional) Override other settings like `SANDBOX_MODE = True` (keep it `True` for paper trading)

---

## 7. Install Dependencies

```bash
cd tiger_trade_bot
pip install -r requirements.txt
```

Or with a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 8. Test Connectivity

Run the E2E test:

```bash
./run_test.sh
```

Expected output if successful:
```
✅ TIGER API CONNECTION SUCCESSFUL
💰 Managed Accounts: ['12345678901234567']
```

---

## 9. Run the Bot

Once the test passes, start paper trading:

```bash
./run_bot.sh --strategy gap --symbols AAPL,TSLA
```

Or use the MA crossover strategy:
```bash
./run_bot.sh --strategy ma --symbols SPY --fast 10 --slow 50
```

Logs will appear in `logs/bot_YYYY-MM-DD.log` and on the console.

---

## 10. Database & Feature Store (Optional)

The bot can persist trade history, predictions, and model metrics using SQLAlchemy with Alembic migrations.

### Initialize Database

For local development, the default SQLite database is created automatically on first run. To explicitly initialize and apply migrations:

```bash
python -m script.db upgrade
```

This creates `trades.db` with tables:
- `trades`: filled order records
- `predictions`: strategy predictions and features
- `model_versions`: ML model metadata

### Configuration

Set `DATABASE_URL` environment variable (default: `sqlite:///./trades.db`). For production, use PostgreSQL:

```bash
export DATABASE_URL=postgresql://user:pass@localhost/tiger_bot
```

### Creating New Migrations

After modifying models in `tiger_trade_bot/db/models.py`, generate a migration:

```bash
python -m script.db revision "describe your schema change"
```

Review the generated file in `alembic/versions/` before applying.

Apply:
```bash
python -m script.db upgrade
```

Rollback:
```bash
python -m script.db downgrade
```

### Schema Details

See `tiger_trade_bot/db/models.py` for table definitions and relationships.

---

## 11. Common Issues & Troubleshooting

| Issue | Likely Cause | Fix |
|-------|--------------|-----|
| `CONNECTION FAILED: Invalid credentials` | Wrong Tiger ID or Account ID | Double-check both values in `config_local.py` |
| `Private key not found` | Key file missing or wrong path | Ensure `keys/rsa_private_key.pem` exists and `PRIVATE_KEY_PATH` points to it |
| `IP not whitelisted` | Your IP not in Tiger console | Add your public IP to whitelist; wait a few minutes for propagation |
| `SSL/Certificate error` | Outdated CA certificates | Update system: `sudo apt-get update && sudo apt-get install ca-certificates` |
| `ModuleNotFoundError: No module named 'tigeropen'` | Dependencies not installed | Run `pip install -r requirements.txt` |
| `Order rejected` | Insufficient buying power or invalid symbol | Paper account has virtual cash; verify symbol is tradable in your region |

---

## 11. Next Steps After Success

- Customize strategy parameters in `config.py` or via CLI
- Add more symbols (ensure they're supported in your market)
- Monitor logs and positions
- Implement your own strategies in `strategy/` directory

---

**Need help?** Check the logs in `logs/` for detailed error messages.