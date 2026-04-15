"""Logging configuration utility."""

import logging
import os
import sys


def setup_logger(name: str = "trade-engine", level: str | None = None) -> logging.Logger:
    """Configure and return a logger with standard formatting.

    Args:
        name: Logger name.
        level: Log level string (DEBUG, INFO, WARNING, ERROR). Defaults to
               LOG_LEVEL environment variable or INFO.

    Returns:
        Configured logger instance.
    """
    log_level = level or os.environ.get("LOG_LEVEL", "INFO").upper()

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(getattr(logging, log_level, logging.INFO))
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
