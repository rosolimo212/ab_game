# coding: utf-8
"""Тесты текстов и UI-хелперов."""

from __future__ import annotations

from core.messages import button, clear_messages_cache, message
from core.models import AppResponse, GameSession, Screen
from ui.helpers import apply_response, build_payload, init_user_identity


def test_message_welcome_has_rounds() -> None:
    clear_messages_cache()
    text = message("welcome", "streamlit", rounds_total=20)
    assert "20" in text
    assert "z-тест" in text.lower() or "Z-тест" in text


def test_buttons_exist() -> None:
    clear_messages_cache()
    assert button("start") == "Начать"
    assert button("guess_effect")
    assert button("guess_no_effect")
    assert button("next_round")
    assert button("restart")


def test_apply_response_stores_game() -> None:
    state: dict = {}
    game = GameSession(round_index=1, rounds_per_session=20)
    apply_response(
        state,
        AppResponse(
            text="hi",
            buttons=["x"],
            screen=Screen.ROUND,
            game=game,
        ),
    )
    assert state["screen"] == Screen.ROUND.value
    assert state["game"] is game
    assert state["buttons"] == ["x"]


def test_build_payload_includes_game() -> None:
    game = GameSession(round_index=2, rounds_per_session=20)
    payload = build_payload(game=game, screen=Screen.FEEDBACK.value)
    assert payload["game"] is game
    assert payload["screen"] == "feedback"


def test_init_user_identity_stable() -> None:
    class _Svc:
        class logger:
            @staticmethod
            def ensure_user(channel, external_user_id):
                from core.identity import make_user_id
                from core.models import UserIdentity

                return UserIdentity(
                    make_user_id(channel, external_user_id), 1, external_user_id
                )

    state: dict = {"external_user_id": "fixed-uuid"}
    first = init_user_identity(_Svc(), state, "streamlit")
    second = init_user_identity(_Svc(), state, "streamlit")
    assert first.user_id == second.user_id
    assert first.external_user_id == "fixed-uuid"
