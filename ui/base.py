# coding: utf-8
"""Сборка AppService из конфига."""

from __future__ import annotations

from typing import Any

from core.app import AppService
from core.logging.factory import build_logger


def build_app_service(config: dict[str, Any]) -> AppService:
    """Собирает AppService с логгером по флагам конфига."""
    logger = build_logger(config)
    return AppService(logger=logger, config=config)
