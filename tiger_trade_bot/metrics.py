"""
Prometheus metrics for Tiger Trade Bot.

Metrics:
- trade_count: Counter of orders placed/filled by side and status
- portfolio_value: Current net liquidation value (Gauge)
- agent_latency: Histogram of API call durations (seconds)
- risk_utilization: Position sizes relative to max limit (Gauge)
"""

import time
from typing import Optional, Dict, Any
from threading import Lock
from contextlib import contextmanager

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    start_http_server,
    REGISTRY,
    CONTENT_TYPE_LATEST,
    generate_latest,
)

# Metric definitions
trade_count = Counter(
    "tiger_trade_bot_orders_total",
    "Total number of orders placed",
    ["side", "status"]
)

portfolio_value = Gauge(
    "tiger_trade_bot_portfolio_value",
    "Current net liquidation value (USD)"
)

agent_latency = Histogram(
    "tiger_trade_bot_agent_latency_seconds",
    "Latency of agent operations",
    ["operation"]
)

risk_utilization = Gauge(
    "tiger_trade_bot_risk_utilization",
    "Current risk utilization (position_size / max_position_size ratio)",
    ["symbol"]
)

# Internal tracking for gauges
_current_net_liquidation: float = 0.0
_max_position_size: float = 10000.0
_position_sizes: Dict[str, float] = {}
_metrics_lock = Lock()


def set_portfolio_value(value: float) -> None:
    """Update the portfolio value gauge."""
    global _current_net_liquidation
    with _metrics_lock:
        _current_net_liquidation = value
        portfolio_value.set(value)


def set_max_position_size(max_size: float) -> None:
    """Configure the max position size for risk calculation."""
    global _max_position_size
    with _metrics_lock:
        _max_position_size = max_size


def update_position_risk(symbol: str, position_value: float) -> None:
    """Update risk utilization for a symbol (position_value / max_position_size)."""
    with _metrics_lock:
        _position_sizes[symbol] = position_value
        if _max_position_size > 0:
            utilization = min(position_value / _max_position_size, 1.0)
            risk_utilization.labels(symbol=symbol).set(utilization)


def clear_position_risk(symbol: str) -> None:
    """Remove risk metric for a symbol when position is closed."""
    with _metrics_lock:
        _position_sizes.pop(symbol, None)
        try:
            risk_utilization.remove(symbol)
        except KeyError:
            pass


def update_all_position_risks(positions: Dict[str, Any], max_position_size: float) -> None:
    """Bulk update risk metrics from positions dict."""
    set_max_position_size(max_position_size)
    for symbol, pos in positions.items():
        # Estimate position value: quantity * current_price
        quantity = pos.get("quantity", 0) if isinstance(pos, dict) else getattr(pos, "quantity", 0)
        price = pos.get("last_price", 0) if isinstance(pos, dict) else getattr(pos, "current_price", 0)
        value = quantity * price
        update_position_risk(symbol, value)


@contextmanager
def measure_latency(operation: str):
    """Context manager to measure operation latency."""
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        agent_latency.labels(operation=operation).observe(duration)


def increment_trade(side: str, status: str) -> None:
    """Increment trade counter."""
    trade_count.labels(side=side, status=status).inc()


def start_metrics_server(port: int = 9090) -> None:
    """Start the Prometheus metrics HTTP server."""
    start_http_server(port)
    print(f"Metrics server started on port {port}")


def get_metrics() -> bytes:
    """Return current metrics in Prometheus text format."""
    return generate_latest(REGISTRY)
