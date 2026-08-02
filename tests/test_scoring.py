# coding: utf-8
"""Тесты подсчёта баллов раунда и сессии."""

from __future__ import annotations

import pytest

from core.models import RoundScore, ZTestResult
from core.scoring import score_round, score_session


def _z(significant: bool, p_value: float = 0.01) -> ZTestResult:
    """Минимальный ZTestResult для scoring-тестов."""
    return ZTestResult(
        p_value=p_value,
        z_stat=2.0 if significant else 0.0,
        significant=significant,
        alpha=0.05,
        successes_a=10,
        trials_a=100,
        successes_b=20 if significant else 10,
        trials_b=100,
        rate_a=0.1,
        rate_b=0.2 if significant else 0.1,
    )


def test_score_round_agree_effect() -> None:
    result = score_round(guess_has_effect=True, z_result=_z(True, 0.01))
    assert result.points == 1
    assert result.guess_has_effect is True
    assert result.test_significant is True
    assert result.p_value == 0.01


def test_score_round_agree_no_effect() -> None:
    result = score_round(guess_has_effect=False, z_result=_z(False, 0.4))
    assert result.points == 1
    assert result.p_value == 0.4


def test_score_round_disagree() -> None:
    wrong_guess_effect = score_round(True, _z(False, 0.5))
    wrong_guess_null = score_round(False, _z(True, 0.01))
    assert wrong_guess_effect.points == 0
    assert wrong_guess_null.points == 0


def test_score_session_all_correct() -> None:
    scores = [
        RoundScore(True, True, 1, 0.01),
        RoundScore(False, False, 1, 0.4),
        RoundScore(True, True, 1, 0.02),
        RoundScore(False, False, 1, 0.6),
    ]
    session = score_session(scores, alpha=0.05)
    assert session.n_rounds == 4
    assert session.n_correct == 4
    assert session.accuracy == 1.0
    assert session.ci_low > 0.4
    assert session.ci_high == 1.0
    assert session.p_value < 0.05
    assert session.significant is True


def test_score_session_chance_level() -> None:
    # 10 из 20 — ровно 50%: p-value высокий, CI вокруг 0.5
    scores = [
        RoundScore(True, True, 1, 0.01) if i < 10 else RoundScore(True, False, 0, 0.5)
        for i in range(20)
    ]
    session = score_session(scores, alpha=0.05)
    assert session.n_correct == 10
    assert session.accuracy == 0.5
    assert session.ci_low < 0.5 < session.ci_high
    assert session.p_value > 0.9
    assert session.significant is False
    assert abs(session.z_stat) < 1e-9


def test_score_session_empty_raises() -> None:
    with pytest.raises(ValueError, match="пустой"):
        score_session([])


def test_score_session_wilson_bounds_for_zero() -> None:
    scores = [RoundScore(True, False, 0, 0.5) for _ in range(5)]
    session = score_session(scores, alpha=0.05)
    assert session.accuracy == 0.0
    assert session.ci_low == 0.0
    assert 0.0 < session.ci_high < 0.6
    assert session.significant is True  # 0/5 далеко от 0.5
