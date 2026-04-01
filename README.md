# 🐯📈 Tiger Trade Bot

A lightweight, direct-connection trading bot for **Tiger Brokers** using the Tiger Open Platform API. Optimized for high performance and low memory footprint on **Raspberry Pi 4**.

## ✨ Features (Phase 8: Observability & Polish)

- **Prometheus Metrics**: trade count, portfolio value, agent latency, risk utilization on `/metrics` (port 9090)
- **Structured JSON Logging**: Machine-readable logs with consistent fields for ELK/Loki
- **Health Checks**: Three-level probes (`/health/live`, `/health/ready`, `/health/detail`)
- **Kubernetes Ready**: Manifests for Deployment, Service, HPA, Ingress, and PVC
- **Database & Migrations**: SQLAlchemy models with Alembic for feature store schema
- **Performance Tests**: Latency benchmarks for core operations

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

# Install dependencies
pip install -r requirements.txt

# Optional: Install development dependencies for performance tests
pip install pytest pytest-mock

# Optional: Initialize database (SQLite local)
python -m script.db upgrade
```

### 3. Configuration

Copy `.env.example` to `.env` (or set environment variables):
```bash
cp .env.example .env
# Edit .env with your Tiger credentials
```

Key environment variables:
- `TIGER_ID`, `ACCOUNT_ID`, `PRIVATE_KEY_PATH`
- `SANDBOX_MODE=True` (paper trading) / `False` (live)
- `HEALTH_PORT=8080`, `METRICS_PORT=9090`
- `DATABASE_URL=sqlite:///./trades.db`
- `LOG_LEVEL=INFO`, `LOG_DIR=./logs`

## 🏥 Health Check Endpoints

The bot starts a FastAPI health server (port `HEALTH_PORT`, default 8080):

- `GET /health/live` — Returns 200 if process is alive (no dependencies checked)
- `GET /health/ready` — Returns 200 if Tiger API is connected; 503 otherwise
- `GET /health/detail` — Detailed JSON with account summary, positions, and active orders

Example:
```bash
curl http://localhost:8080/health/detail
```

## 📊 Prometheus Metrics

Metrics server runs on `METRICS_PORT` (default 9090) at `/metrics`.

Exported metrics:
- `tiger_trade_bot_orders_total` — Counter (labels: side, status)
- `tiger_trade_bot_portfolio_value` — Gauge (USD)
- `tiger_trade_bot_agent_latency_seconds` — Histogram (labels: operation)
- `tiger_trade_bot_risk_utilization` — Gauge per symbol (0-1 ratio)

Scrape example:
```bash
curl http://localhost:9090/metrics
```

## 🗄 Database Migrations (Alembic)

The bot uses SQLAlchemy with Alembic for schema migrations.

- Models: `tiger_trade_bot/db/models.py` (trades, predictions, model_versions)
- Alembic config: `alembic.ini`
- Migration scripts: `alembic/versions/`
- Helper CLI: `python -m script.db [upgrade|downgrade|revision <msg>]`

Upgrade to latest:
```bash
python -m script.db upgrade
```

Create a new migration (after code changes):
```bash
python -m script.db revision "add new feature column"
```

## ⚙️ Running the Bot

```bash
# Basic run
python -m tiger_trade_bot --strategy gap --symbols AAPL,TSLA

# With custom parameters
python -m tiger_trade_bot --strategy ma --symbols AAPL --fast 10 --slow 50 --sandbox
```

Flags:
- `--strategy`: `gap` or `ma`
- `--symbols`: comma-separated tickers
- `--no-websocket`: disable streaming
- `--tiger-id`, `--account-id`, `--key-path`: override config

The bot will:
1. Start health server (port 8080)
2. Start metrics server (port 9090)
3. Connect to Tiger API
4. Initialize selected strategy
5. Enter main loop: every 60s print account/positions and update metrics

Press `Ctrl+C` to stop; open orders are cancelled gracefully.

## 📂 Project Structure

```
tiger_trade_bot/
├── keys/                  # Secure storage for rsa_private_key.pem (gitignored)
├── logs/                  # Daily JSON logs
├── strategy/              # Trading strategies: Gap, Moving Average
├── tests/
│   ├── performance/      # Latency benchmarks
│   ├── test_tiger_connectivity.py
│   ├── test_trader.py
│   └── test_data.py
├── tiger_trade_bot/
│   ├── bot.py             # Main entry point
│   ├── config.py          # Configuration & env vars
│   ├── data.py            # TigerDataFetcher (REST + WebSocket)
│   ├── trader.py          # PaperTrader with order lifecycle
│   ├── strategies.py      # Strategy implementations
│   ├── logger.py          # JSON logging setup
│   ├── metrics.py         # Prometheus metrics instrumentation
│   ├── health.py          # FastAPI health checks
│   └── db/
│       ├── __init__.py
│       └── models.py      # SQLAlchemy models
├── k8s/                   # Kubernetes manifests (deployment, service, hpa, ingress, pvc, configmap, secret)
├── alembic/               # Alembic migrations environment
│   ├── env.py
│   └── versions/
│       └── 001_initial_feature_store.py
├── script/
│   └── db.py              # DB migration CLI helper
├── requirements.txt
├── .env.example
├── README.md
└── SETUP_GUIDE.md
```

## 🐳 Kubernetes Deployment

See [k8s/README.md](k8s/README.md) for detailed steps.

Quick start:

```bash
# 1. Build and push your image
docker build -t clawzhao/tiger_trade_bot:latest .
docker push clawzhao/tiger_trade_bot:latest

# 2. Create secret with your credentials
kubectl create secret generic tiger-trade-bot-secret \
  --from-literal=tiger-id='YOUR_TIGER_ID' \
  --from-literal=account-id='YOUR_ACCOUNT_ID' \
  --from-file=rsa-private-key=./keys/rsa_private_key.pem

# 3. Apply manifests
kubectl apply -f k8s/

# 4. Verify
kubectl get pods,svc,ingress,hpa -l app=tiger-trade-bot
```

## 🧪 Testing

```bash
# Unit tests
pytest tests/

# With coverage
pytest --cov=tiger_trade_bot tests/

# Performance benchmarks
pytest -m performance tests/performance/test_latency.py -v

# Standalone performance test
python tests/performance/test_latency.py
```

## ⚠️ Safety Protocols

- **Sandbox Mode:** Default to `sandbox_debug=True` for paper trading. Set `SANDBOX_MODE=False` only for live trading (caution!).
- **IP Whitelisting:** Add your Pi's/public IP to the Tiger Developer Console whitelist; otherwise API calls will be rejected.
- **Resource Efficiency:** Designed to run on Raspberry Pi 4 (4GB). Limit memory to ~512Mi in k8s.
- **Secure Key Handling:** Private key stored outside repo (`keys/`) and referenced via `PRIVATE_KEY_PATH`. Add to `.gitignore`.
- **Order Validation:** Max position size and daily loss limit configured via config; prevents runaway orders.

## 📝 License

MIT

---

*Developed using OpenCode Superpowers Framework.*