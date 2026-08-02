# coding: utf-8
"""
Идентификаторы пользователя.

user_id — sha256(channel:external_user_id), PK в БД.
internal_user_id — инкремент (sequence / локальный счётчик).
external_user_id — id канала (uuid streamlit-сессии и т.д.).
"""

from __future__ import annotations

import hashlib
import uuid


def make_user_id(channel: str, external_user_id: str) -> str:
    """
    Стабильный user_id из канала и внешнего id.

    :param channel: streamlit | telegram | console
    :param external_user_id: id сессии/пользователя в канале
    :return: hex sha256
    """
    raw = f"{channel}:{external_user_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_external_user_id(channel: str) -> str:
    """Новый uuid для каналов без встроенного user id."""
    _ = channel
    return str(uuid.uuid4())
