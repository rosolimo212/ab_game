# coding: utf-8
"""Тесты z-теста двух пропорций."""

from __future__ import annotations

import numpy as np

from core.generator import generate_round
from core.models import BranchSeries, DayPoint, RoundData
from core.stats import two_proportion_z_test, z_test_round


def test_identical_proportions_not_significant() -> None:
    result = two_proportion_z_test(
        successes_a=50,
        trials_a=200,
        successes_b=50,
        trials_b=200,
        alpha=0.05,
    )
    assert result.p_value > 0.05
    assert result.significant is False
    assert result.z_stat == 0.0


def test_large_difference_significant() -> None:
    result = two_proportion_z_test(
        successes_a=100,
        trials_a=1000,
        successes_b=200,
        trials_b=1000,
        alpha=0.05,
    )
    assert result.p_value < 0.05
    assert result.significant is True


def test_zero_trials_returns_nonsignificant() -> None:
    result = two_proportion_z_test(0, 0, 0, 10, alpha=0.05)
    assert result.significant is False
    assert result.p_value == 1.0


def test_z_test_round_pools_days() -> None:
    branch_a = BranchSeries(
        name="A",
        true_p=0.1,
        points=(
            DayPoint(1, 10, 100),
            DayPoint(2, 10, 100),
        ),
    )
    branch_b = BranchSeries(
        name="B",
        true_p=0.2,
        points=(
            DayPoint(1, 20, 100),
            DayPoint(2, 20, 100),
        ),
    )
    round_data = RoundData(
        branch_a=branch_a,
        branch_b=branch_b,
        has_effect=True,
        base_p=0.1,
    )
    result = z_test_round(round_data, alpha=0.05)
    assert result.successes_a == 20
    assert result.trials_a == 200
    assert result.successes_b == 40
    assert result.trials_b == 200
    assert result.significant is True


def test_generator_and_z_test_smoke() -> None:
    game = {
        "base_p": 0.1,
        "noise": 0.0,
        "n_per_day": 500,
        "n_days": 14,
        "effect_probability": 0.0,
        "effect_relative_range": 0.2,
        "rounds_per_session": 20,
        "alpha": 0.05,
    }
    round_data = generate_round(game, rng=np.random.default_rng(0))
    result = z_test_round(round_data, alpha=game["alpha"])
    assert 0.0 <= result.p_value <= 1.0
    assert result.trials_a == 500 * 14
    assert result.trials_b == 500 * 14
