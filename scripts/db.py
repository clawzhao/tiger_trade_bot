#!/usr/bin/env python3
"""
Database migration and management CLI.

Usage:
    python scripts/db.py upgrade head
    python scripts/db.py downgrade -1
    python scripts/db.py revision "Initial schema"
    python scripts/db.py history
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic.config import Config
from alembic import command

def get_alembic_config() -> Config:
    config = Config(str(Path(__file__).parent.parent / "alembic.ini")
    return config

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/db.py <command> [args]")
        sys.exit(1)

    cmd = sys.argv[1]
    config = get_alembic_config()

    if cmd == "upgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        command.upgrade(config, revision)
    elif cmd == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        command.downgrade(config, revision)
    elif cmd == "revision":
        message = sys.argv[2] if len(sys.argv) > 2 else None
        command.revision(config, message=message, autogenerate=True)
    elif cmd == "history":
        command.history(config)
    elif cmd == "current":
        command.current(config)
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == "__main__":
    main()
