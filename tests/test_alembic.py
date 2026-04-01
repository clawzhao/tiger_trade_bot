"""
Alembic migration sanity checks.
"""

import importlib.util
import os
from pathlib import Path

def test_alembic_versions_exist():
    """Ensure at least one migration script exists."""
    versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
    assert versions_dir.exists(), "alembic/versions directory should exist"
    files = list(versions_dir.glob("*.py"))
    assert len(files) > 0, "No migration files found in alembic/versions"

def test_alembic_config_importable():
    """Ensure alembic.ini can be read by Config (basic check)."""
    from alembic.config import Config
    # We'll try loading the config file path but not use it; just ensure no error on import
    project_root = Path(__file__).parent.parent
    ini_path = project_root / "alembic.ini"
    assert ini_path.exists(), "alembic.ini should exist"
    # The following would work if alembic is installed; but we may not have it during test? Actually requirements include alembic.
    # So we can actually create Config object
    cfg = Config(str(ini_path))
    assert cfg.get_main_option("script_location") == "alembic"
