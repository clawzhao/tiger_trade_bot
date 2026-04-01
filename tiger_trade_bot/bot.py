"""
Tiger Trade Bot - Main Entry Point

Usage:
    python -m tiger_trade_bot --strategy gap --symbols AAPL,TSLA
    python -m tiger_trade_bot --strategy ma --symbols AAPL --fast 10 --slow 50
"""

import argparse
import sys
import signal
import threading
import time
from pathlib import Path
from datetime import datetime

from config import (
    TIGER_ID,
    ACCOUNT_ID,
    PRIVATE_KEY_PATH,
    SANDBOX_MODE,
    LOG_LEVEL,
    LOG_DIR,
    WS_ENABLED,
    HEALTH_PORT,
    METRICS_PORT,
    MAX_POSITION_SIZE,
    validate_config,
)
from .logger import setup_logging
from .metrics import start_metrics_server, set_portfolio_value, update_all_position_risks, increment_trade
from .health import start_health_server_in_thread
from .data import TigerDataFetcher
from .trader import PaperTrader
from .strategies import GapTradingStrategy, MovingAverageCrossoverStrategy, TradeSignal


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Tiger Trade Bot - Paper trading with Tiger Open API"
    )
    parser.add_argument(
        "--strategy",
        choices=["gap", "ma"],
        default="gap",
        help="Trading strategy to use",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default="AAPL,TSLA,SPY",
        help="Comma-separated list of symbols to trade",
    )
    parser.add_argument(
        "--sandbox",
        action="store_true",
        default=SANDBOX_MODE,
        help="Run in paper trading (sandbox) mode",
    )
    parser.add_argument(
        "--tiger-id", type=str, default=TIGER_ID, help="Tiger Developer ID"
    )
    parser.add_argument(
        "--account-id", type=str, default=ACCOUNT_ID, help="Paper trading account ID"
    )
    parser.add_argument(
        "--key-path",
        type=str,
        default=PRIVATE_KEY_PATH,
        help="Path to RSA private key (.pem)",
    )
    parser.add_argument(
        "--no-websocket", action="store_true", help="Disable WebSocket streaming"
    )

    # Strategy-specific parameters
    parser.add_argument(
        "--gap-threshold",
        type=float,
        default=0.02,
        help="Gap threshold (percentage, default 2%%)",
    )
    parser.add_argument(
        "--fast", type=int, default=10, help="Fast MA period for MA strategy"
    )
    parser.add_argument(
        "--slow", type=int, default=50, help="Slow MA period for MA strategy"
    )

    return parser.parse_args()


def create_strategy(args, data_fetcher: TigerDataFetcher, trader: PaperTrader):
    """Instantiate the selected strategy with parameters."""
    symbols = [s.strip().upper() for s in args.symbols.split(",")]
    strategy_name = args.strategy

    if strategy_name == "gap":
        params = {"gap_threshold_pct": args.gap_threshold, "hold_period_bars": 10}
        strategy = GapTradingStrategy(symbols, data_fetcher, trader, params)

    elif strategy_name == "ma":
        params = {"fast_period": args.fast, "slow_period": args.slow}
        strategy = MovingAverageCrossoverStrategy(symbols, data_fetcher, trader, params)

    else:
        raise ValueError(f"Unknown strategy: {strategy_name}")

    return strategy


