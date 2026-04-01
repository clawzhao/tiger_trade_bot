import pytest
from unittest.mock import MagicMock, patch
from tiger_trade_bot.trader import PaperTrader, OrderSide, OrderType, OrderStatus


@pytest.fixture
def mock_trade_client():
    with (
        patch("tiger_trade_bot.trader.TradeClient") as mock_trade_client,
        patch("tiger_trade_bot.trader.read_private_key") as mock_read_key,
    ):
        yield mock_trade_client


def test_connect_success(mock_trade_client):
    mock_instance = mock_trade_client.return_value
    mock_instance.get_account_info.return_value = {"net_liquidation": 100000.0}

    trader = PaperTrader("ID", "ACC", "key", True)
    assert trader.connect() is True
    assert trader.is_connected() is True
    assert trader._initial_balance == 100000.0


def test_place_order_success(mock_trade_client):
    mock_instance = mock_trade_client.return_value
    mock_instance.get_account_info.return_value = {"net_liquidation": 100000.0}
    mock_instance.place_order.return_value = "TIGER_123"

    trader = PaperTrader()
    trader.connect()

    with patch("tiger_trade_bot.trader.increment_trade") as mock_increment:
        order = trader.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
        assert order.symbol == "AAPL"
        assert order.status == OrderStatus.PENDING
        assert order.tiger_order_id == "TIGER_123"
        mock_increment.assert_called_once_with(side="BUY", status="placed")


def test_place_order_validation_fail(mock_trade_client):
    mock_instance = mock_trade_client.return_value
    mock_instance.get_account_info.return_value = {"net_liquidation": 100000.0}
    trader = PaperTrader()
    trader.connect()

    # Quantity <= 0
    with pytest.raises(ValueError):
        trader.place_order("AAPL", OrderSide.BUY, 0, OrderType.MARKET)

    # Limit order without limit price
    with pytest.raises(ValueError):
        trader.place_order("AAPL", OrderSide.BUY, 10, OrderType.LIMIT)


def test_get_positions_caching(mock_trade_client):
    mock_instance = mock_trade_client.return_value
    mock_instance.get_account_info.return_value = {"net_liquidation": 100000.0}
    mock_instance.get_positions.return_value = [{"symbol": "AAPL", "quantity": 10}]

    trader = PaperTrader()
    trader.connect()

    # Call 1: Without cache (clears cache, fetches directly)
    pos1 = trader.get_positions(use_cache=False)
    assert "AAPL" in pos1
    assert mock_instance.get_positions.call_count == 1

    # Call 2: With cache (uses tiger API once and caches)
    pos2 = trader.get_positions(use_cache=True)
    assert "AAPL" in pos2
    assert mock_instance.get_positions.call_count == 2

    # Call 3: With cache (should not increment call_count on tiger API)
    pos3 = trader.get_positions(use_cache=True)
    assert mock_instance.get_positions.call_count == 2


def test_order_fill_triggers_metrics(mock_trade_client):
    """Test that order fill updates risk metric and increments trade counter."""
    mock_instance = mock_trade_client.return_value
    mock_instance.get_account_info.return_value = {"net_liquidation": 100000.0}
    trader = PaperTrader()
    trader.connect()

    with patch("tiger_trade_bot.trader.increment_trade") as mock_increment, \
         patch("tiger_trade_bot.trader.update_position_risk") as mock_risk:
        # Simulate order fill via update_order
        order = trader.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
        trader.update_order(order.tiger_order_id, "FILLED", 10, 150.0)

        # Check trade incremented with filled status
        mock_increment.assert_called_with(side="BUY", status="filled")
        # Risk should be updated for the position
        mock_risk.assert_called()
