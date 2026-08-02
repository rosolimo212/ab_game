# coding: utf-8
"""Тесты текстов и UI-хелперов."""

from __future__ import annotations

from core.messages import button, clear_messages_cache, message
from core.models import AppResponse, GameSession, Screen, ZTestResult
from core.models import BranchSeries, DayPoint, RoundData
from ui.feedback_panel import format_feedback_stats
from ui.helpers import apply_response, build_payload, init_user_identity


def test_message_welcome_has_rounds() -> None:
    clear_messages_cache()
    text = message("welcome", "streamlit", rounds_total=20)
    assert "20" in text
    assert "зовут" in text.lower()


def test_buttons_exist() -> None:
    clear_messages_cache()
    assert button("continue") == "Далее"
    assert button("difficulty_easy")
    assert button("difficulty_hard")
    assert button("end_game") == "Закончить игру"
    assert button("guess_effect")
    assert button("restart")


def test_privacy_notice_exists() -> None:
    clear_messages_cache()
    text = message("privacy_notice", "streamlit")
    assert "персональн" in text.lower()


def test_apply_response_stores_game_and_name() -> None:
    state: dict = {}
    game = GameSession(round_index=1, rounds_per_session=20, user_name="Роман")
    apply_response(
        state,
        AppResponse(
            text="hi",
            buttons=["x"],
            screen=Screen.ROUND,
            game=game,
            user_name="Роман",
        ),
    )
    assert state["screen"] == Screen.ROUND.value
    assert state["game"] is game
    assert state["user_name"] == "Роман"


def test_build_payload_includes_game() -> None:
    game = GameSession(round_index=2, rounds_per_session=20)
    payload = build_payload(
        game=game, screen=Screen.FEEDBACK.value, user_name="Аня", text="hi"
    )
    assert payload["game"] is game
    assert payload["screen"] == "feedback"
    assert payload["user_name"] == "Аня"
    assert payload["text"] == "hi"


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


def test_feedback_panel_mentions_targets() -> None:
    round_data = RoundData(
        branch_a=BranchSeries("A", 0.1, (DayPoint(1, 10, 100),)),
        branch_b=BranchSeries("B", 0.2, (DayPoint(1, 20, 100),)),
        has_effect=True,
        base_p=0.1,
    )
    z = ZTestResult(
        p_value=0.01,
        z_stat=2.0,
        significant=True,
        alpha=0.05,
        successes_a=10,
        trials_a=100,
        successes_b=20,
        trials_b=100,
        rate_a=0.1,
        rate_b=0.2,
    )
    text = format_feedback_stats(round_data, z)
    assert "целевое" in text
    assert "фактическое" in text
    assert "10.00%" in text
    assert "20.00%" in text
    assert "%" in text
