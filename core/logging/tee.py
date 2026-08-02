# coding: utf-8
"""
Обёртка логгера: дублирует события в список (для debug_mode в UI).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from core.logging.base import EventLogger
from core.models import UserIdentity


class TeeEventLogger(EventLogger):
    """Проксирует вызовы во внутренний логгер и копирует log_event в sink."""

    def __init__(self, inner: EventLogger, sink: list[dict[str, Any]]) -> None:
        self._inner = inner
        self._sink = sink

    def ensure_user(self, channel: str, external_user_id: str) -> UserIdentity:
        return self._inner.ensure_user(channel, external_user_id)

    def upsert_user(
        self,
        identity: UserIdentity,
        user_name: str,
        registration_date: datetime,
        registration_channel: str,
        last_active_at: datetime,
        is_paid: bool = False,
        is_trial: bool = False,
        is_active: bool = True,
    ) -> None:
        self._inner.upsert_user(
            identity,
            user_name,
            registration_date,
            registration_channel,
            last_active_at,
            is_paid=is_paid,
            is_trial=is_trial,
            is_active=is_active,
        )

    def log_event(
        self,
        identity: UserIdentity,
        event_name: str,
        channel: str,
        event_parameters: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        self._inner.log_event(
            identity=identity,
            event_name=event_name,
            channel=channel,
            event_parameters=event_parameters,
            timestamp=timestamp,
        )
        self._sink.append(
            {
                "event_name": event_name,
                "channel": channel,
                "event_parameters": event_parameters,
                "external_user_id": identity.external_user_id,
            }
        )

    def get_user_profile(self, identity: UserIdentity) -> dict[str, Any] | None:
        return self._inner.get_user_profile(identity)
