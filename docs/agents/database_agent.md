---
name: Database Agent
description: SQLAlchemy ORM models and Alembic migrations for feature store and trade history.
usage: |
  The database agent provides:
  - Models: `Trade`, `Prediction`, `ModelVersion`
  - Engine and session factory: `tiger_trade_bot.db.session`
  - Alembic migration tooling in `alembic/`
  - CLI helper: `python -m script.db upgrade|downgrade|revision <msg>`
examples:
  - Initialize DB: `python -m script.db upgrade`
  - Create migration: `python -m script.db revision "add column"`
reference: tiger_trade_bot/db/, alembic/, script/db.py
---