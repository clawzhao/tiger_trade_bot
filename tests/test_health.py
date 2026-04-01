"""
Tests for health check endpoints.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import asyncio

from tiger_trade_bot.health import start_health_server_in_thread, get_health_service
from tiger_trade_bot.trader import PaperTrader
from tiger_trade_bot.data import TigerDataFetcher


@pytest.fixture
def mock_trader():
    trader = MagicMock(spec=PaperTrader)
    trader.is_connected.return_value = True
    trader.get_account_summary.return_value = {
        "net_liquidation": 100000.0,
        "cash_balance": 50000.0,
        "daily_pnl": 123.45,
    }
    trader.get_positions.return_value = {"AAPL": MagicMock(quantity=100)}
    trader.get_active_orders.return_value = []
    return trader


@pytest.fixture
def mock_data_fetcher():
    return MagicMock(spec=TigerDataFetcher)


def test_health_live_endpoint(mock_trader, mock_data_fetcher):
    """Test /health/live returns alive status."""
    from tiger_trade_bot.health import HealthService

    service = HealthService()
    service.set_components(mock_trader, mock_data_fetcher)
    app = service.create_app()

    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    json = response.json()
    assert json["status"] == "alive"
    assert "timestamp" in json


def test_health_ready_when_connected(mock_trader, mock_data_fetcher):
    """Test /health/ready returns 200 when trader is connected."""
    from tiger_trade_bot.health import HealthService

    service = HealthService()
    service.set_components(mock_trader, mock_data_fetcher)
    app = service.create_app()

    client = TestClient(app)
    response = client.get("/health/ready")
    assert response.status_code == 200
    json = response.json()
    assert json["status"] == "ready"


def test_health_ready_when_not_connected(mock_trader, mock_data_fetcher):
    """Test /health/ready returns 503 when trader is not connected."""
    from tiger_trade_bot.health import HealthService

    mock_trader.is_connected.return_value = False
    service = HealthService()
    service.set_components(mock_trader, mock_data_fetcher)
    app = service.create_app()

    client = TestClient(app)
    response = client.get("/health/ready")
    assert response.status_code == 503
    json = response.json()
    assert json["status"] == "not_ready"
    assert json["reason"] == "trader_not_connected"


def test_health_detail_endpoint(mock_trader, mock_data_fetcher):
    """Test /health/detail returns full status."""
    from tiger_trade_bot.health import HealthService

    service = HealthService()
    service.set_components(mock_trader, mock_data_fetcher)
    app = service.create_app()

    client = TestClient(app)
    response = client.get("/health/detail")
    assert response.status_code == 200
    json = response.json()
    assert "status" in json
    assert "timestamp" in json
    assert "uptime_seconds" in json
    assert "account" in json
    assert "positions" in json
    assert "orders" in json


def test_health_detail_when_disconnected(mock_trader, mock_data_fetcher):
    """Test /health/detail shows trader disconnected."""
    from tiger_trade_bot.health import HealthService

    mock_trader.is_connected.return_value = False
    service = HealthService()
    service.set_components(mock_trader, mock_data_fetcher)
    app = service.create_app()

    client = TestClient(app)
    response = client.get("/health/detail")
    assert response.status_code == 200
    json = response.json()
    assert json["status"] == "degraded" or json.get("trader") == "disconnected"


def test_health_service_singleton():
    """Test get_health_service returns singleton."""
    service1 = get_health_service()
    service2 = get_health_service()
    assert service1 is service2
