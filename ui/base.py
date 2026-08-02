# coding: utf-8
"""Сборка AppService из конфига."""

from __future__ import annotations

from typing import Any

from core.app import AppService
from core.logging.factory import build_logger
from core.logging.tee import TeeEventLogger


def build_app_service(
    config: dict[str, Any],
    *,
    event_sink: list[dict[str, Any]] | None = None,
) -> AppService:
    """
    Собирает AppService с логгером по флагам конфига.

    :param event_sink: если задан (debug_mode) — события дублируются в список для UI
    """
    logger = build_logger(config)
    if event_sink is not None:
        logger = TeeEventLogger(logger, event_sink)
    return AppService(logger=logger, config=config)
