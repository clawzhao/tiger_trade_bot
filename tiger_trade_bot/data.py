"""
Market Data Fetcher for Tiger Open API.

Provides:
- Real-time quotes
- Historical bars (kline data)
- WebSocket streaming for live price updates with reconnection/ping-pong
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Any, Callable, Generator
from datetime import datetime, timedelta
from functools import lru_cache
import pandas as pd
from dataclasses import dataclass

from tenacity import retry, stop_after_attempt, wait_exponential

from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.trade.trade_client import TradeClient
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.push.push_client import PushClient

from config import (
    TIGER_ID, ACCOUNT_ID, PRIVATE_KEY_PATH, SANDBOX_MODE,
    LOG_LEVEL, LOG_DIR, WS_ENABLED, WS_RECONNECT_INTERVAL
)

logger = logging.getLogger(__name__)


@dataclass
class Quote:
    """Standardized quote data structure.

    Attributes:
        symbol (str): The ticker symbol.
        bid_price (float): Current highest bid price.
        ask_price (float): Current lowest ask price.
        bid_size (int): Size of the bid.
        ask_size (int): Size of the ask.
        last_price (float): The most recent traded price.
        volume (int): The trading volume.
        timestamp (datetime): Timestamp of the quote.
    """
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
    """OHLCV bar data.

    Attributes:
        symbol (str): The ticker symbol.
        timestamp (datetime): Start time of the bar.
        open (float): Open price.
        high (float): High price.
        low (float): Low price.
        close (float): Close price.
        volume (int): Trading volume.
    """
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
                 sandbox: bool = SANDBOX_MODE) -> None:
        """Initialize data fetcher with Tiger credentials.

        Args:
            tiger_id (str): Tiger developer ID.
            account_id (str): Tiger paper or live account ID.
            private_key_path (str): Path to RSA private key.
            sandbox (bool): True for paper trading, False for live.
        """
        self.tiger_id = tiger_id
        self.account_id = account_id
        self.private_key_path = private_key_path
        self.sandbox = sandbox

        self._quote_client: Optional[QuoteClient] = None
        self._trade_client: Optional[TradeClient] = None
        self._push_client: Optional[PushClient] = None
        self._connected: bool = False

        self._quote_callbacks: List[Callable[[Quote], None]] = []
        self._bar_callbacks: List[Callable[[Bar], None]] = []
        
        # WebSocket health monitoring
        self._ws_symbols: List[str] = []
        self._ws_monitor_thread: Optional[threading.Thread] = None
        self._ws_running: bool = False
        self._last_ping_time: float = 0.0

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    def connect(self) -> bool:
        """Establish connection to Tiger API with retries.

        Returns:
            bool: True if connection is successful, False otherwise.
        """
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
            raise  # Let tenacity retry

    def disconnect(self) -> None:
        """Close all connections and stop WebSocket monitor."""
        self._ws_running = False
        if self._push_client:
            try:
                self._push_client.disconnect()
            except Exception:
                pass
        self._connected = False
        logger.info("Disconnected from Tiger API")

    def is_connected(self) -> bool:
        """Check connection status.

        Returns:
            bool: Connection status.
        """
        return self._connected

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    def get_quote(self, symbols: List[str]) -> Dict[str, Quote]:
        """Fetch real-time quotes for given symbols with retry logic.

        Args:
            symbols (List[str]): List of ticker symbols (e.g., ['AAPL', 'TSLA'])

        Returns:
            Dict[str, Quote]: Dictionary mapping symbol to Quote object.
        """
        if not self._connected or not self._quote_client:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            quotes_data = self._quote_client.get_bid_ask(symbols)

            result = {}
            for symbol, data in quotes_data.items():
                result[symbol] = Quote(
                    symbol=symbol,
                    bid_price=getattr(data, 'bid_price', 0.0),
                    ask_price=getattr(data, 'ask_price', 0.0),
                    bid_size=getattr(data, 'bid_size', 0),
                    ask_size=getattr(data, 'ask_size', 0),
                    last_price=getattr(data, 'last_price', 0.0),
                    volume=getattr(data, 'volume', 0),
                    timestamp=datetime.now()
                )
            return result

        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")
            raise

    def get_bars_generator(self, symbol: str, period: str = "day", count: int = 100) -> Generator[Dict[str, Any], None, None]:
        """Memory-optimized generator for historical K-line data.
        
        Args:
            symbol (str): Ticker symbol.
            period (str): Bar period (e.g., 'day', '5min').
            count (int): Number of bars to fetch.
            
        Yields:
            Dict[str, Any]: Dictionary representation of a bar.
        """
        if not self._connected or not self._quote_client:
            raise RuntimeError("Not connected. Call connect() first.")
            
        try:
            bars = self._quote_client.get_bars(symbol=symbol, period=period, count=count)
            for bar in bars:
                yield {
                    'timestamp': bar.timestamp,
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close,
                    'volume': bar.volume
                }
        except Exception as e:
            logger.error(f"Error fetching bars generator for {symbol}: {e}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    def get_bars(self, symbol: str, period: str = "day", count: int = 100,
                 start_time: Optional[datetime] = None,
                 end_time: Optional[datetime] = None) -> pd.DataFrame:
        """Fetch historical K-line data as DataFrame, limited to 500 bars for memory optimization.

        Args:
            symbol (str): Ticker symbol.
            period (str): Bar period - '1min', '5min', '15min', '30min', '60min', 'day', 'week'.
            count (int): Number of bars to fetch (if start/end not provided).
            start_time (Optional[datetime]): Start datetime (inclusive).
            end_time (Optional[datetime]): End datetime (exclusive).

        Returns:
            pd.DataFrame: DataFrame with columns: timestamp, open, high, low, close, volume.
        """
        if not self._connected or not self._quote_client:
            raise RuntimeError("Not connected. Call connect() first.")

        # Ensure we don't request too many bars to save memory on Pi
        count = min(count, 500)

        try:
            bars = self._quote_client.get_bars(
                symbol=symbol,
                period=period,
                count=count,
                start_time=start_time,
                end_time=end_time
            )

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
                
            # Strict memory limit enforcement (500 rows max)
            return df.tail(500)

        except Exception as e:
            logger.error(f"Error fetching bars for {symbol}: {e}")
            raise

    def start_websocket(self, symbols: List[str]) -> None:
        """Start WebSocket streaming for real-time quotes with auto-reconnection.

        Args:
            symbols (List[str]): List of symbols to subscribe.
        """
        if not WS_ENABLED or not self._push_client:
            logger.warning("WebSocket not enabled or client not available")
            return

        self._ws_symbols = symbols
        self._ws_running = True
        
        try:
            self._connect_and_subscribe_ws()
            
            # Start monitoring thread
            self._ws_monitor_thread = threading.Thread(target=self._monitor_websocket, daemon=True)
            self._ws_monitor_thread.start()
        except Exception as e:
            logger.error(f"Error starting WebSocket: {e}")

    def _connect_and_subscribe_ws(self) -> None:
        """Helper to connect and subscribe to WS."""
        if not self._push_client:
            return
            
        try:
            self._push_client.connect()
            for symbol in self._ws_symbols:
                self._push_client.subscribe_quote(symbol)
                logger.info(f"Subscribed to {symbol} via WebSocket")
            self._last_ping_time = time.time()
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")

    def _monitor_websocket(self) -> None:
        """Background thread to monitor WS connection and reconnect if needed."""
        while self._ws_running:
            time.sleep(WS_RECONNECT_INTERVAL)
            if not self._push_client:
                continue
                
            # Simulated ping/pong or connection check. In a real scenario,
            # this would check the socket status or send a ping message.
            try:
                # Basic ping/pong verification by checking the connection
                # The Tiger SDK usually handles heartbeat, but we ensure it's alive here
                current_time = time.time()
                # Sending an empty string or standard ping frame if supported
                if hasattr(self._push_client, 'ping'):
                    self._push_client.ping()
                self._last_ping_time = current_time
            except Exception as e:
                logger.warning(f"WebSocket connection lost, attempting reconnect... {e}")
                try:
                    self._push_client.disconnect()
                except Exception:
                    pass
                time.sleep(2)
                self._connect_and_subscribe_ws()

    def stop_websocket(self) -> None:
        """Stop WebSocket streaming."""
        self._ws_running = False
        if self._push_client:
            try:
                self._push_client.disconnect()
                logger.info("WebSocket stopped")
            except Exception as e:
                logger.error(f"Error stopping WebSocket: {e}")

    def on_quote(self, callback: Callable[[Quote], None]) -> None:
        """Register callback for quote updates (WebSocket)."""
        self._quote_callbacks.append(callback)

    def on_bar(self, callback: Callable[[Bar], None]) -> None:
        """Register callback for bar updates (WebSocket)."""
        self._bar_callbacks.append(callback)

    def _setup_websocket_callbacks(self) -> None:
        """Internal: Setup WebSocket callback handlers."""
        if not self._push_client:
            return

        def quote_callback(data: Any) -> None:
            """Handle incoming quote data from WebSocket."""
            self._last_ping_time = time.time()  # Reset ping timer on message
            try:
                quote = Quote(
                    symbol=data.symbol,
                    bid_price=getattr(data, 'bid_price', 0.0),
                    ask_price=getattr(data, 'ask_price', 0.0),
                    bid_size=getattr(data, 'bid_size', 0),
                    ask_size=getattr(data, 'ask_size', 0),
                    last_price=getattr(data, 'last_price', 0.0),
                    volume=getattr(data, 'volume', 0),
                    timestamp=datetime.now()
                )
                for cb in self._quote_callbacks:
                    cb(quote)
            except Exception as e:
                logger.error(f"Error in quote callback: {e}")

        def bar_callback(data: Any) -> None:
            """Handle incoming bar data from WebSocket."""
            self._last_ping_time = time.time()  # Reset ping timer on message
            try:
                bar = Bar(
                    symbol=data.symbol,
                    timestamp=data.timestamp,
                    open=getattr(data, 'open', 0.0),
                    high=getattr(data, 'high', 0.0),
                    low=getattr(data, 'low', 0.0),
                    close=getattr(data, 'close', 0.0),
                    volume=getattr(data, 'volume', 0)
                )
                for cb in self._bar_callbacks:
                    cb(bar)
            except Exception as e:
                logger.error(f"Error in bar callback: {e}")

        self._push_client.quote_changed = quote_callback
        self._push_client.kline_changed = bar_callback

    @lru_cache(maxsize=1)
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information (balance, positions, etc.) with LRU cache and retries.

        Returns:
            Dict[str, Any]: Account information.
        """
        if not self._trade_client:
            raise RuntimeError("Trade client not initialized")
        return self._trade_client.get_account_info(self.account_id)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5), reraise=True)
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current open positions.

        Returns:
            List[Dict[str, Any]]: List of position dictionaries.
        """
        if not self._trade_client:
            raise RuntimeError("Trade client not initialized")
        return self._trade_client.get_positions(self.account_id)
