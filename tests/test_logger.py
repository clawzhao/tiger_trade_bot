"""
Tests for structured JSON logger.
"""

import json
import logging
from io import StringIO

from tiger_trade_bot.logger import JsonFormatter, setup_logging


def test_json_formatter_output():
    """Test JsonFormatter produces valid JSON with required fields."""
    formatter = JsonFormatter()

    # Create a log record
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Test message",
        args=(),
        exc_info=None,
    )

    # Format the record
    output = formatter.format(record)

    # Parse JSON
    parsed = json.loads(output)

    # Required fields
    assert "timestamp" in parsed
    assert "level" in parsed
    assert parsed["level"] == "INFO"
    assert "logger" in parsed and parsed["logger"] == "test.logger"
    assert "module" in parsed
    assert "function" in parsed
    assert "line" in parsed
    assert "message" in parsed
    # message field should contain our message by default
    # Actually our formatter uses %(message)s in format string, but JsonFormatter adds 'message' separately
    # Let's check if 'message' or 'msg' is used. In JsonFormatter, we call super().add_fields which puts 'message' key from record.getMessage()
    assert parsed["message"] == "Test message"


def test_json_formatter_with_exception():
    """Test JsonFormatter includes exception info."""
    formatter = JsonFormatter()

    try:
        raise ValueError("test error")
    except ValueError:
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname=__file__,
            lineno=10,
            msg="Error occurred",
            args=(),
            exc_info=True,  # Simulate logging.exception
        )

    output = formatter.format(record)
    parsed = json.loads(output)

    assert "exception" in parsed
    assert parsed["exception"]["type"] == "ValueError"
    assert parsed["exception"]["message"] == "test error"
    assert isinstance(parsed["exception"]["traceback"], list)


def test_json_formatter_with_extra_fields():
    """Test JsonFormatter includes extra fields from record."""
    formatter = JsonFormatter()

    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Trade executed",
        args=(),
        exc_info=None,
    )
    # Add extra fields
    record.symbol = "AAPL"
    record.order_id = "12345"

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["symbol"] == "AAPL"
    assert parsed["order_id"] == "12345"


def test_setup_logging_creates_handlers(tmp_path):
    """Test setup_logging configures root logger with handlers."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    logger = setup_logging(log_level="DEBUG", log_dir=str(log_dir))

    # Root logger should have handlers (file and console)
    assert len(logger.handlers) >= 1

    # Test that we can log a message
    test_msg = "Test log message"
    logger.info(test_msg, extra={"test": "value"})

    # Find log file
    log_files = list(log_dir.glob("bot_*.log"))
    assert len(log_files) == 1
    log_content = log_files[0].read_text()

    # Check that JSON line contains our message
    found = False
    for line in log_content.splitlines():
        if line.strip():
            data = json.loads(line)
            if data.get("message") == test_msg:
                found = True
                break
    assert found, f"Test message not found in log output: {log_content}"
