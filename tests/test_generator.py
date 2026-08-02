# coding: utf-8
"""Тесты генератора биномиальных рядов."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from core.config import load_app_config
from core.difficulty import DIFFICULTY_HARD, resolve_game_cfg
from core.generator import generate_round
from core.stats import z_test_round

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / "settings.yaml"


def _game_cfg():
    return load_app_config(SETTINGS, secrets_file=None)["game"]


def test_generate_round_shape_and_bounds() -> None:
    game = _game_cfg()
    rng = np.random.default_rng(42)
    round_data = generate_round(game, rng=rng)

    assert len(round_data.branch_a.points) == game["n_days"]
    assert len(round_data.branch_b.points) == game["n_days"]
    assert round_data.branch_a.name == "A"
    assert round_data.branch_b.name == "B"
    assert game["base_p_min"] <= round_data.base_p <= game["base_p_max"]

    for branch in (round_data.branch_a, round_data.branch_b):
        for point in branch.points:
            assert point.denominator == game["n_per_day"]
            assert 0 <= point.numerator <= point.denominator
            assert 0.0 <= point.rate <= 1.0


def test_base_p_varies_across_rounds() -> None:
    game = _game_cfg()
    rng = np.random.default_rng(99)
    bases = {generate_round(game, rng=rng).base_p for _ in range(40)}
    assert len(bases) > 5


def test_effect_flag_false_keeps_same_true_p() -> None:
    game = dict(_game_cfg())
    game["effect_probability"] = 0.0
    game.pop("base_p_min", None)
    game.pop("base_p_max", None)
    rng = np.random.default_rng(7)
    round_data = generate_round(game, rng=rng)
    assert round_data.has_effect is False
    assert round_data.branch_a.true_p == round_data.branch_b.true_p == game["base_p"]


def test_effect_flag_true_shifts_within_relative_range() -> None:
    game = dict(_game_cfg())
    game["effect_probability"] = 1.0
    game["noise"] = 0.0
    game.pop("base_p_min", None)
    game.pop("base_p_max", None)
    base_p = float(game["base_p"])
    rel = float(game["effect_relative_range"])
    rng = np.random.default_rng(11)

    for _ in range(50):
        round_data = generate_round(game, rng=rng)
        assert round_data.has_effect is True
        p_b = round_data.branch_b.true_p
        assert 0.0 <= p_b <= 1.0
        assert abs(p_b - base_p) <= base_p * rel + 1e-12 or p_b in (0.0, 1.0)


def test_effect_probability_roughly_half() -> None:
    game = dict(_game_cfg())
    game["effect_probability"] = 0.5
    rng = np.random.default_rng(123)
    n = 2000
    effects = sum(generate_round(game, rng=rng).has_effect for _ in range(n))
    share = effects / n
    assert 0.45 <= share <= 0.55


def test_hard_difficulty_effect_rate_near_half_and_not_always_null() -> None:
    """
    На hard эффект в генераторе ~50%; среди раундов с эффектом
    z-тест не должен почти всегда давать «эффекта нет».
    """
    root_game = _game_cfg()
    hard = resolve_game_cfg(root_game, DIFFICULTY_HARD)
    assert abs(float(hard["effect_probability"]) - 0.5) < 1e-9
    assert float(hard["effect_relative_range"]) >= 0.2

    rng = np.random.default_rng(2026)
    n = 400
    with_effect = 0
    significant_given_effect = 0
    for _ in range(n):
        rd = generate_round(hard, rng=rng)
        if not rd.has_effect:
            continue
        with_effect += 1
        zt = z_test_round(rd, alpha=float(hard["alpha"]))
        if zt.significant:
            significant_given_effect += 1

    assert with_effect >= n * 0.35
    # При старом range=0.08 доля significant была << 20%; ждём заметно выше.
    assert significant_given_effect / with_effect >= 0.25
