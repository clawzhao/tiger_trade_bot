"""
Structured JSON logging setup for Tiger Trade Bot.

Uses python-json-logger to output logs in JSON format with consistent fields.
"""

import json
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from pythonjsonlogger import jsonlogger


class JsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any]
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        # Ensure timestamp is in ISO format
        if "asctime" in log_record:
            log_record["timestamp"] = log_record.pop("asctime")
        else:
            log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"

        # Add standard fields
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "getMessage",
                "asctime"
            ):
                log_record[key] = value


def setup_logging(log_level: str = "INFO", log_dir: str = "./logs") -> logging.Logger:
    """Configure JSON logging with rotation to file and console.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory to store log files

    Returns:
        Root logger instance
    """
    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(exist_ok=True)

    log_file = log_dir_path / f"bot_{datetime.now().strftime('%Y-%m-%d')}.log"

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    formatter = JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        json_ensure_ascii=False
    )

    # Rotating file handler (10 MB per file, keep last 5)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)

    # Console handler - output JSON lines
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return root_logger