def main():
    """Main bot entry point."""
    args = parse_args()
    validate_config()
    logger = setup_logging(log_level=LOG_LEVEL, log_dir=LOG_DIR)

    logger.info("=" * 60)
    logger.info("🐯📈 Tiger Trade Bot Starting")
    logger.info("=" * 60)
    logger.info(f"Strategy: {args.strategy}")
    logger.info(f"Symbols: {args.symbols}")
    logger.info(f"Sandbox mode: {args.sandbox}")
    logger.info(f"WebSocket: {not args.no_websocket}")

    # Start Prometheus metrics server in background
    metrics_thread = threading.Thread(
        target=lambda: start_metrics_server(METRICS_PORT),
        daemon=True,
        name="MetricsServer"
    )
    metrics_thread.start()
    logger.info(f"📊 Metrics server started on port {METRICS_PORT}")

    # Validate credentials explicitly
    if args.tiger_id == "YOUR_TIGER_ID" or not args.tiger_id:
        logger.error("Missing Tiger ID. Set in .env or via --tiger-id")
        sys.exit(1)
    if args.account_id == "YOUR_PAPER_ACCOUNT_ID" or not args.account_id:
        logger.error("Missing Account ID. Set in .env or via --account-id")
        sys.exit(1)
    if not Path(args.key_path).exists():
        logger.error(f"Private key not found: {args.key_path}")
        sys.exit(1)

    # Initialize components
    logger.info("🔌 Connecting to Tiger API...")
    data_fetcher = TigerDataFetcher(
        tiger_id=args.tiger_id,
        account_id=args.account_id,
        private_key_path=args.key_path,
        sandbox=args.sandbox,
    )

    trader = PaperTrader(
        tiger_id=args.tiger_id,
        account_id=args.account_id,
        private_key_path=args.key_path,
        sandbox=args.sandbox,
        max_position_size=MAX_POSITION_SIZE,
    )

    # Connect
    if not data_fetcher.connect():
        logger.error("Failed to connect data fetcher")
        sys.exit(1)

    if not trader.connect():
        logger.error("Failed to connect trader")
        sys.exit(1)

    logger.info("✅ Connected to Tiger API")

    # Start health server (needs trader & data_fetcher)
    start_health_server_in_thread(trader, data_fetcher)
    logger.info(f"🏥 Health server started on port {HEALTH_PORT}")

    # Initialize strategy
    strategy = create_strategy(args, data_fetcher, trader)
    if not strategy.initialize():
        logger.error("Strategy initialization failed")
        sys.exit(1)

    # Register callbacks for WebSocket
    if not args.no_websocket and WS_ENABLED:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
        data_fetcher.on_bar(strategy.on_bar)
        data_fetcher.on_quote(strategy.on_quote)
        data_fetcher.start_websocket(symbols)
        logger.info(f"📡 WebSocket started for {len(symbols)} symbols")

    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        cleanup_and_exit(data_fetcher, trader, logger)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Main loop
    logger.info("🚀 Bot is running. Press Ctrl+C to stop.")
    try:
        while True:
            # Periodic tasks (every 60 seconds)
            try:
                summary = trader.get_account_summary()
                nav = summary.get('net_liquidation', 0.0)
                daily_pnl = summary.get('daily_pnl', 0.0)
                cash = summary.get('cash_balance', 0.0)

                logger.info(
                    "Account update",
                    extra={
                        "event": "account_summary",
                        "net_liquidation": nav,
                        "cash_balance": cash,
                        "daily_pnl": daily_pnl,
                    }
                )

                # Update Prometheus metrics
                set_portfolio_value(nav)

                positions = trader.get_positions()
                update_all_position_risks(positions, MAX_POSITION_SIZE)

                # Log positions
                if positions:
                    for symbol, pos in positions.items():
                        logger.info(
                            "Position",
                            extra={
                                "event": "position",
                                "symbol": symbol,
                                "quantity": pos.quantity,
                                "avg_cost": pos.avg_cost,
                                "current_price": pos.current_price,
                                "unrealized_pnl": pos.unrealized_pnl,
                            }
                        )

            except Exception as e:
                logger.error("Status update failed", exc_info=True)

            time.sleep(60)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
        cleanup_and_exit(data_fetcher, trader, logger)


def cleanup_and_exit(data_fetcher, trader, logger):
    """Gracefully cancel open orders and disconnect."""
    logger.info("Cancelling all active orders...")
    try:
        active_orders = trader.get_active_orders()
        for order in active_orders:
            logger.info("Cancelling order", extra={"order_id": order.id, "symbol": order.symbol})
            trader.cancel_order(order.id)
    except Exception as e:
        logger.error("Error during order cleanup", exc_info=True)

    logger.info("Disconnecting from API...")
    data_fetcher.disconnect()
    trader.disconnect()
    logger.info("Shutdown complete")
    sys.exit(0)


if __name__ == "__main__":
    main()
