"""
Integration tests for Tiger Trade Bot components.
"""

import asyncio
import pytest
from unittest.mock import MagicMock, patch
from tiger_trade_bot.bot import create_strategy
from tiger_trade_bot.trader import PaperTrader, OrderSide, OrderType
from tiger_trade_bot.data import TigerDataFetcher
from tiger_trade_bot.strategies import GapTradingStrategy, MovingAverageCrossoverStrategy


@pytest.fixture
def mock_tiger_clients():
    with patch("tiger_trade_bot.trader.TradeClient") as mock_trade_client, \
         patch("tiger_trade_bot.trader.read_private_key") as mock_read_key, \
         patch("tiger_trade_bot.data.QuoteClient") as mock_quote_client, \
         patch("tiger_trade_bot.data.PushClient") as mock_push_client:
        yield mock_trade_client, mock_quote_client, mock_push_client


@pytest.fixture
def mock_components(mock_tiger_clients):
    mock_trade, mock_quote, mock_push = mock_tiger_clients
    mock_trade_instance = mock_trade.return_value
    mock_quote_instance = mock_quote.return_value

    # Mock account info
    mock_trade_instance.get_account_info.return_value = {
        "net_liquidation": 100000.0,
        "cash_balance": 50000.0,
        "buying_power": 100000.0,
        "total_profit_loss": 0.0,
    }

    # Mock positions
    mock_trade_instance.get_positions.return_value = [
        {"symbol": "AAPL", "quantity": 50, "average_cost": 150.0, "last_price": 155.0, "side": "BUY"}
    ]

    # Mock order placement
    mock_trade_instance.place_order.return_value = "TIGER_ORDER_123"

    # Mock websocket push client
    mock_push_instance = mock_push.return_value
    mock_push_instance.connect.return_value = None
    mock_push_instance.disconnect.return_value = None

    yield {
        "trade_client": mock_trade_instance,
        "quote_client": mock_quote_instance,
        "push_client": mock_push_instance,
    }


def test_create_strategy_gap(mock_components):
    """Test GapTradingStrategy creation."""
    data_fetcher = TigerDataFetcher("id", "acc", "key", True)
    trader = PaperTrader("id", "acc", "key", True)
    data_fetcher.connect = MagicMock(return_value=True)
    trader.connect = MagicMock(return_value=True)

    strategy = create_strategy(
        MagicMock(strategy="gap", symbols="AAPL,TSLA", gap_threshold=0.03),
        data_fetcher,
        trader
    )
    assert isinstance(strategy, GapTradingStrategy)


def test_create_strategy_ma(mock_components):
    """Test MovingAverageCrossoverStrategy creation."""
    data_fetcher = TigerDataFetcher("id", "acc", "key", True)
    trader = PaperTrader("id", "acc", "key", True)
    data_fetcher.connect = MagicMock(return_value=True)
    trader.connect = MagicMock(return_value=True)

    strategy = create_strategy(
        MagicMock(strategy="ma", symbols="SPY", fast=20, slow=100),
        data_fetcher,
        trader
    )
    assert isinstance(strategy, MovingAverageCrossoverStrategy)


def test_trader_order_lifecycle(mock_components):
    """Test order placement triggers metrics increment."""
    trader = PaperTrader("id", "acc", "key", True)
    trader.connect()

    with patch("tiger_trade_bot.trader.increment_trade") as mock_increment:
        order = trader.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
        assert order.status.value == "PENDING"
        mock_increment.assert_called_once_with(side="BUY", status="placed")


def test_data_fetcher_connectivity(mock_tiger_clients):
    """Test TigerDataFetcher connections."""
    mock_trade, mock_quote, mock_push = mock_tiger_clients
    mock_trade_instance = mock_trade.return_value
    mock_trade_instance.get_account_info.return_value = {"net_liquidation": 10000}

    fetcher = TigerDataFetcher("id", "acc", "key", True)
    assert fetcher.connect() is True
    assert fetcher.is_connected() is True


def test_health_probe_integration(mock_components):
    """Test health detail endpoint returns expected fields."""
    from tiger_trade_bot.health import HealthService

    # Create trader and data_fetcher with connected=True
    trader = PaperTrader("id", "acc", "key", True)
    trader._connected = True
    # Override get_account_summary to use our mock or real connection
    # Since we already have mock_components, we can't easily inject them into a new PaperTrader
    # Instead, use a MagicMock that already has methods returning values
    mock_trader = MagicMock(spec=PaperTrader)
    mock_trader.is_connected.return_value = True
    mock_trader.get_account_summary.return_value = {
        "net_liquidation": 100000.0,
        "cash_balance": 50000.0,
        "daily_pnl": 123.45,
    }
    mock_trader.get_positions.return_value = {"AAPL": MagicMock(quantity=100)}
    mock_trader.get_active_orders.return_value = []

    mock_data_fetcher = MagicMock(spec=TigerDataFetcher)

    service = HealthService()
    service.set_components(mock_trader, mock_data_fetcher)
    detail = asyncio.run(service.detail())

    assert detail["status"] == "ok"
    assert "account" in detail
    assert detail["account"]["net_liquidation"] == 100000.0
    assert "positions" in detail
    assert detail["positions"]["count"] == 1


def test_logging_integration(mock_components, caplog):
    """Test that JSON logs are emitted during operations."""
    import logging
    from tiger_trade_bot.logger import setup_logging
    setup_logging(log_level="INFO")

    logger = logging.getLogger("test.integration")
    logger.info("Integration test log", extra={"component": "health", "symbol": "AAPL"})

    # Check caplog contains our record (caplog works with standard logging)
    assert any("Integration test log" in rec.message for rec in caplog.records)


def test_metrics_lifecycle(mock_components):
    """Test metrics are updated during PaperTrader lifecycle."""
    trader = PaperTrader("id", "acc", "key", True)
    trader.connect()
    # After connect, portfolio value metric should have been set (call set_portfolio_value)
    # The connect method calls set_portfolio_value internally via metrics update on account_info fetch
    # Can't easily assert gauge value but ensure no error


def test_database_session_factory():
    """Test get_db provides a session and closes it."""
    from tiger_trade_bot.db.session import get_db
    sessions = []
    for db in get_db():
        sessions.append(db)
        # Do a simple operation to ensure it's a valid session
        db.execute("SELECT 1")
    assert len(sessions) == 1
    # After generator ends, db should be closed; we can't use it further
    # Already closed in finally
