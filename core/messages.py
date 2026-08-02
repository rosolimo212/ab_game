# coding: utf-8
"""
Тексты диалогов с пользователем (data/dialog_messages.json).

Цель:
    Единый каталог всех user-facing строк: экраны, кнопки, панель метрик,
    подписи графика и hover. Править JSON, не хардкодить в UI/brain.

Вход:
    name сообщения/кнопки, опционально channel.

Выход:
    Строка для показа. Пустое поле канала в JSON → default.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_MESSAGES_PATH = Path(__file__).resolve().parents[1] / "data" / "dialog_messages.json"

CHANNEL_TO_UI_KEY = {
    "console": "console",
    "telegram": "telegram",
    "streamlit": "browser",
}


@lru_cache(maxsize=1)
def _load_catalog(path: str | None = None) -> dict[str, Any]:
    file_path = Path(path) if path else DEFAULT_MESSAGES_PATH
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _resolve_channel_key(channel: str | None) -> str | None:
    if channel is None:
        return None
    return CHANNEL_TO_UI_KEY.get(channel, channel)


def _pick_text(entry: dict[str, Any], channel: str | None) -> str:
    ui_key = _resolve_channel_key(channel)
    if ui_key:
        override = str(entry.get(ui_key, "") or "").strip()
        if override:
            return override
    return str(entry["default"])


def _find_by_name(section: str, name: str, path: str | None = None) -> dict[str, Any]:
    catalog = _load_catalog(path)
    for item in catalog.get(section, []):
        if item.get("name") == name:
            return item
    raise KeyError(f"Не найден {section} name={name!r} в dialog_messages.json")


def message(
    name: str,
    channel: str | None = None,
    *,
    path: str | None = None,
    **placeholders: Any,
) -> str:
    """Текст сообщения по имени с подстановками {round_index}, {accuracy}, …"""
    entry = _find_by_name("messages", name, path)
    text = _pick_text(entry, channel)
    if placeholders:
        text = text.format(**placeholders)
    return text


def button(
    name: str,
    channel: str | None = None,
    *,
    path: str | None = None,
) -> str:
    """Текст кнопки по имени."""
    entry = _find_by_name("buttons", name, path)
    return _pick_text(entry, channel)


def clear_messages_cache() -> None:
    """Сброс кэша каталога (для тестов)."""
    _load_catalog.cache_clear()
