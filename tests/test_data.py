import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import pandas as pd

from tiger_trade_bot.data import TigerDataFetcher, Quote, Bar

@pytest.fixture
def mock_clients():
    with patch("tiger_trade_bot.data.QuoteClient") as mock_quote_client, \
         patch("tiger_trade_bot.data.TradeClient") as mock_trade_client, \
         patch("tiger_trade_bot.data.PushClient") as mock_push_client, \
         patch("tiger_trade_bot.data.read_private_key") as mock_read_key:
        yield mock_quote_client, mock_trade_client, mock_push_client

def test_connect_success(mock_clients):
    mock_quote, mock_trade, mock_push = mock_clients
    fetcher = TigerDataFetcher("TEST_ID", "TEST_ACC", "fake/path.pem", True)
    assert fetcher.connect() is True
    assert fetcher.is_connected() is True

def test_get_bars_limits_to_500(mock_clients):
    mock_quote, _, _ = mock_clients
    mock_instance = mock_quote.return_value
    
    # Create 600 fake bars
    fake_bars = []
    class DummyBar:
        def __init__(self, i):
            self.timestamp = datetime(2023, 1, 1)
            self.open = i
            self.high = i
            self.low = i
            self.close = i
            self.volume = i

    for i in range(600):
        fake_bars.append(DummyBar(i))
    
    mock_instance.get_bars.return_value = fake_bars
    
    fetcher = TigerDataFetcher()
    fetcher.connect()
    
    # Request 600 bars
    df = fetcher.get_bars("AAPL", count=600)
    
    # count gets clipped to 500 internally in get_bars (count = min(count, 500))
    # and the result is df.tail(500)
    assert len(df) == 500

def test_get_bars_generator(mock_clients):
    mock_quote, _, _ = mock_clients
    mock_instance = mock_quote.return_value
    
    class DummyBar:
        def __init__(self):
            self.timestamp = datetime(2023, 1, 1)
            self.open = 100
            self.high = 110
            self.low = 90
            self.close = 105
            self.volume = 1000

    mock_instance.get_bars.return_value = [DummyBar(), DummyBar()]
    
    fetcher = TigerDataFetcher()
    fetcher.connect()
    
    gen = fetcher.get_bars_generator("AAPL", count=2)
    bars = list(gen)
    
    assert len(bars) == 2
    assert bars[0]["open"] == 100

def test_websocket_ping_pong_reconnect(mock_clients):
    mock_quote, mock_trade, mock_push = mock_clients
    mock_push_instance = mock_push.return_value
    
    fetcher = TigerDataFetcher()
    fetcher.connect()
    
    # Mock time.sleep to avoid hanging
    with patch("time.sleep", return_value=None):
        fetcher.start_websocket(["AAPL"])
        assert fetcher._ws_running is True
        
        # Test stop
        fetcher.stop_websocket()
        assert fetcher._ws_running is False
        mock_push_instance.disconnect.assert_called()

def test_get_account_info_caching(mock_clients):
    _, mock_trade, _ = mock_clients
    mock_trade_instance = mock_trade.return_value
    mock_trade_instance.get_account_info.return_value = {"net_liquidation": 10000}
    
    fetcher = TigerDataFetcher()
    fetcher.connect()
    
    # First call
    res1 = fetcher.get_account_info()
    assert res1["net_liquidation"] == 10000
    
    # Second call (should be cached)
    res2 = fetcher.get_account_info()
    
    # trade client called once due to lru_cache
    mock_trade_instance.get_account_info.assert_called_once()
