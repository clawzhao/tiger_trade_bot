"""
Market Data Fetcher for Tiger Open API.

Provides:
- Real-time quotes
- Historical bars (kline data)
- WebSocket streaming for live price updates
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
import pandas as pd
from dataclasses import dataclass

from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.trade.trade_client import TradeClient
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.push.push_client import PushClient

from config import (
    TIGER_ID, ACCOUNT_ID, PRIVATE_KEY_PATH, SANDBOX_MODE,
    LOG_LEVEL, LOG_DIR, WS_ENABLED
)

logger = logging.getLogger(__name__)


@dataclass
class Quote:
    """Standardized quote data structure."""
    symbol: str
    bid_price: float
    ask_price: float
    bid_size: int
    ask_size: int
    last_price: float
    volume: int
    timestamp: datetime


@dataclass
class Bar:
    """OHLCV bar data."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class TigerDataFetcher:
    """Main class for fetching market data from Tiger Open API."""

    def __init__(self, tiger_id: str = TIGER_ID, account_id: str = ACCOUNT_ID,
                 private_key_path: str = PRIVATE_KEY_PATH,
                 sandbox: bool = SANDBOX_MODE):
        """Initialize data fetcher with Tiger credentials."""
        self.tiger_id = tiger_id
        self.account_id = account_id
        self.private_key_path = private_key_path
        self.sandbox = sandbox

        self._quote_client: Optional[QuoteClient] = None
        self._trade_client: Optional[TradeClient] = None
        self._push_client: Optional[PushClient] = None
        self._connected = False

        self._quote_callbacks: List[Callable] = []
        self._bar_callbacks: List[Callable] = []

    def connect(self) -> bool:
        """Establish connection to Tiger API."""
        try:
            # Configure client
            client_config = TigerOpenClientConfig(sandbox_debug=self.sandbox)
            client_config.private_key = read_private_key(self.private_key_path)
            client_config.tiger_id = self.tiger_id
            client_config.account = self.account_id

            # Initialize clients
            self._quote_client = QuoteClient(client_config)
            self._trade_client = TradeClient(client_config)

            if WS_ENABLED:
                self._push_client = PushClient(client_config)
                self._setup_websocket_callbacks()

            self._connected = True
            logger.info("✅ Data fetcher connected to Tiger API")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            return False

    def disconnect(self):
        """Close all connections."""
        if self._push_client:
            try:
                self._push_client.disconnect()
            except:
                pass
        self._connected = False
        logger.info("Disconnected from Tiger API")

    def is_connected(self) -> bool:
        return self._connected

    def get_quote(self, symbols: List[str]) -> Dict[str, Quote]:
        """
        Fetch real-time quotes for given symbols.

        Args:
            symbols: List of ticker symbols (e.g., ['AAPL', 'TSLA'])

        Returns:
            Dict mapping symbol to Quote object
        """
        if not self._connected or not self._quote_client:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            # Tiger returns: bid_ask_list with (bid_price, ask_price, bid_size, ask_size)
            quotes_data = self._quote_client.get_bid_ask(symbols)

            result = {}
            for symbol, data in quotes_data.items():
                # Extract data from Tiger's response format
                # The actual response structure may vary - adjust as needed
                bid_price = data.bid_price if hasattr(data, 'bid_price') else 0.0
                ask_price = data.ask_price if hasattr(data, 'ask_price') else 0.0
                bid_size = data.bid_size if hasattr(data, 'bid_size') else 0
                ask_size = data.ask_size if hasattr(data, 'ask_size') else 0
                last_price = data.last_price if hasattr(data, 'last_price') else 0.0
                volume = data.volume if hasattr(data, 'volume') else 0
                timestamp = datetime.now()

                result[symbol] = Quote(
                    symbol=symbol,
                    bid_price=bid_price,
                    ask_price=ask_price,
                    bid_size=bid_size,
                    ask_size=ask_size,
                    last_price=last_price,
                    volume=volume,
                    timestamp=timestamp
                )
            return result

        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")
            raise

    def get_bars(self, symbol: str, period: str = "day", count: int = 100,
                 start_time: Optional[datetime] = None,
                 end_time: Optional[datetime] = None) -> pd.DataFrame:
        """
        Fetch historical K-line data.

        Args:
            symbol: Ticker symbol
            period: Bar period - '1min', '5min', '15min', '30min', '60min', 'day', 'week'
            count: Number of bars to fetch (if start/end not provided)
            start_time: Start datetime (inclusive)
            end_time: End datetime (exclusive)

        Returns:
            pandas DataFrame with columns: timestamp, open, high, low, close, volume
        """
        if not self._connected or not self._quote_client:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            # Tiger's get_bars parameter format
            # Adjust based on actual tigeropen SDK implementation
            bars = self._quote_client.get_bars(
                symbol=symbol,
                period=period,
                count=count,
                start_time=start_time,
                end_time=end_time
            )

            # Convert to DataFrame
            data = []
            for bar in bars:
                data.append({
                    'timestamp': bar.timestamp,
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close,
                    'volume': bar.volume
                })

            df = pd.DataFrame(data)
            if not df.empty:
                df.set_index('timestamp', inplace=True)
                df.sort_index(inplace=True)
            return df

        except Exception as e:
            logger.error(f"Error fetching bars for {symbol}: {e}")
            raise

    def start_websocket(self, symbols: List[str]):
        """
        Start WebSocket streaming for real-time quotes.

        Args:
            symbols: List of symbols to subscribe

        Note:
            Callbacks must be registered via `on_quote()` and `on_bar()` before starting.
        """
        if not WS_ENABLED or not self._push_client:
            logger.warning("WebSocket not enabled or client not available")
            return

        try:
            # Subscribe to symbols
            for symbol in symbols:
                self._push_client.subscribe_quote(symbol)
                logger.info(f"Subscribed to {symbol} via WebSocket")
        except Exception as e:
            logger.error(f"Error starting WebSocket: {e}")

    def stop_websocket(self):
        """Stop WebSocket streaming."""
        if self._push_client:
            try:
                self._push_client.disconnect()
                logger.info("WebSocket stopped")
            except Exception as e:
                logger.error(f"Error stopping WebSocket: {e}")

    def on_quote(self, callback: Callable[[Quote], None]):
        """Register callback for quote updates (WebSocket)."""
        self._quote_callbacks.append(callback)

    def on_bar(self, callback: Callable[[Bar], None]):
        """Register callback for bar updates (WebSocket)."""
        self._bar_callbacks.append(callback)

    def _setup_websocket_callbacks(self):
        """Internal: Setup WebSocket callback handlers."""
        if not self._push_client:
            return

        def quote_callback(data):
            """Handle incoming quote data from WebSocket."""
            try:
                quote = Quote(
                    symbol=data.symbol,
                    bid_price=data.bid_price,
                    ask_price=data.ask_price,
                    bid_size=data.bid_size,
                    ask_size=data.ask_size,
                    last_price=data.last_price,
                    volume=data.volume,
                    timestamp=datetime.now()
                )
                for cb in self._quote_callbacks:
                    cb(quote)
            except Exception as e:
                logger.error(f"Error in quote callback: {e}")

        def bar_callback(data):
            """Handle incoming bar data from WebSocket."""
            try:
                bar = Bar(
                    symbol=data.symbol,
                    timestamp=data.timestamp,
                    open=data.open,
                    high=data.high,
                    low=data.low,
                    close=data.close,
                    volume=data.volume
                )
                for cb in self._bar_callbacks:
                    cb(bar)
            except Exception as e:
                logger.error(f"Error in bar callback: {e}")

        # Register with PushClient (actual method names may vary)
        self._push_client.on_quote = quote_callback
        self._push_client.on_bar = bar_callback

    # Convenience methods
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information (balance, positions, etc.)."""
        if not self._trade_client:
            raise RuntimeError("Trade client not initialized")
        return self._trade_client.get_account_info(self.account_id)

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current open positions."""
        if not self._trade_client:
            raise RuntimeError("Trade client not initialized")
        return self._trade_client.get_positions(self.account_id)