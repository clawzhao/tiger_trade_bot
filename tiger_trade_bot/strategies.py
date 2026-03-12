"""
Trading Strategies for Tiger Trade Bot.

Current strategies:
- GapTradingStrategy: Simple gap fill strategy (overnight gaps)
- MovingAverageCrossover: SMA crossover strategy
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, time
from enum import Enum

import pandas as pd
import numpy as np

from .data import Bar, Quote, TigerDataFetcher
from .trader import PaperTrader, OrderSide, OrderType

logger = logging.getLogger(__name__)


class Signal(Enum):
    BUY = "BUY"
    SELL = "SHORT"  # or SELL to close long
    HOLD = "HOLD"


@dataclass
class TradeSignal:
    """Trading signal with metadata."""
    symbol: str
    signal: Signal
    confidence: float = 1.0  # 0.0 to 1.0
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: str = ""


class BaseStrategy:
    """Base class for trading strategies."""

    def __init__(self, symbols: List[str], data_fetcher: TigerDataFetcher,
                 trader: PaperTrader, parameters: Optional[Dict] = None):
        self.symbols = symbols
        self.data = data_fetcher
        self.trader = trader
        self.parameters = parameters or {}
        self._bar_history: Dict[str, pd.DataFrame] = {}

    def initialize(self) -> bool:
        """Load initial historical data."""
        try:
            for symbol in self.symbols:
                df = self.data.get_bars(symbol, period="day", count=100)
                if not df.empty:
                    self._bar_history[symbol] = df
                    logger.info(f"Loaded {len(df)} bars for {symbol}")
            return True
        except Exception as e:
            logger.error(f"Strategy initialization failed: {e}")
            return False

    def on_bar(self, bar: Bar):
        """Called when a new bar arrives via WebSocket."""
        symbol = bar.symbol
        if symbol not in self._bar_history:
            self._bar_history[symbol] = pd.DataFrame()

        # Append new bar
        new_row = pd.DataFrame([{
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume
        }], index=[bar.timestamp])

        self._bar_history[symbol] = pd.concat([self._bar_history[symbol], new_row]).tail(200)

        # Generate signal and execute
        signal = self.generate_signal(symbol)
        if signal.signal != Signal.HOLD:
            self.execute_signal(signal)

    def on_quote(self, quote: Quote):
        """Called when a new quote arrives via WebSocket."""
        # Optional: implement quote-level logic
        pass

    def generate_signal(self, symbol: str) -> TradeSignal:
        """Generate trading signal for given symbol. Override in subclass."""
        raise NotImplementedError

    def execute_signal(self, signal: TradeSignal):
        """Execute the trading signal."""
        symbol = signal.symbol
        position_size = self._calculate_position_size(signal.price)

        if signal.signal == Signal.BUY:
            logger.info(f"📈 BUY signal for {symbol} @ ${signal.price:.2f} "
                       f"(size: {position_size}, reason: {signal.reason})")
            try:
                order = self.trader.place_order(
                    symbol=symbol,
                    side=OrderSide.BUY,
                    quantity=position_size,
                    order_type=OrderType.MARKET
                )
                logger.info(f"   Order placed: {order.id}")
            except Exception as e:
                logger.error(f"   Order failed: {e}")

        elif signal.signal == Signal.SELL:
            # For now, SELL means short; adjust for your strategy
            logger.info(f"📉 SELL (short) signal for {symbol} @ ${signal.price:.2f} "
                       f"(size: {position_size})")
            # Implement short selling if supported
            pass

    def _calculate_position_size(self, price: float) -> int:
        """Calculate position size based on account and risk parameters."""
        # Simple position sizing: fixed share count
        # TODO: Implement proper Kelly criterion or fixed $ amount
        return 100  # Fixed 100 shares for now

    def get_indicators(self, symbol: str) -> Dict[str, float]:
        """Calculate technical indicators from bar history."""
        if symbol not in self._bar_history:
            return {}

        df = self._bar_history[symbol]
        if len(df) < 20:
            return {}

        close = df['close']
        high = df['high']
        low = df['low']

        indicators = {
            'sma_20': close.rolling(20).mean().iloc[-1],
            'sma_50': close.rolling(50).mean().iloc[-1] if len(df) >= 50 else None,
            'sma_200': close.rolling(200).mean().iloc[-1] if len(df) >= 200 else None,
            'rsi_14': self._calculate_rsi(close, 14),
            'atr_14': self._calculate_atr(high, low, close, 14),
            'high_52w': high.rolling(252).max().iloc[-1] if len(df) >= 252 else high.max(),
            'low_52w': low.rolling(252).min().iloc[-1] if len(df) >= 252 else low.min(),
        }
        return {k: v for k, v in indicators.items() if v is not None}

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return 50.0

        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return rsi.iloc[-1]

    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
        """Calculate Average True Range."""
        if len(high) < period:
            return (high - low).mean()

        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()
        return atr.iloc[-1]


class GapTradingStrategy(BaseStrategy):
    """
    Gap Trading Strategy:

    Logic:
    1. Identify overnight gaps (current open vs previous close)
    2. If price gaps up significantly (> 2%), wait for pullback into gap half
    3. If price gaps down significantly (> 2%), fade the rally
    4. Hold for intraday mean reversion

    Parameters:
    - gap_threshold_pct: Minimum gap size to trigger (default 2%)
    - hold_period_bars: How long to hold position (default 10 bars)
    """

    def __init__(self, symbols: List[str], data_fetcher: TigerDataFetcher,
                 trader: PaperTrader, parameters: Optional[Dict] = None):
        super().__init__(symbols, data_fetcher, trader, parameters)
        self.gap_threshold = self.parameters.get('gap_threshold_pct', 0.02)
        self.hold_period = self.parameters.get('hold_period_bars', 10)

    def generate_signal(self, symbol: str) -> TradeSignal:
        if symbol not in self._bar_history:
            return TradeSignal(symbol, Signal.HOLD)

        df = self._bar_history[symbol]
        if len(df) < 2:
            return TradeSignal(symbol, Signal.HOLD)

        # Get today's bar and previous close
        current_bar = df.iloc[-1]
        prev_close = df.iloc[-2]['close']

        # Calculate gap
        gap_pct = (current_bar['open'] - prev_close) / prev_close
        current_price = current_bar['close']  # Use current close for decision

        signal = Signal.HOLD
        reason = ""

        # Gap Up > threshold -> Look for short entry (fade)
        if gap_pct > self.gap_threshold:
            # Check if price has pulled back into the gap
            gap_fill_level = prev_close + (current_bar['open'] - prev_close) / 2
            if current_price <= gap_fill_level:
                signal = Signal.SELL
                reason = f"Gap fill short: gap={gap_pct:.2%}, price=${current_price:.2f}"

        # Gap Down > threshold -> Look for long entry (fade)
        elif gap_pct < -self.gap_threshold:
            gap_fill_level = prev_close + (current_bar['open'] - prev_close) / 2
            if current_price >= gap_fill_level:
                signal = Signal.BUY
                reason = f"Gap fill long: gap={gap_pct:.2%}, price=${current_price:.2f}"

        return TradeSignal(
            symbol=symbol,
            signal=signal,
            price=current_price,
            reason=reason
        )


class MovingAverageCrossoverStrategy(BaseStrategy):
    """
    Simple SMA Crossover Strategy:

    - Buy when fast MA crosses above slow MA
    - Sell (short) when fast MA crosses below slow MA

    Parameters:
    - fast_period: Fast SMA period (default 10)
    - slow_period: Slow SMA period (default 50)
    """

    def __init__(self, symbols: List[str], data_fetcher: TigerDataFetcher,
                 trader: PaperTrader, parameters: Optional[Dict] = None):
        super().__init__(symbols, data_fetcher, trader, parameters)
        self.fast_period = self.parameters.get('fast_period', 10)
        self.slow_period = self.parameters.get('slow_period', 50)
        self._last_signal: Dict[str, Signal] = {}

    def generate_signal(self, symbol: str) -> TradeSignal:
        df = self._bar_history.get(symbol)
        if df is None or len(df) < self.slow_period + 5:
            return TradeSignal(symbol, Signal.HOLD)

        # Calculate MAs
        fast_ma = df['close'].rolling(self.fast_period).mean()
        slow_ma = df['close'].rolling(self.slow_period).mean()

        if len(fast_ma) < 2 or len(slow_ma) < 2:
            return TradeSignal(symbol, Signal.HOLD)

        fast_current = fast_ma.iloc[-1]
        fast_prev = fast_ma.iloc[-2]
        slow_current = slow_ma.iloc[-1]
        slow_prev = slow_ma.iloc[-2]

        current_price = df['close'].iloc[-1]
        current_signal = Signal.HOLD
        reason = ""

        # Bullish crossover: fast crosses above slow
        if fast_prev <= slow_prev and fast_current > slow_current:
            current_signal = Signal.BUY
            reason = f"SMA crossover: fast(>{self.fast_period}) {fast_prev:.2f}->{fast_current:.2f} crossed above slow(>{self.slow_period})"

        # Bearish crossover: fast crosses below slow
        elif fast_prev >= slow_prev and fast_current < slow_current:
            current_signal = Signal.SELL
            reason = f"SMA crossover: fast crossed below slow"

        # Detect reverting back to HOLD
        elif self._last_signal.get(symbol, Signal.HOLD) != Signal.HOLD and current_signal == Signal.HOLD:
            reason = "Signal neutralized"

        self._last_signal[symbol] = current_signal

        return TradeSignal(
            symbol=symbol,
            signal=current_signal,
            price=current_price,
            reason=reason
        )