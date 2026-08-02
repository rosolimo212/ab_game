# coding: utf-8
"""
Статистическая проверка различий двух пропорций (z-тест).

Цель:
    По агрегированным числителям/знаменателям веток A и B посчитать
    двухсторонний z-тест пропорций и вердикт significant при заданном alpha.

Вход:
    successes/trials по двум группам, либо RoundData; alpha (по умолчанию 0.05).

Выход:
    ZTestResult (p_value, z_stat, significant, …).

Риски:
    При нулевых trials или se=0 (обе доли 0 или 1) z_stat=0, p_value=1.0 —
    считаем «эффекта нет» на уровне теста. Это осознанное упрощение MVP.
"""

from __future__ import annotations

import math

from core.models import RoundData, ZTestResult


def _standard_normal_sf(z: float) -> float:
    """
    Survival function Φ̄(z) = 1 - Φ(z) стандартного нормального распределения.

    Через erfc, без зависимости от scipy.
    """
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def two_proportion_z_test(
    successes_a: int,
    trials_a: int,
    successes_b: int,
    trials_b: int,
    alpha: float = 0.05,
) -> ZTestResult:
    """
    Двухсторонний z-тест равенства двух пропорций (pooled SE).

    :param successes_a: успехи группы A
    :param trials_a: испытания группы A
    :param successes_b: успехи группы B
    :param trials_b: испытания группы B
    :param alpha: порог значимости
    :return: ZTestResult
    """
    if trials_a < 0 or trials_b < 0:
        raise ValueError("Число испытаний не может быть отрицательным")
    if successes_a < 0 or successes_b < 0:
        raise ValueError("Число успехов не может быть отрицательным")
    if successes_a > trials_a or successes_b > trials_b:
        raise ValueError("Число успехов не может превышать число испытаний")
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha должен быть в (0, 1), получено {alpha}")

    if trials_a == 0 or trials_b == 0:
        return ZTestResult(
            p_value=1.0,
            z_stat=0.0,
            significant=False,
            alpha=alpha,
            successes_a=successes_a,
            trials_a=trials_a,
            successes_b=successes_b,
            trials_b=trials_b,
            rate_a=0.0 if trials_a == 0 else successes_a / trials_a,
            rate_b=0.0 if trials_b == 0 else successes_b / trials_b,
        )

    rate_a = successes_a / trials_a
    rate_b = successes_b / trials_b
    pooled = (successes_a + successes_b) / (trials_a + trials_b)
    se_sq = pooled * (1.0 - pooled) * (1.0 / trials_a + 1.0 / trials_b)

    # Вырожденный случай: обе доли 0 или 1 → дисперсия нулевая.
    if se_sq <= 0.0:
        z_stat = 0.0
        p_value = 1.0
    else:
        z_stat = (rate_a - rate_b) / math.sqrt(se_sq)
        p_value = 2.0 * _standard_normal_sf(abs(z_stat))
        # Численная защита от выхода за [0, 1] из-за float.
        p_value = min(1.0, max(0.0, p_value))

    return ZTestResult(
        p_value=p_value,
        z_stat=z_stat,
        significant=p_value < alpha,
        alpha=alpha,
        successes_a=successes_a,
        trials_a=trials_a,
        successes_b=successes_b,
        trials_b=trials_b,
        rate_a=rate_a,
        rate_b=rate_b,
    )


def z_test_round(round_data: RoundData, alpha: float = 0.05) -> ZTestResult:
    """
    Z-тест для данных раунда: пул по всем дням каждой ветки.

    :param round_data: сгенерированный раунд
    :param alpha: порог значимости
    :return: ZTestResult
    """
    return two_proportion_z_test(
        successes_a=round_data.branch_a.total_numerator,
        trials_a=round_data.branch_a.total_denominator,
        successes_b=round_data.branch_b.total_numerator,
        trials_b=round_data.branch_b.total_denominator,
        alpha=alpha,
    )
