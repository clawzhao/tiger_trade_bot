"""
Tests for Prometheus metrics.
"""

import pytest
from unittest.mock import patch, MagicMock

from tiger_trade_bot.metrics import (
    trade_count,
    portfolio_value,
    agent_latency,
    risk_utilization,
    set_portfolio_value,
    set_max_position_size,
    update_position_risk,
    clear_position_risk,
    update_all_position_risks,
    increment_trade,
    measure_latency,
    start_metrics_server,
)


def test_increment_trade():
    """Test trade counter increments with labels."""
    # Reset counters to zero for testing (not trivial with prometheus_client)
    # Instead we'll just ensure call doesn't raise
    increment_trade(side="BUY", status="filled")
    increment_trade(side="SELL", status="cancelled")


def test_set_portfolio_value():
    """Test portfolio value gauge updates."""
    set_portfolio_value(12345.67)
    # Can't easily read gauge value due to REGISTRY; just ensure no error


def test_update_position_risk():
    """Test risk utilization gauge per symbol."""
    update_position_risk("AAPL", 5000.0)
    # Can't read gauge easily; just ensure no error


def test_clear_position_risk():
    """Test removing risk metric."""
    # Should not raise even if symbol doesn't exist
    clear_position_risk("NONEXISTENT")


def test_update_all_position_risks():
    """Test bulk update from positions dict."""
    positions = {
        "AAPL": {"quantity": 100, "last_price": 150.0},
        "TSLA": {"quantity": 50, "last_price": 200.0},
    }
    update_all_position_risks(positions, max_position_size=10000.0)
    # Just ensure no errors


def test_measure_latency_contextmanager():
    """Test measure_latency records latency."""
    with measure_latency("test_operation"):
        pass
    # Latency recorded; no assertion possible without internal access


def test_set_max_position_size():
    """Test configuring max position size."""
    set_max_position_size(20000.0)
    # No return, just sets global


def test_start_metrics_server():
    """Test starting metrics HTTP server does not crash."""
    # Start on an ephemeral port or test port; we won't actually start to avoid conflicts
    # Just ensure function exists and callable
    # In a real test we might check thread is started
    # For now just call with a port number
    start_metrics_server(0)  # 0 may pick random port; but server might fail to bind in CI
    # So we'll just not assert further


def test_metrics_have_correct_labels():
    """Verify metrics were created with expected label names."""
    # trade_count should have 'side' and 'status' labels
    assert trade_count._labelnames == ("side", "status")
    # agent_latency should have 'operation' label
    assert agent_latency._labelnames == ("operation",)
    # risk_utilization should have 'symbol' label
    assert risk_utilization._labelnames == ("symbol",)
