"""Logging configuration."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from stock_simulator.utils.paths import get_logs_dir


def setup_logging(username: str | None = None) -> None:
    """Configure application and optional per-user loggers."""
    logs_dir = get_logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    root_logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    app_handler = RotatingFileHandler(
        logs_dir / "stock_simulator.log",
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    app_handler.setFormatter(formatter)
    root_logger.addHandler(app_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    if username:
        user_log_dir = logs_dir / "users"
        user_log_dir.mkdir(parents=True, exist_ok=True)
        user_handler = RotatingFileHandler(
            user_log_dir / f"{username}.log",
            maxBytes=500_000,
            backupCount=2,
            encoding="utf-8",
        )
        user_handler.setFormatter(formatter)
        logging.getLogger(f"user.{username}").addHandler(user_handler)
