---
name: Logger Agent
description: Structured JSON logging configuration with rotation.
usage: |
  The logger agent configures the root logger to output JSON lines to both console and rotating file.
  - Formatter: JsonFormatter with timestamp, level, logger, module, function, line, and extra fields.
  - Rotation: 10 MB per file, keep 5 backups.
  - Log directory: `LOG_DIR` (default `./logs`).
examples:
  - All logs: `logs/bot_2025-06-17.log`
  - Console: each line is JSON with fields like `level`, `message`, `symbol` (when provided)
reference: tiger_trade_bot/logger.py
---