# coding: utf-8
"""
Чистые ответы сценария (тексты + кнопки + экран).

Цель:
    Собрать AppResponse без I/O и без обращения к логгеру.
    Тексты — из dialog_messages.json.
"""

from __future__ import annotations

from core.difficulty import difficulty_label
from core.format_text import fmt_p_value, fmt_pct
from core.messages import button, message
from core.models import AppResponse, GameSession, Screen


def on_welcome(channel: str, rounds_total: int) -> AppResponse:
    """Экран START: представление."""
    return AppResponse(
        text=message("welcome", channel, rounds_total=rounds_total),
        buttons=[button("continue", channel)],
        screen=Screen.START,
        finished=False,
        game=None,
    )


def on_empty_name(channel: str, rounds_total: int) -> AppResponse:
    """Пустое имя на START."""
    return AppResponse(
        text=message("empty_name", channel, rounds_total=rounds_total),
        buttons=[button("continue", channel)],
        screen=Screen.START,
        finished=False,
        game=None,
    )


def on_difficulty(channel: str, user_name: str) -> AppResponse:
    """Экран выбора сложности."""
    return AppResponse(
        text=message("choose_difficulty", channel, user_name=user_name),
        buttons=[
            button("difficulty_easy", channel),
            button("difficulty_normal", channel),
            button("difficulty_hard", channel),
        ],
        screen=Screen.DIFFICULTY,
        finished=False,
        game=None,
        user_name=user_name,
    )


def on_round(channel: str, game: GameSession) -> AppResponse:
    """Экран ROUND: догадка по графику."""
    return AppResponse(
        text=message(
            "round_prompt",
            channel,
            round_index=game.round_index,
            rounds_total=game.rounds_per_session,
            difficulty=difficulty_label(game.difficulty),
            user_name=game.user_name,
        ),
        buttons=[
            button("guess_effect", channel),
            button("guess_no_effect", channel),
            button("end_game", channel),
        ],
        screen=Screen.ROUND,
        finished=False,
        game=game,
        user_name=game.user_name,
    )


def on_feedback(channel: str, game: GameSession) -> AppResponse:
    """Экран FEEDBACK сразу после догадки."""
    score = game.last_round_score
    z_result = game.last_z_result
    if score is None or z_result is None:
        raise ValueError("Для FEEDBACK нужны last_round_score и last_z_result")

    result_line = message(
        "feedback_result_ok" if score.points == 1 else "feedback_result_fail",
        channel,
    )
    verdict = message(
        "feedback_verdict_significant" if z_result.significant else "feedback_verdict_ns",
        channel,
    )
    return AppResponse(
        text=message(
            "feedback",
            channel,
            round_index=game.round_index,
            result_line=result_line,
            p_value=fmt_p_value(z_result.p_value),
            verdict=verdict,
            points=score.points,
            user_name=game.user_name,
        ),
        buttons=[
            button("next_round", channel),
            button("end_game", channel),
        ],
        screen=Screen.FEEDBACK,
        finished=False,
        game=game,
        user_name=game.user_name,
    )


def on_summary(channel: str, game: GameSession) -> AppResponse:
    """Экран SUMMARY: доля верных + CI + p-value."""
    session = game.session_score
    if session is None:
        raise ValueError("Для SUMMARY нужен session_score")

    session_verdict = message(
        "summary_verdict_significant" if session.significant else "summary_verdict_ns",
        channel,
    )
    ci_level = int(round(100.0 * (1.0 - session.alpha)))
    return AppResponse(
        text=message(
            "summary",
            channel,
            user_name=game.user_name or message("default_player_name", channel),
            difficulty=difficulty_label(game.difficulty),
            n_correct=session.n_correct,
            rounds_total=session.n_rounds,
            accuracy=fmt_pct(session.accuracy),
            ci_level=ci_level,
            ci_low=fmt_pct(session.ci_low),
            ci_high=fmt_pct(session.ci_high),
            session_p=fmt_p_value(session.p_value),
            session_verdict=session_verdict,
        ),
        buttons=[button("export_csv", channel), button("restart", channel)],
        screen=Screen.SUMMARY,
        finished=True,
        game=game,
        user_name=game.user_name,
    )


def on_summary_empty(channel: str, user_name: str, difficulty: str) -> AppResponse:
    """Итог без сыгранных раундов (ранний выход)."""
    return AppResponse(
        text=message(
            "summary_empty",
            channel,
            user_name=user_name or message("default_player_name", channel),
            difficulty=difficulty_label(difficulty),
        ),
        buttons=[button("restart", channel)],
        screen=Screen.SUMMARY,
        finished=True,
        game=GameSession(
            round_index=0,
            rounds_per_session=0,
            user_name=user_name,
            difficulty=difficulty,
        ),
        user_name=user_name,
    )
