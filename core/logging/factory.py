# coding: utf-8
"""Фабрика логгера по app.logging_enabled."""

from __future__ import annotations

from typing import Any

from core.logging.base import EventLogger
from core.logging.noop import NoopLogger
from core.logging.postgres import PostgresLogger


def build_logger(config: dict[str, Any]) -> EventLogger:
    """postgres при logging_enabled, иначе noop."""
    if config["app"].get("logging_enabled"):
        return PostgresLogger(config["logging"])
    return NoopLogger()
