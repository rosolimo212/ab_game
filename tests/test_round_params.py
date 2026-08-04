# coding: utf-8
"""Тесты сериализации round_parameters."""

from __future__ import annotations

from core.models import BranchSeries, DayPoint, RoundData, ZTestResult
from core.round_params import round_parameters_row, round_series_payload


def test_round_series_and_row() -> None:
    rd = RoundData(
        branch_a=BranchSeries("A", 0.1, (DayPoint(1, 10, 100),)),
        branch_b=BranchSeries("B", 0.2, (DayPoint(1, 25, 100),)),
        has_effect=True,
        base_p=0.1,
        calibrate_steps=2,
    )
    series = round_series_payload(rd)
    assert series["A"][0]["rate"] == 0.1
    assert series["B"][0]["numerator"] == 25

    z = ZTestResult(
        p_value=0.01,
        z_stat=2.0,
        significant=True,
        alpha=0.05,
        successes_a=10,
        trials_a=100,
        successes_b=25,
        trials_b=100,
        rate_a=0.1,
        rate_b=0.25,
    )
    row = round_parameters_row(
        rd, z, round_index=3, difficulty="hard", noise=0.12
    )
    assert row["want_effect"] is True
    assert row["aligned"] is True
    assert row["calibrate_steps"] == 2
    assert row["difficulty"] == "hard"
