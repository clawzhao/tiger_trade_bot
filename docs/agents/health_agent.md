---
name: Health Agent
description: Provides health check endpoints for the Tiger Trade Bot using FastAPI.
usage: |
  The health agent runs in a background thread and serves three endpoints:
  - `/health/live`: returns 200 if process is alive
  - `/health/ready`: returns 200 if Tiger API connected; else 503
  - `/health/detail`: detailed status (account, positions, orders, uptime)
examples:
  - curl http://localhost:8080/health/live
  - curl http://localhost:8080/health/ready
  - curl http://localhost:8080/health/detail
reference: tiger_trade_bot/health.py
---