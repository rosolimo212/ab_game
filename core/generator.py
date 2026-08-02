# coding: utf-8
"""
Генерация временных рядов биномиальной метрики для одного раунда A/B.

Цель:
    По параметрам из конфига (или явных аргументов) построить две ветки:
    дневные числитель/знаменатель и долю за день.

Правила MVP:
    - Метрика ∈ [0, 1], биномиальная доля.
    - base_p раунда: Uniform(base_p_min, base_p_max), иначе фиксированный base_p.
    - С вероятностью effect_probability ветка B получает сдвиг p:
      Uniform(-effect_relative_range, +effect_relative_range) * base_p.
    - Иначе p_B = p_A = base_p.
    - На каждый день: истинная доля с относительным шумом, затем Binomial(n, p_day).

Вход:
    Параметры game-секции и опциональный numpy Generator (воспроизводимость).

Выход:
    RoundData с ветками A и B.

Риски:
    При base_p близком к 0 или 1 и большом noise/effect клип в [0, 1] сжимает эффект.
    has_effect — про сдвиг в генераторе, не про значимость z-теста.
"""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from core.models import BranchSeries, DayPoint, RoundData


def _clip_probability(value: float) -> float:
    """Ограничивает вероятность отрезком [0, 1]."""
    return float(np.clip(value, 0.0, 1.0))


def _sample_base_p(game_cfg: Mapping[str, Any], rng: np.random.Generator) -> float:
    """
    Базовая доля раунда: разброс [base_p_min, base_p_max] или фиксированный base_p.
    """
    if "base_p_min" in game_cfg and "base_p_max" in game_cfg:
        lo = float(game_cfg["base_p_min"])
        hi = float(game_cfg["base_p_max"])
        if not 0.0 < lo <= hi < 1.0:
            raise ValueError(
                f"base_p_min/max должны быть в (0, 1) и min<=max, получено [{lo}, {hi}]"
            )
        return float(rng.uniform(lo, hi))
    return float(game_cfg["base_p"])


def _resolve_branch_b_p(
    base_p: float,
    effect_probability: float,
    effect_relative_range: float,
    rng: np.random.Generator,
) -> tuple[float, bool]:
    """
    Выбирает истинный p для ветки B и флаг has_effect.

    :return: (p_b, has_effect)
    """
    if rng.random() >= effect_probability:
        return base_p, False

    # Равномерный относительный сдвиг ± effect_relative_range от base_p.
    relative = rng.uniform(-effect_relative_range, effect_relative_range)
    p_b = _clip_probability(base_p * (1.0 + relative))
    return p_b, True


def _simulate_branch(
    name: str,
    true_p: float,
    n_days: int,
    n_per_day: int,
    noise: float,
    rng: np.random.Generator,
) -> BranchSeries:
    """
    Симулирует дневной ряд одной ветки.

    Каждый день:
        1) p_day = clip(true_p * (1 + N(0, noise)), 0, 1)  при noise > 0;
           иначе p_day = true_p.
        2) numerator ~ Binomial(n_per_day, p_day).
    """
    points: list[DayPoint] = []
    for day in range(1, n_days + 1):
        if noise > 0.0:
            p_day = _clip_probability(true_p * (1.0 + float(rng.normal(0.0, noise))))
        else:
            p_day = true_p
        numerator = int(rng.binomial(n_per_day, p_day))
        points.append(
            DayPoint(day=day, numerator=numerator, denominator=n_per_day)
        )
    return BranchSeries(name=name, true_p=true_p, points=tuple(points))


def generate_round(
    game_cfg: Mapping[str, Any],
    rng: np.random.Generator | None = None,
) -> RoundData:
    """
    Генерирует один раунд A/B по секции game конфига.

    :param game_cfg: словарь параметров (как config['game'] после resolve_game_cfg)
    :param rng: генератор случайных чисел; если None — создаётся новый
    :return: RoundData
    """
    if rng is None:
        rng = np.random.default_rng()

    base_p = _sample_base_p(game_cfg, rng)
    noise = float(game_cfg["noise"])
    n_per_day = int(game_cfg["n_per_day"])
    n_days = int(game_cfg["n_days"])
    effect_probability = float(game_cfg["effect_probability"])
    effect_relative_range = float(game_cfg["effect_relative_range"])

    p_b, has_effect = _resolve_branch_b_p(
        base_p=base_p,
        effect_probability=effect_probability,
        effect_relative_range=effect_relative_range,
        rng=rng,
    )

    branch_a = _simulate_branch(
        name="A",
        true_p=base_p,
        n_days=n_days,
        n_per_day=n_per_day,
        noise=noise,
        rng=rng,
    )
    branch_b = _simulate_branch(
        name="B",
        true_p=p_b,
        n_days=n_days,
        n_per_day=n_per_day,
        noise=noise,
        rng=rng,
    )

    return RoundData(
        branch_a=branch_a,
        branch_b=branch_b,
        has_effect=has_effect,
        base_p=base_p,
    )
