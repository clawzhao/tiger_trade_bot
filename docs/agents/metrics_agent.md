---
name: Metrics Agent
description: Exposes Prometheus metrics on an HTTP endpoint for monitoring.
usage: |
  The metrics agent starts an HTTP server on `METRICS_PORT` (default 9090) and serves
  metrics in Prometheus text format at `/metrics`. It tracks:
  - `tiger_trade_bot_orders_total` (counter): order count by side and status
  - `tiger_trade_bot_portfolio_value` (gauge): net liquidation value
  - `tiger_trade_bot_agent_latency_seconds` (histogram): operation latencies
  - `tiger_trade_bot_risk_utilization` (gauge): per-symbol position risk (0-1)
examples:
  - curl http://localhost:9090/metrics
reference: tiger_trade_bot/metrics.py
---