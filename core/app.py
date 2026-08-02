# coding: utf-8
"""
AppService — оркестратор игрового сценария.

Цель:
    Имя → сложность → раунды → фидбек → итог (или досрочный выход).

Состояние игры передаётся через payload["game"] (из session_state).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np

from core.brain import (
    on_difficulty,
    on_empty_name,
    on_feedback,
    on_round,
    on_summary,
    on_summary_empty,
    on_welcome,
)
from core.difficulty import (
    DIFFICULTY_EASY,
    DIFFICULTY_HARD,
    DIFFICULTY_NORMAL,
    resolve_game_cfg,
)
from core.generator import generate_round
from core.logging.base import EventLogger
from core.models import (
    ACTION_DIFFICULTY_EASY,
    ACTION_DIFFICULTY_HARD,
    ACTION_DIFFICULTY_NORMAL,
    ACTION_END_GAME,
    ACTION_GUESS_EFFECT,
    ACTION_GUESS_NO_EFFECT,
    ACTION_NAME_ENTERED,
    ACTION_NEXT_ROUND,
    ACTION_RESTART,
    AppResponse,
    GameSession,
    RoundData,
    UserIdentity,
)
from core.scoring import score_round, score_session
from core.stats import z_test_round

ACTION_TO_DIFFICULTY = {
    ACTION_DIFFICULTY_EASY: DIFFICULTY_EASY,
    ACTION_DIFFICULTY_NORMAL: DIFFICULTY_NORMAL,
    ACTION_DIFFICULTY_HARD: DIFFICULTY_HARD,
}

BUTTON_CLICK_EVENTS = {
    ACTION_NAME_ENTERED: "button_continue",
    ACTION_DIFFICULTY_EASY: "button_difficulty_easy",
    ACTION_DIFFICULTY_NORMAL: "button_difficulty_normal",
    ACTION_DIFFICULTY_HARD: "button_difficulty_hard",
    ACTION_GUESS_EFFECT: "button_guess_effect",
    ACTION_GUESS_NO_EFFECT: "button_guess_no_effect",
    ACTION_NEXT_ROUND: "button_next_round",
    ACTION_END_GAME: "button_end_game",
    ACTION_RESTART: "button_restart",
}


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

    def _log_button_click(
        self, identity: UserIdentity, channel: str, action: str
    ) -> None:
        event_name = BUTTON_CLICK_EVENTS.get(action)
        if event_name is None:
            return
        self.logger.log_event(
            identity=identity,
            event_name=event_name,
            channel=channel,
            event_parameters={"action": action},
        )

    def _round_shown_params(
        self,
        round_index: int,
        round_data: RoundData,
        *,
        noise: float,
        difficulty: str,
    ) -> dict[str, Any]:
        z_result = z_test_round(round_data, alpha=self._alpha())
        return {
            "round_index": round_index,
            "difficulty": difficulty,
            "noise": noise,
            "mean_a": round_data.branch_a.pooled_rate,
            "mean_b": round_data.branch_b.pooled_rate,
            "target_a": round_data.branch_a.true_p,
            "target_b": round_data.branch_b.true_p,
            "p_value": z_result.p_value,
        }

    def handle_start(
        self,
        identity: UserIdentity,
        channel: str,
        context: dict[str, Any] | None = None,
    ) -> AppResponse:
        """Первый визит: имя или сразу выбор сложности, если имя уже есть."""
        _ = context
        identity = self._resolve_identity(identity, channel)
        self._ensure_user_stub(identity, channel)
        self.logger.log_event(
            identity=identity,
            event_name="start_screen_visit",
            channel=channel,
            event_parameters=None,
        )
        profile = self.logger.get_user_profile(identity) or {}
        existing_name = str(profile.get("user_name") or "").strip()
        if existing_name:
            return on_difficulty(channel, existing_name)
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
        self._log_button_click(identity, channel, action)

        if action == ACTION_NAME_ENTERED:
            return self._handle_name_entered(identity, channel, payload)

        if action in ACTION_TO_DIFFICULTY:
            return self._start_session(
                identity,
                channel,
                payload,
                difficulty=ACTION_TO_DIFFICULTY[action],
            )

        if action == ACTION_GUESS_EFFECT:
            self._touch_user(identity, channel, payload)
            return self._handle_guess(identity, channel, payload, True)

        if action == ACTION_GUESS_NO_EFFECT:
            self._touch_user(identity, channel, payload)
            return self._handle_guess(identity, channel, payload, False)

        if action == ACTION_NEXT_ROUND:
            self._touch_user(identity, channel, payload)
            return self._handle_next(identity, channel, payload)

        if action == ACTION_END_GAME:
            self._touch_user(identity, channel, payload)
            return self._end_game(identity, channel, payload)

        if action == ACTION_RESTART:
            self._touch_user(identity, channel, payload)
            user_name = str(payload.get("user_name") or "").strip()
            if not user_name:
                profile = self.logger.get_user_profile(identity) or {}
                user_name = str(profile.get("user_name") or "").strip()
            if user_name:
                return on_difficulty(channel, user_name)
            return on_welcome(channel, self._rounds_per_session())

        return on_welcome(channel, self._rounds_per_session())

    def _ensure_user_stub(self, identity: UserIdentity, channel: str) -> None:
        now = datetime.now()
        profile = self.logger.get_user_profile(identity) or {}
        existing_name = str(profile.get("user_name") or "")
        reg = profile.get("registration_date")
        if not isinstance(reg, datetime):
            reg = now
        self.logger.upsert_user(
            identity=identity,
            user_name=existing_name,
            registration_date=reg,
            registration_channel=channel,
            last_active_at=now,
        )

    def _touch_user(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        payload = payload or {}
        now = datetime.now()
        profile = self.logger.get_user_profile(identity) or {}
        user_name = str(payload.get("user_name") or profile.get("user_name") or "")
        reg = profile.get("registration_date")
        if not isinstance(reg, datetime):
            reg = now
        self.logger.upsert_user(
            identity=identity,
            user_name=user_name,
            registration_date=reg,
            registration_channel=channel,
            last_active_at=now,
        )

    def _handle_name_entered(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        user_name = str(payload.get("text") or payload.get("user_name") or "").strip()
        if not user_name:
            return on_empty_name(channel, self._rounds_per_session())

        now = datetime.now()
        profile = self.logger.get_user_profile(identity) or {}
        reg = profile.get("registration_date")
        if not isinstance(reg, datetime):
            reg = now
        self.logger.upsert_user(
            identity=identity,
            user_name=user_name,
            registration_date=reg,
            registration_channel=channel,
            last_active_at=now,
        )
        self.logger.log_event(
            identity=identity,
            event_name="name_entered",
            channel=channel,
            event_parameters={"user_name": user_name},
        )
        return on_difficulty(channel, user_name)

    def _start_session(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
        *,
        difficulty: str,
    ) -> AppResponse:
        self._touch_user(identity, channel, payload)
        profile = self.logger.get_user_profile(identity) or {}
        user_name = str(
            payload.get("user_name") or profile.get("user_name") or ""
        ).strip()
        if not user_name:
            return on_welcome(channel, self._rounds_per_session())

        session_cfg = resolve_game_cfg(self._game_cfg(), difficulty)
        rounds_total = int(session_cfg["rounds_per_session"])
        noise = float(session_cfg["noise"])
        round_data = generate_round(session_cfg, rng=self.rng)
        game = GameSession(
            round_index=1,
            rounds_per_session=rounds_total,
            round_data=round_data,
            round_scores=(),
            difficulty=difficulty,
            user_name=user_name,
            noise=noise,
        )
        self.logger.log_event(
            identity=identity,
            event_name="session_start",
            channel=channel,
            event_parameters={
                "rounds_per_session": rounds_total,
                "difficulty": difficulty,
                "noise": noise,
                "effect_relative_range": float(session_cfg["effect_relative_range"]),
                "user_name": user_name,
            },
        )
        self.logger.log_event(
            identity=identity,
            event_name="round_shown",
            channel=channel,
            event_parameters=self._round_shown_params(
                1, round_data, noise=noise, difficulty=difficulty
            ),
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
        user_answer = "effect" if guess_has_effect else "no_effect"
        updated = GameSession(
            round_index=game.round_index,
            rounds_per_session=game.rounds_per_session,
            round_data=game.round_data,
            round_scores=game.round_scores + (round_score,),
            last_z_result=z_result,
            last_round_score=round_score,
            session_score=None,
            difficulty=game.difficulty,
            user_name=game.user_name,
            noise=game.noise,
        )
        self.logger.log_event(
            identity=identity,
            event_name="guess_submitted",
            channel=channel,
            event_parameters={
                "round_index": updated.round_index,
                "user_answer": user_answer,
                "guess_has_effect": guess_has_effect,
                "test_significant": z_result.significant,
                "points": round_score.points,
                "p_value": z_result.p_value,
                "difficulty": updated.difficulty,
            },
        )
        return on_feedback(channel, updated)

    def _finish_with_scores(
        self,
        identity: UserIdentity,
        channel: str,
        game: GameSession,
    ) -> AppResponse:
        if not game.round_scores:
            self.logger.log_event(
                identity=identity,
                event_name="game_finished",
                channel=channel,
                event_parameters={
                    "n_correct": 0,
                    "n_rounds": 0,
                    "early_exit": True,
                    "difficulty": game.difficulty,
                    "user_name": game.user_name,
                },
            )
            return on_summary_empty(channel, game.user_name, game.difficulty)

        session_score = score_session(game.round_scores, alpha=self._alpha())
        finished = GameSession(
            round_index=game.round_index,
            rounds_per_session=game.rounds_per_session,
            round_data=None,
            round_scores=game.round_scores,
            last_z_result=game.last_z_result,
            last_round_score=game.last_round_score,
            session_score=session_score,
            difficulty=game.difficulty,
            user_name=game.user_name,
            noise=game.noise,
        )
        self.logger.log_event(
            identity=identity,
            event_name="game_finished",
            channel=channel,
            event_parameters={
                "n_correct": session_score.n_correct,
                "n_rounds": session_score.n_rounds,
                "accuracy": session_score.accuracy,
                "ci_low": session_score.ci_low,
                "ci_high": session_score.ci_high,
                "p_value": session_score.p_value,
                "significant": session_score.significant,
                "difficulty": finished.difficulty,
                "user_name": finished.user_name,
                "early_exit": len(game.round_scores) < game.rounds_per_session,
            },
        )
        return on_summary(channel, finished)

    def _end_game(
        self,
        identity: UserIdentity,
        channel: str,
        payload: dict[str, Any],
    ) -> AppResponse:
        game = payload.get("game")
        if not isinstance(game, GameSession):
            user_name = str(payload.get("user_name") or "").strip()
            return on_summary_empty(channel, user_name, DIFFICULTY_NORMAL)
        return self._finish_with_scores(identity, channel, game)

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
            return self._finish_with_scores(identity, channel, game)

        session_cfg = resolve_game_cfg(self._game_cfg(), game.difficulty)
        next_index = game.round_index + 1
        round_data = generate_round(session_cfg, rng=self.rng)
        nxt = GameSession(
            round_index=next_index,
            rounds_per_session=game.rounds_per_session,
            round_data=round_data,
            round_scores=game.round_scores,
            difficulty=game.difficulty,
            user_name=game.user_name,
            noise=float(session_cfg["noise"]),
        )
        self.logger.log_event(
            identity=identity,
            event_name="round_shown",
            channel=channel,
            event_parameters=self._round_shown_params(
                next_index,
                round_data,
                noise=nxt.noise,
                difficulty=nxt.difficulty,
            ),
        )
        return on_round(channel, nxt)
