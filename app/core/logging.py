"""Structured JSON logging for MindScope.

Configures Python's logging module to emit JSON lines compatible with
CloudWatch Logs Insights queries.

Every entry includes: timestamp, level, logger, message.
Entries with session_id/user_id context use the LogContext helper.

CloudWatch Log Groups:
  /mindscope/api      — application logs
  /mindscope/bedrock  — LLM call logs (set logger name to "mindscope.bedrock")

Usage:
    from app.core.logging import setup_logging, get_logger
    setup_logging()                           # called once in main.py
    logger = get_logger(__name__)             # in each module
    logger.info("Session created", extra={"session_id": sid, "user_id": uid})
"""
import json
import logging
import sys
import traceback
from typing import Optional


class _JsonFormatter(logging.Formatter):
    """Formats each LogRecord as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Propagate structured fields injected via extra={}
        for key in ("session_id", "user_id", "model", "stage", "latency_ms", "token_count"):
            val = getattr(record, key, None)
            if val is not None:
                entry[key] = val

        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(entry, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with JSON formatter.

    Call once at application startup (main.py lifespan or module level).
    Safe to call multiple times — idempotent.
    """
    root = logging.getLogger()
    if any(isinstance(h, logging.StreamHandler) and isinstance(h.formatter, _JsonFormatter)
           for h in root.handlers):
        return  # already configured

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())

    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Quiet noisy third-party loggers
    for noisy in ("uvicorn.access", "sqlalchemy.engine", "botocore", "boto3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Use `__name__` as the name."""
    return logging.getLogger(name)
