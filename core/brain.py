# coding: utf-8
"""
Чистые ответы сценария (тексты + кнопки + экран).

Цель:
    Собрать AppResponse без I/O и без обращения к логгеру.
    Тексты — из dialog_messages.json.
"""

from __future__ import annotations

from core.messages import button, message
from core.models import AppResponse, GameSession, Screen


def _fmt_pct(value: float) -> str:
    """Доля → строка процентов с одним знаком."""
    return f"{100.0 * value:.1f}%"


def _fmt_p(value: float) -> str:
    """p-value для отображения."""
    if value < 0.001:
        return f"{value:.2e}"
    return f"{value:.4f}"


def on_welcome(channel: str, rounds_total: int) -> AppResponse:
    """Экран START."""
    return AppResponse(
        text=message("welcome", channel, rounds_total=rounds_total),
        buttons=[button("start", channel)],
        screen=Screen.START,
        finished=False,
        game=None,
    )


def on_round(channel: str, game: GameSession) -> AppResponse:
    """Экран ROUND: догадка по графику."""
    return AppResponse(
        text=message(
            "round_prompt",
            channel,
            round_index=game.round_index,
            rounds_total=game.rounds_per_session,
        ),
        buttons=[
            button("guess_effect", channel),
            button("guess_no_effect", channel),
        ],
        screen=Screen.ROUND,
        finished=False,
        game=game,
    )


def on_feedback(channel: str, game: GameSession) -> AppResponse:
    """Экран FEEDBACK сразу после догадки."""
    score = game.last_round_score
    z_result = game.last_z_result
    if score is None or z_result is None:
        raise ValueError("Для FEEDBACK нужны last_round_score и last_z_result")

    result_line = "верно" if score.points == 1 else "неверно"
    verdict = "эффект значим" if z_result.significant else "эффекта нет"
    return AppResponse(
        text=message(
            "feedback",
            channel,
            round_index=game.round_index,
            result_line=result_line,
            p_value=_fmt_p(z_result.p_value),
            verdict=verdict,
            points=score.points,
        ),
        buttons=[button("next_round", channel)],
        screen=Screen.FEEDBACK,
        finished=False,
        game=game,
    )


def on_summary(channel: str, game: GameSession) -> AppResponse:
    """Экран SUMMARY: доля верных + CI + p-value."""
    session = game.session_score
    if session is None:
        raise ValueError("Для SUMMARY нужен session_score")

    session_verdict = (
        "доля значимо отличается от 50%"
        if session.significant
        else "отличие от 50% незначимо"
    )
    ci_level = int(round(100.0 * (1.0 - session.alpha)))
    return AppResponse(
        text=message(
            "summary",
            channel,
            n_correct=session.n_correct,
            rounds_total=session.n_rounds,
            accuracy=_fmt_pct(session.accuracy),
            ci_level=ci_level,
            ci_low=_fmt_pct(session.ci_low),
            ci_high=_fmt_pct(session.ci_high),
            session_p=_fmt_p(session.p_value),
            session_verdict=session_verdict,
        ),
        buttons=[button("restart", channel)],
        screen=Screen.SUMMARY,
        finished=True,
        game=game,
    )
