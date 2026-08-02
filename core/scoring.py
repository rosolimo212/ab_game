# coding: utf-8
"""
Подсчёт баллов раунда и итога сессии.

Цель:
    Раунд — 1 балл, если догадка игрока совпала с вердиктом z-теста (не с has_effect
    генератора). Сессия — доля верных, Wilson CI и z-тест против p=0.5 (мета-ирония).

Вход:
    Догадка + ZTestResult; либо последовательность RoundScore и alpha.

Выход:
    RoundScore / SessionScore.

Риски:
    Пустая сессия запрещена. При n=1 CI широкий — это ожидаемо для малых выборок.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from core.models import RoundScore, SessionScore, ZTestResult


def _standard_normal_sf(z: float) -> float:
    """Survival function Φ̄(z) = 1 - Φ(z)."""
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def _standard_normal_ppf(p: float) -> float:
    """
    Квантиль N(0,1): Φ^{-1}(p).

    Бинарный поиск по Φ через erfc — без scipy и без erfcinv.
    """
    if not 0.0 < p < 1.0:
        raise ValueError(f"p должен быть в (0, 1), получено {p}")
    # Симметрия: ищем только в верхней половине.
    if p < 0.5:
        return -_standard_normal_ppf(1.0 - p)

    lo, hi = 0.0, 10.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        cdf = 1.0 - _standard_normal_sf(mid)
        if cdf < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def score_round(guess_has_effect: bool, z_result: ZTestResult) -> RoundScore:
    """
    Балл раунда: согласие с significant z-теста.

    :param guess_has_effect: догадка игрока («эффект есть»)
    :param z_result: результат z-теста по данным раунда
    :return: RoundScore с points ∈ {0, 1}
    """
    agrees = guess_has_effect is z_result.significant
    return RoundScore(
        guess_has_effect=guess_has_effect,
        test_significant=z_result.significant,
        points=1 if agrees else 0,
        p_value=z_result.p_value,
    )


def _wilson_ci(successes: int, n: int, alpha: float) -> tuple[float, float]:
    """
    Wilson score interval для биномиальной доли.

    :return: (ci_low, ci_high) в [0, 1]
    """
    if n <= 0:
        raise ValueError("n должен быть положительным")
    if not 0 <= successes <= n:
        raise ValueError("successes должен быть в [0, n]")

    z = _standard_normal_ppf(1.0 - alpha / 2.0)
    z2 = z * z
    p_hat = successes / n
    denom = 1.0 + z2 / n
    center = (p_hat + z2 / (2.0 * n)) / denom
    half = (
        z
        * math.sqrt((p_hat * (1.0 - p_hat) + z2 / (4.0 * n)) / n)
        / denom
    )
    return max(0.0, center - half), min(1.0, center + half)


def _proportion_z_vs_half(successes: int, n: int) -> tuple[float, float]:
    """
    Двухсторонний z-тест H0: p = 0.5 для биномиальной доли.

    :return: (z_stat, p_value)
    """
    if n <= 0:
        raise ValueError("n должен быть положительным")
    p_hat = successes / n
    se = math.sqrt(0.25 / n)
    z_stat = (p_hat - 0.5) / se
    p_value = 2.0 * _standard_normal_sf(abs(z_stat))
    p_value = min(1.0, max(0.0, p_value))
    return z_stat, p_value


def score_session(
    round_scores: Sequence[RoundScore],
    alpha: float = 0.05,
) -> SessionScore:
    """
    Итог сессии по баллам раундов.

    :param round_scores: результаты раундов (непустой)
    :param alpha: уровень для CI и вердикта significant vs 0.5
    :return: SessionScore
    """
    if not round_scores:
        raise ValueError("Сессия не может быть пустой")
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha должен быть в (0, 1), получено {alpha}")

    n_rounds = len(round_scores)
    n_correct = sum(score.points for score in round_scores)
    accuracy = n_correct / n_rounds
    ci_low, ci_high = _wilson_ci(n_correct, n_rounds, alpha)
    z_stat, p_value = _proportion_z_vs_half(n_correct, n_rounds)

    return SessionScore(
        n_rounds=n_rounds,
        n_correct=n_correct,
        accuracy=accuracy,
        ci_low=ci_low,
        ci_high=ci_high,
        p_value=p_value,
        z_stat=z_stat,
        significant=p_value < alpha,
        alpha=alpha,
    )
