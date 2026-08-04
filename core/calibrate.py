# coding: utf-8
"""
Подгонка раунда под явный флаг «должен быть значимый эффект».

Если want_effect=True, а z-тест ещё не значим — увеличиваем |p_B − p_A|
и пересэмплируем ветку B, пока p_value < alpha (или исчерпан лимит шагов).

Если want_effect=False, а тест значим — сближаем p_B к p_A и пересэмплируем.
"""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np

from core.generator import _clip_probability, _simulate_branch
from core.models import RoundData
from core.stats import z_test_round


def calibrate_round_to_effect_flag(
    round_data: RoundData,
    game_cfg: Mapping[str, Any],
    rng: np.random.Generator,
    *,
    alpha: float | None = None,
    max_steps: int = 24,
) -> RoundData:
    """
    Гарантирует (насколько позволяют шум и клип), что
    z_test.significant == round_data.has_effect.

    :param round_data: уже сэмплированный раунд; ``has_effect`` — целевой флаг
    :return: RoundData с тем же флагом и, при необходимости, новым B / true_p
    """
    if alpha is None:
        alpha = float(game_cfg.get("alpha", 0.05))
    noise = float(game_cfg["noise"])
    n_per_day = int(game_cfg["n_per_day"])
    n_days = int(game_cfg["n_days"])
    want = bool(round_data.has_effect)
    p_a = float(round_data.branch_a.true_p)
    p_b = float(round_data.branch_b.true_p)

    current = round_data

    def _matches(rd: RoundData) -> bool:
        return z_test_round(rd, alpha=alpha).significant is want

    if _matches(current):
        return current

    if abs(p_b - p_a) < 1e-15:
        direction = 1.0 if float(rng.random()) < 0.5 else -1.0
        gap = max(p_a * 0.05, 0.01)
    else:
        direction = 1.0 if p_b > p_a else -1.0
        gap = abs(p_b - p_a)

    for steps in range(1, max_steps + 1):
        if want:
            gap = min(max(gap * 1.45, gap + 0.01), 0.95)
            new_p_b = _clip_probability(p_a + direction * gap)
        else:
            if steps >= max_steps // 2:
                new_p_b = p_a
            else:
                new_p_b = _clip_probability(p_a + (p_b - p_a) * 0.45)
            p_b = new_p_b

        branch_b = _simulate_branch(
            name="B",
            true_p=new_p_b,
            n_days=n_days,
            n_per_day=n_per_day,
            noise=noise,
            rng=rng,
        )
        current = RoundData(
            branch_a=current.branch_a,
            branch_b=branch_b,
            has_effect=want,
            base_p=current.base_p,
            calibrate_steps=steps,
        )
        if _matches(current):
            return current
        p_b = new_p_b

    return current
