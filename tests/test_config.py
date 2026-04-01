"""
Tests for configuration loading.
"""

import importlib
import os
from unittest.mock import patch


def test_default_config_values():
    """Test that default config values are set when env vars not provided."""
    import config as config_mod
    # These defaults are from config.py when env not set
    # Note: TIGER_ID and ACCOUNT_ID default to placeholder strings; they are required
    assert config_mod.TIGER_ID == "YOUR_TIGER_ID" or config_mod.TIGER_ID is None
    assert config_mod.ACCOUNT_ID == "YOUR_PAPER_ACCOUNT_ID" or config_mod.ACCOUNT_ID is None
    assert config_mod.PRIVATE_KEY_PATH == "./keys/rsa_private_key.pem"
    assert config_mod.SANDBOX_MODE is True
    assert config_mod.LOG_LEVEL == "INFO"
    assert config_mod.LOG_DIR == "./logs"
    assert config_mod.HEALTH_PORT == 8080
    assert config_mod.METRICS_PORT == 9090
    assert config_mod.DATABASE_URL == "sqlite:///./trades.db"
    assert config_mod.MAX_POSITION_SIZE == 10000.0
    assert config_mod.DAILY_LOSS_LIMIT == 500.0


def test_env_override(monkeypatch):
    """Test that environment variables override defaults."""
    monkeypatch.setenv("TIGER_ID", "TEST_TIGER_123")
    monkeypatch.setenv("ACCOUNT_ID", "12345678901234567")
    monkeypatch.setenv("PRIVATE_KEY_PATH", "/custom/path/key.pem")
    monkeypatch.setenv("SANDBOX_MODE", "False")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("HEALTH_PORT", "5000")
    monkeypatch.setenv("METRICS_PORT", "5001")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    monkeypatch.setenv("MAX_POSITION_SIZE", "20000")
    monkeypatch.setenv("DAILY_LOSS_LIMIT", "1000")

    # Reload config module to pick up new env vars
    import config as config_mod
    importlib.reload(config_mod)

    assert config_mod.TIGER_ID == "TEST_TIGER_123"
    assert config_mod.ACCOUNT_ID == "12345678901234567"
    assert config_mod.PRIVATE_KEY_PATH == "/custom/path/key.pem"
    assert config_mod.SANDBOX_MODE is False
    assert config_mod.LOG_LEVEL == "DEBUG"
    assert config_mod.HEALTH_PORT == 5000
    assert config_mod.METRICS_PORT == 5001
    assert config_mod.DATABASE_URL == "postgresql://user:pass@localhost/db"
    assert config_mod.MAX_POSITION_SIZE == 20000.0
    assert config_mod.DAILY_LOSS_LIMIT == 1000.0
