"""
Performance tests for Tiger Trade Bot.

Measures:
- PaperTrader.connect() latency (with mocked Tiger API)
- Order placement path latency
- Account summary fetch latency
- Position retrieval latency

Run with: pytest -m performance tests/performance/test_latency.py
Or: python -m tests.performance.test_latency
"""

import time
import statistics
from typing import List, Callable
from unittest.mock import MagicMock, patch

import pytest
from tiger_trade_bot.trader import PaperTrader
from tiger_trade_bot.data import TigerDataFetcher


def measure_operation(operation: Callable, iterations: int = 100) -> List[float]:
    """Run an operation multiple times and collect durations in seconds."""
    durations = []
    for _ in range(iterations):
        start = time.perf_counter()
        try:
            operation()
        except Exception as e:
            # In performance tests, we may mock; ignore errors but count time
            pass
        end = time.perf_counter()
        durations.append(end - start)
    return durations


def print_stats(name: str, durations: List[float]) -> None:
    """Print summary statistics."""
    mean = statistics.mean(durations)
    median = statistics.median(durations)
    stdev = statistics.stdev(durations) if len(durations) > 1 else 0.0
    p95 = sorted(durations)[int(0.95 * len(durations)) - 1]
    print(f"\n{name}:")
    print(f"  Iterations: {len(durations)}")
    print(f"  Mean:   {mean*1000:.3f} ms")
    print(f"  Median: {median*1000:.3f} ms")
    print(f"  Stdev:  {stdev*1000:.3f} ms")
    print(f"  P95:    {p95*1000:.3f} ms")


@pytest.fixture
def mock_tiger_client():
    """Create a mock Tiger TradeClient."""
    with patch('tiger_trade_bot.trader.TradeClient') as mock_client:
        instance = mock_client.return_value

        # Mock get_account_info
        instance.get_account_info.return_value = {
            'net_liquidation': 100000.0,
            'cash_balance': 50000.0,
            'buying_power': 100000.0,
            'total_profit_loss': 0.0,
        }

        # Mock get_positions
        instance.get_positions.return_value = [
            {
                'symbol': 'AAPL',
                'quantity': 100,
                'average_cost': 150.0,
                'last_price': 155.0,
                'side': 'BUY',
            }
        ]

        # Mock place_order
        instance.place_order.return_value = "mock_order_123"

        # Mock cancel_order
        instance.cancel_order.return_value = None

        yield instance


@pytest.fixture
def trader(mock_tiger_client):
    """Create a PaperTrader instance (connected)."""
    trader = PaperTrader(
        tiger_id="test_id",
        account_id="test_account",
        private_key_path="./keys/rsa_private_key.pem",
        sandbox=True,
        max_position_size=10000.0,
    )
    # Force connected state (we test with mocked client)
    trader._trade_client = mock_tiger_client
    trader._connected = True
    return trader


@pytest.mark.performance
def test_connect_latency(mock_tiger_client):
    """Benchmark PaperTrader.connect() latency."""
    durations = measure_operation(
        lambda: PaperTrader(
            tiger_id="test_id",
            account_id="test_account",
            private_key_path="./keys/rsa_private_key.pem",
            sandbox=True,
        ).connect(),
        iterations=50
    )
    print_stats("connect() latency", durations)


@pytest.mark.performance
def test_get_account_summary_latency(trader):
    """Benchmark get_account_summary() latency."""
    durations = measure_operation(
        lambda: trader.get_account_summary(),
        iterations=100
    )
    print_stats("get_account_summary() latency", durations)


@pytest.mark.performance
def test_get_positions_latency(trader):
    """Benchmark get_positions() latency."""
    durations = measure_operation(
        lambda: trader.get_positions(),
        iterations=100
    )
    print_stats("get_positions() latency", durations)


@pytest.mark.performance
def test_place_order_latency(trader):
    """Benchmark place_order() latency."""
    from tiger_trade_bot.trader import OrderSide, OrderType
    durations = measure_operation(
        lambda: trader.place_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=10,
            order_type=OrderType.MARKET
        ),
        iterations=100
    )
    print_stats("place_order() latency", durations)


@pytest.mark.performance
def test_cancel_order_latency(trader):
    """Benchmark cancel_order() latency."""
    # First place an order so we have something to cancel
    from tiger_trade_bot.trader import OrderSide, OrderType
    order = trader.place_order(
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=10,
        order_type=OrderType.MARKET
    )
    durations = measure_operation(
        lambda: trader.cancel_order(order.id),
        iterations=50
    )
    print_stats("cancel_order() latency", durations)


if __name__ == "__main__":
    # Run standalone (without pytest) for quick benchmark
    print("Running performance tests standalone (mocked)...")
    with patch('tiger_trade_bot.trader.TradeClient') as mock_client:
        instance = mock_client.return_value
        instance.get_account_info.return_value = {
            'net_liquidation': 100000.0,
            'cash_balance': 50000.0,
            'buying_power': 100000.0,
            'total_profit_loss': 0.0,
        }
        instance.get_positions.return_value = [
            {'symbol': 'AAPL', 'quantity': 100, 'average_cost': 150.0, 'last_price': 155.0, 'side': 'BUY'}
        ]
        instance.place_order.return_value = "mock_order_123"
        instance.cancel_order.return_value = None

        tr = PaperTrader(tiger_id="test", account_id="test", private_key_path="./keys/rsa_private_key.pem", sandbox=True)
        tr._trade_client = instance
        tr._connected = True

        test_connect_latency(mock_client)
        test_get_account_summary_latency(tr)
        test_get_positions_latency(tr)
        test_place_order_latency(tr)
        test_cancel_order_latency(tr)
