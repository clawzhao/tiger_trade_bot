"""
Tiger Trade Bot - Main Entry Point

Usage:
    python -m tiger_trade_bot --strategy gap --symbols AAPL,TSLA
    python -m tiger_trade_bot --strategy ma --symbols AAPL --fast 10 --slow 50
"""

import argparse
import logging
import sys
import time
import signal
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
)
from .data import TigerDataFetcher
from .trader import PaperTrader
from .strategies import GapTradingStrategy, MovingAverageCrossoverStrategy, TradeSignal


def setup_logging(log_level: str = LOG_LEVEL, log_dir: str = LOG_DIR):
    """Configure structured logging with rotation to file and console."""
    import logging.handlers

    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(exist_ok=True)

    log_file = log_dir_path / f"bot_{datetime.now().strftime('%Y-%m-%d')}.log"

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Use a structured format, e.g. adding module and line number
    formatter = logging.Formatter(
        "%(asctime)s - [%(levelname)s] - %(name)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Rotating File handler (10 MB per file, keep last 5 files)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers if re-configured
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger


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
    logger = setup_logging()

    logger.info("=" * 60)
    logger.info("🐯📈 Tiger Trade Bot Starting")
    logger.info("=" * 60)
    logger.info(f"Strategy: {args.strategy}")
    logger.info(f"Symbols: {args.symbols}")
    logger.info(f"Sandbox mode: {args.sandbox}")
    logger.info(f"WebSocket: {not args.no_websocket}")

    # Validate credentials
    if args.tiger_id == "YOUR_TIGER_ID":
        logger.error("❌ Please set your Tiger ID in config.py or via --tiger-id")
        sys.exit(1)
    if args.account_id == "YOUR_PAPER_ACCOUNT_ID":
        logger.error("❌ Please set your Account ID in config.py or via --account-id")
        sys.exit(1)
    if not Path(args.key_path).exists():
        logger.error(f"❌ Private key not found: {args.key_path}")
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
    )

    # Connect
    if not data_fetcher.connect():
        logger.error("❌ Failed to connect data fetcher")
        sys.exit(1)

    if not trader.connect():
        logger.error("❌ Failed to connect trader")
        sys.exit(1)

    # Initialize strategy
    strategy = create_strategy(args, data_fetcher, trader)
    if not strategy.initialize():
        logger.error("❌ Strategy initialization failed")
        sys.exit(1)

    # Register callbacks for WebSocket
    if not args.no_websocket and WS_ENABLED:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
        data_fetcher.on_bar(strategy.on_bar)
        data_fetcher.on_quote(strategy.on_quote)
        data_fetcher.start_websocket(symbols)
        logger.info(f"📡 WebSocket started for {len(symbols)} symbols")

    def signal_handler(sig, frame):
        logger.info(f"\n🛑 Received signal {sig}, shutting down...")
        cleanup_and_exit(data_fetcher, trader, logger)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Main loop
    logger.info("🚀 Bot is running. Press Ctrl+C to stop.")
    try:
        while True:
            # Periodic tasks (every 60 seconds)
            # - Print status
            # - Refresh positions
            # - Check for filled orders

            try:
                summary = trader.get_account_summary()
                logger.info(
                    f"💰 Account: Nav=${summary['net_liquidation']:.2f}, "
                    f"Cash=${summary['cash_balance']:.2f}, "
                    f"DayP&L=${summary['daily_pnl']:.2f}"
                )

                positions = trader.get_open_positions()
                if positions:
                    logger.info(f"📊 Positions:")
                    for pos in positions.values():
                        logger.info(
                            f"   {pos.symbol}: {pos.quantity} @ ${pos.avg_cost:.2f} "
                            f"(P&L: ${pos.unrealized_pnl:.2f})"
                        )

            except Exception as e:
                logger.error(f"Error in status update: {e}")

            time.sleep(60)

    except KeyboardInterrupt:
        logger.info("\n🛑 Keyboard interrupt received, shutting down...")
        cleanup_and_exit(data_fetcher, trader, logger)


def cleanup_and_exit(data_fetcher, trader, logger):
    """Gracefully cancel open orders and disconnect."""
    logger.info("🧹 Cancelling all active orders...")
    try:
        active_orders = trader.get_active_orders()
        for order in active_orders:
            logger.info(f"Cancelling order {order.id} for {order.symbol}...")
            trader.cancel_order(order.id)
    except Exception as e:
        logger.error(f"Error during order cleanup: {e}")

    logger.info("Disconnecting from API...")
    data_fetcher.disconnect()
    trader.disconnect()
    logger.info("✅ Shutdown complete")
    sys.exit(0)


if __name__ == "__main__":
    main()
