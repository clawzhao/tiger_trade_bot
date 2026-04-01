"""
End-to-End test simulating bot startup and main loop.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import asyncio
import threading
import time
import sys

from tiger_trade_bot.bot import main, parse_args, create_strategy
from tiger_trade_bot.trader import PaperTrader
from tiger_trade_bot.data import TigerDataFetcher
from tiger_trade_bot.strategies import GapTradingStrategy


@pytest.fixture
def mock_all_dependencies():
    """Comprehensive mocks for all external components."""
    import types

    with patch("tiger_trade_bot.bot.setup_logging") as mock_logging, \
         patch("tiger_trade_bot.bot.start_metrics_server") as mock_metrics, \
         patch("tiger_trade_bot.bot.start_health_server_in_thread") as mock_health, \
         patch("tiger_trade_bot.bot.TigerDataFetcher") as mock_data_cls, \
         patch("tiger_trade_bot.bot.PaperTrader") as mock_trader_cls, \
         patch("tiger_trade_bot.bot.validate_config") as mock_validate, \
         patch("tiger_trade_bot.bot.parse_args") as mock_parse_args, \
         patch("tiger_trade_bot.bot.time.sleep", side_effect=KeyboardInterrupt), \
         patch("sys.exit") as mock_exit, \
         patch("tiger_trade_bot.bot.Path") as MockPath:

        # Mock Path to always say key file exists
        mock_path_instance = MockPath.return_value
        mock_path_instance.exists.return_value = True

        # Mock parse_args to return a namespace with sensible defaults
        args = types.SimpleNamespace(
            strategy="gap",
            symbols="AAPL,TSLA",
            sandbox=True,
            tiger_id="TEST_TIGER_ID",
            account_id="TEST_ACCOUNT_ID",
            key_path="./keys/rsa_private_key.pem",
            no_websocket=False,
            gap_threshold=0.02,
            fast=10,
            slow=50,
        )
        mock_parse_args.return_value = args

        # Mock logger
        mock_logger = MagicMock()
        mock_logging.return_value = mock_logger

        # Mock data fetcher instance
        mock_data = MagicMock()
        mock_data.connect.return_value = True
        mock_data_cls.return_value = mock_data

        # Mock trader instance
        mock_trader = MagicMock()
        mock_trader.connect.return_value = True
        mock_trader.is_connected.return_value = True
        mock_trader.get_account_summary.return_value = {
            "net_liquidation": 100000.0,
            "cash_balance": 50000.0,
            "daily_pnl": 0.0,
        }
        mock_trader.get_positions.return_value = {}
        mock_trader_cls.return_value = mock_trader

        # Mock strategy
        mock_strategy = MagicMock()
        mock_strategy.initialize.return_value = True
        mock_strategy.on_bar = MagicMock()
        mock_strategy.on_quote = MagicMock()

        def create_strategy_impl(args, data_fetcher, trader):
            return mock_strategy
        with patch("tiger_trade_bot.bot.create_strategy", side_effect=create_strategy_impl):
            yield {
                "logger": mock_logger,
                "metrics": mock_metrics,
                "health": mock_health,
                "data": mock_data,
                "trader": mock_trader,
                "strategy": mock_strategy,
                "validate_config": mock_validate,
                "parse_args": mock_parse_args,
                "exit": mock_exit,
            }


def test_bot_main_successful_startup_and_shutdown(mock_all_dependencies):
    """Test that bot.main() initializes all services and shuts down cleanly."""
    # Running main; time.sleep will raise KeyboardInterrupt quickly, triggering cleanup
    main()

    m = mock_all_dependencies

    # Verify logging setup
    m["logger"].info.assert_any_call("🐯📈 Tiger Trade Bot Starting")

    # Verify metrics and health servers started
    m["metrics"].assert_called_once()
    m["health"].assert_called_once()

    # Validate configuration was called
    m["validate_config"].assert_called_once()

    # Verifies connect called
    m["data"].connect.assert_called_once()
    m["trader"].connect.assert_called_once()

    # Verify strategy initialized
    m["strategy"].initialize.assert_called_once()

    # Finally, sys.exit(0) called after cleanup
    m["exit"].assert_called_with(0)
