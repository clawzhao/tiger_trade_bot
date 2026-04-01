#!/usr/bin/env python3
"""Database migration helper for Tiger Trade Bot.

Usage:
    python -m script.db upgrade      # Apply all migrations
    python -m script.db downgrade    # Roll back all migrations
    python -m script.db revision "msg"  # Create a new migration (autogenerate)
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic.config import Config
from alembic import command

def get_alembic_config() -> Config:
    """Get Alembic config object."""
    project_root = Path(__file__).parent.parent
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    # Ensure we use the same DATABASE_URL from config
    from config import DATABASE_URL
    alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
    return alembic_cfg

def upgrade() -> None:
    """Upgrade to latest migration."""
    cfg = get_alembic_config()
    command.upgrade(cfg, "head")

def downgrade() -> None:
    """Downgrade to base (initial state)."""
    cfg = get_alembic_config()
    command.downgrade(cfg, "base")

def revision(message: str) -> None:
    """Create a new migration with autogenerate."""
    cfg = get_alembic_config()
    command.revision(cfg, message=message, autogenerate=True)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m script.db [upgrade|downgrade|revision <msg>]")
        sys.exit(1)

    action = sys.argv[1]
    if action == "upgrade":
        upgrade()
    elif action == "downgrade":
        downgrade()
    elif action == "revision":
        if len(sys.argv) < 3:
            print("Usage: python -m script.db revision <message>")
            sys.exit(1)
        revision(sys.argv[2])
    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
