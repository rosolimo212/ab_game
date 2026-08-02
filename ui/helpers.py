# coding: utf-8
"""
Общие функции для UI-клиентов.

Цель:
    Связать session state с AppService: identity, payload, AppResponse.
"""

from __future__ import annotations

from typing import Any

from core.identity import new_external_user_id
from core.models import AppResponse, GameSession, UserIdentity


def build_payload(
    *,
    game: GameSession | None = None,
    screen: str | None = None,
) -> dict[str, Any]:
    """Контекст шага для handle_action."""
    payload: dict[str, Any] = {}
    if game is not None:
        payload["game"] = game
    if screen is not None:
        payload["screen"] = screen
    return payload


def apply_response(state: dict[str, Any], response: AppResponse) -> None:
    """Записывает AppResponse в session state."""
    state["last_text"] = response.text
    state["screen"] = response.screen.value
    state["buttons"] = list(response.buttons)
    state["finished"] = bool(response.finished)
    state["game"] = response.game


def store_identity(state: dict[str, Any], identity: UserIdentity) -> None:
    """Сохраняет UserIdentity в session state."""
    state["user_id"] = identity.user_id
    state["internal_user_id"] = identity.internal_user_id
    state["external_user_id"] = identity.external_user_id


def get_identity(state: dict[str, Any]) -> UserIdentity:
    """Восстанавливает UserIdentity из session state."""
    return UserIdentity(
        user_id=str(state["user_id"]),
        internal_user_id=int(state["internal_user_id"]),
        external_user_id=str(state["external_user_id"]),
    )


def init_user_identity(service: Any, state: dict[str, Any], channel: str) -> UserIdentity:
    """Один external_user_id на сессию → одна строка users."""
    if (
        state.get("user_id")
        and state.get("internal_user_id") is not None
        and state.get("external_user_id")
    ):
        return get_identity(state)

    if not state.get("external_user_id"):
        state["external_user_id"] = new_external_user_id(channel)

    identity = service.logger.ensure_user(channel, str(state["external_user_id"]))
    store_identity(state, identity)
    return identity
