# coding: utf-8
"""Тесты AppService — игровой сценарий MVP."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from core.app import AppService
from core.config import load_app_config
from core.identity import make_user_id
from core.logging.base import EventLogger
from core.models import (
    ACTION_GUESS_EFFECT,
    ACTION_GUESS_NO_EFFECT,
    ACTION_NEXT_ROUND,
    ACTION_RESTART,
    ACTION_START_SESSION,
    Screen,
    UserIdentity,
)


class FakeLogger(EventLogger):
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.users: dict[str, dict[str, Any]] = {}
        self._counter = 0

    def ensure_user(self, channel: str, external_user_id: str) -> UserIdentity:
        user_id = make_user_id(channel, external_user_id)
        if user_id in self.users:
            row = self.users[user_id]
            return UserIdentity(user_id, row["internal_user_id"], external_user_id)
        self._counter += 1
        self.users[user_id] = {
            "internal_user_id": self._counter,
            "external_user_id": external_user_id,
            "user_name": "",
            "registration_date": datetime.now(),
        }
        return UserIdentity(user_id, self._counter, external_user_id)

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
        self.users[identity.user_id] = {
            "internal_user_id": identity.internal_user_id,
            "external_user_id": identity.external_user_id,
            "user_name": user_name,
            "registration_date": registration_date,
            "registration_channel": registration_channel,
            "last_active_at": last_active_at,
            "is_paid": is_paid,
            "is_trial": is_trial,
            "is_active": is_active,
        }

    def log_event(
        self,
        identity: UserIdentity,
        event_name: str,
        channel: str,
        event_parameters: dict[str, Any] | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        self.events.append(
            {
                "user_id": identity.user_id,
                "event_name": event_name,
                "channel": channel,
                "event_parameters": event_parameters,
            }
        )

    def get_user_profile(self, identity: UserIdentity) -> dict[str, Any] | None:
        row = self.users.get(identity.user_id)
        if row is None:
            return None
        return {
            "user_name": str(row.get("user_name", "")),
            "registration_date": row.get("registration_date"),
        }


def _game_config(rounds: int = 3) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    cfg = load_app_config(root / "settings.yaml", None)
    cfg["game"] = dict(cfg["game"])
    cfg["game"]["rounds_per_session"] = rounds
    return cfg


def _make_service(rounds: int = 3) -> tuple[AppService, FakeLogger]:
    logger = FakeLogger()
    service = AppService(
        logger=logger,
        config=_game_config(rounds),
        rng=np.random.default_rng(42),
    )
    return service, logger


def test_handle_start_welcome() -> None:
    service, logger = _make_service()
    identity = logger.ensure_user("streamlit", "ext-1")
    resp = service.handle_start(identity, "streamlit")
    assert resp.screen == Screen.START
    assert resp.game is None
    assert logger.events[0]["event_name"] == "start_screen_visit"
    assert identity.user_id in logger.users


def test_full_short_session_flow() -> None:
    service, logger = _make_service(rounds=2)
    channel = "streamlit"
    identity = logger.ensure_user(channel, "ext-flow")

    start = service.handle_start(identity, channel)
    assert start.screen == Screen.START

    round1 = service.handle_action(identity, channel, ACTION_START_SESSION, {})
    assert round1.screen == Screen.ROUND
    assert round1.game is not None
    assert round1.game.round_index == 1
    assert round1.game.round_data is not None

    fb1 = service.handle_action(
        identity,
        channel,
        ACTION_GUESS_EFFECT,
        {"game": round1.game},
    )
    assert fb1.screen == Screen.FEEDBACK
    assert fb1.game is not None
    assert fb1.game.last_round_score is not None
    assert fb1.game.last_z_result is not None
    assert len(fb1.game.round_scores) == 1

    round2 = service.handle_action(
        identity, channel, ACTION_NEXT_ROUND, {"game": fb1.game}
    )
    assert round2.screen == Screen.ROUND
    assert round2.game is not None
    assert round2.game.round_index == 2

    fb2 = service.handle_action(
        identity,
        channel,
        ACTION_GUESS_NO_EFFECT,
        {"game": round2.game},
    )
    assert fb2.screen == Screen.FEEDBACK

    summary = service.handle_action(
        identity, channel, ACTION_NEXT_ROUND, {"game": fb2.game}
    )
    assert summary.screen == Screen.SUMMARY
    assert summary.finished is True
    assert summary.game is not None
    assert summary.game.session_score is not None
    assert summary.game.session_score.n_rounds == 2

    names = [e["event_name"] for e in logger.events]
    assert "session_start" in names
    assert names.count("round_shown") == 2
    assert names.count("guess_submitted") == 2
    assert "game_finished" in names
    assert "button_start" in names
    assert "button_guess_effect" in names
    assert "button_guess_no_effect" in names
    assert "button_next_round" in names

    shown = [e for e in logger.events if e["event_name"] == "round_shown"]
    params = shown[0]["event_parameters"] or {}
    assert "noise" in params
    assert "mean_a" in params
    assert "mean_b" in params
    assert "p_value" in params

    guesses = [e for e in logger.events if e["event_name"] == "guess_submitted"]
    assert guesses[0]["event_parameters"]["user_answer"] == "effect"
    assert guesses[1]["event_parameters"]["user_answer"] == "no_effect"


def test_restart_starts_new_session() -> None:
    service, logger = _make_service(rounds=1)
    identity = logger.ensure_user("streamlit", "ext-restart")
    service.handle_start(identity, "streamlit")
    r1 = service.handle_action(identity, "streamlit", ACTION_START_SESSION, {})
    fb = service.handle_action(
        identity, "streamlit", ACTION_GUESS_EFFECT, {"game": r1.game}
    )
    summary = service.handle_action(
        identity, "streamlit", ACTION_NEXT_ROUND, {"game": fb.game}
    )
    assert summary.screen == Screen.SUMMARY

    again = service.handle_action(
        identity, "streamlit", ACTION_RESTART, {"game": summary.game}
    )
    assert again.screen == Screen.ROUND
    assert again.game is not None
    assert again.game.round_index == 1
    assert again.game.round_scores == ()


def test_guess_without_game_raises() -> None:
    service, logger = _make_service()
    identity = logger.ensure_user("streamlit", "ext-err")
    with pytest.raises(ValueError, match="game"):
        service.handle_action(identity, "streamlit", ACTION_GUESS_EFFECT, {})
