# coding: utf-8
"""
AppService — оркестратор игрового сценария.

Цель:
    Единая точка входа для Streamlit (и позже других UI):
    старт сессии → раунд → догадка → фидбек → итог.

Поток:
    UI → handle_start / handle_action(identity, channel, action, payload)
    → generator / stats / scoring / brain → AppResponse (+ GameSession в response.game).

Состояние игры передаётся через payload["game"] (из session_state), потому что
Streamlit пересоздаёт AppService на каждый rerun.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np

from core.brain import on_feedback, on_round, on_summary, on_welcome
from core.generator import generate_round
from core.logging.base import EventLogger
from core.models import (
    ACTION_GUESS_EFFECT,
    ACTION_GUESS_NO_EFFECT,
    ACTION_NEXT_ROUND,
    ACTION_RESTART,
    ACTION_START_SESSION,
    AppResponse,
    GameSession,
    UserIdentity,
)
from core.scoring import score_round, score_session
from core.stats import z_test_round


class AppService:
    """Единая точка входа бизнес-логики ab_game."""

    def __init__(
        self,
        logger: EventLogger,
        config: dict[str, Any],
        rng: np.random.Generator | None = None,
    ) -> None:
        self.logger = logger
        self.config = config
        self.rng = rng if rng is not None else np.random.default_rng()

    def _resolve_identity(
        self, identity: UserIdentity, channel: str
    ) -> UserIdentity:
        return self.logger.ensure_user(channel, identity.external_user_id)

    def _game_cfg(self) -> dict[str, Any]:
        return self.config["game"]

    def _alpha(self) -> float:
        return float(self._game_cfg()["alpha"])

    def _rounds_per_session(self) -> int:
        return int(self._game_cfg()["rounds_per_session"])

    def handle_start(
        self,
        identity: UserIdentity,
        channel: str,
        context: dict[str, Any] | None = None,
    ) -> AppResponse:
        """Первый визит: приветствие, без старта раундов."""
        _ = context
        identity = self._resolve_identity(identity, channel)
        self._ensure_user_stub(identity, channel)
        self.logger.log_event(
            identity=identity,
            event_name="start_screen_visit",
            channel=channel,
            event_parameters=None,
        )
        return on_welcome(channel, self._rounds_per_session())

    def handle_action(
        self,
        identity: UserIdentity,
        channel: str,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> AppResponse:
        payload = payload or {}
        identity = self._resolve_identity(identity, channel)
        self._touch_user(identity, channel)

        if action in (ACTION_START_SESSION, ACTION_RESTART):
            return self._start_session(identity, channel)

        if action == ACTION_GUESS_EFFECT:
            return self._handle_guess(identity, channel, payload, True)

        if action == ACTION_GUESS_NO_EFFECT:
            return self._handle_guess(identity, channel, payload, False)

        if action == ACTION_NEXT_ROUND:
            return self._handle_next(identity, channel, payload)

        return on_welcome(channel, self._rounds_per_session())

    def _ensure_user_stub(self, identity: UserIdentity, channel: str) -> None:
        now = datetime.now()
        self.logger.upsert_user(
            identity=identity,
            user_name="",
            registration_date=now,
            registration_channel=channel,
            last_active_at=now,
        )

    def _touch_user(self, identity: UserIdentity, channel: str) -> None:
        now = datetime.now()
        profile = self.logger.get_user_profile(identity) or {}
        reg = profile.get("registration_date")
        if not isinstance(reg, datetime):
            reg = now
        self.logger.upsert_user(
            identity=identity,
            user_name=str(profile.get("user_name") or ""),
            registration_date=reg,
            registration_channel=channel,
            last_active_at=now,
        )

    def _start_session(
        self, identity: UserIdentity, channel: str
    ) -> AppResponse:
        rounds_total = self._rounds_per_session()
        round_data = generate_round(self._game_cfg(), rng=self.rng)
        game = GameSession(
            round_index=1,
            rounds_per_session=rounds_total,
            round_data=round_data,
            round_scores=(),
        )
        self.logger.log_event(
            identity=identity,
            event_name="session_start",
            channel=channel,
            event_parameters={"rounds_per_session": rounds_total},
        )
        self.logger.log_event(
            identity=identity,
            event_name="round_shown",
            channel=channel,
            event_parameters={"round_index": 1},
        )
        return on_round(channel, game)

    def _require_game(self, payload: dict[str, Any]) -> GameSession:
        game = payload.get("game")
        if not isinstance(game, GameSession):
            raise ValueError("В payload нужен game: GameSession")
        return game

    def _handle_guess(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
        guess_has_effect: bool,
    ) -> AppResponse:
        game = self._require_game(payload)
        if game.round_data is None:
            raise ValueError("Нет round_data для догадки")

        z_result = z_test_round(game.round_data, alpha=self._alpha())
        round_score = score_round(guess_has_effect, z_result)
        updated = GameSession(
            round_index=game.round_index,
            rounds_per_session=game.rounds_per_session,
            round_data=game.round_data,
            round_scores=game.round_scores + (round_score,),
            last_z_result=z_result,
            last_round_score=round_score,
            session_score=None,
        )
        self.logger.log_event(
            identity=identity,
            event_name="guess_submitted",
            channel=channel,
            event_parameters={
                "round_index": updated.round_index,
                "guess_has_effect": guess_has_effect,
                "test_significant": z_result.significant,
                "points": round_score.points,
                "p_value": z_result.p_value,
            },
        )
        return on_feedback(channel, updated)

    def _handle_next(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        game = self._require_game(payload)
        if len(game.round_scores) < game.round_index:
            raise ValueError("Нельзя перейти дальше без догадки в текущем раунде")

        if game.round_index >= game.rounds_per_session:
            session_score = score_session(game.round_scores, alpha=self._alpha())
            finished = GameSession(
                round_index=game.round_index,
                rounds_per_session=game.rounds_per_session,
                round_data=None,
                round_scores=game.round_scores,
                last_z_result=game.last_z_result,
                last_round_score=game.last_round_score,
                session_score=session_score,
            )
            self.logger.log_event(
                identity=identity,
                event_name="session_finished",
                channel=channel,
                event_parameters={
                    "n_correct": session_score.n_correct,
                    "n_rounds": session_score.n_rounds,
                    "accuracy": session_score.accuracy,
                    "ci_low": session_score.ci_low,
                    "ci_high": session_score.ci_high,
                    "p_value": session_score.p_value,
                    "significant": session_score.significant,
                },
            )
            return on_summary(channel, finished)

        next_index = game.round_index + 1
        round_data = generate_round(self._game_cfg(), rng=self.rng)
        nxt = GameSession(
            round_index=next_index,
            rounds_per_session=game.rounds_per_session,
            round_data=round_data,
            round_scores=game.round_scores,
        )
        self.logger.log_event(
            identity=identity,
            event_name="round_shown",
            channel=channel,
            event_parameters={"round_index": next_index},
        )
        return on_round(channel, nxt)
