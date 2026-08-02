# coding: utf-8
"""Тесты экспорта CSV."""

from __future__ import annotations

from core.export_csv import session_rounds_to_csv_rows, session_rounds_to_csv_text
from core.models import BranchSeries, DayPoint, RoundData


def _round(base: float = 0.1) -> RoundData:
    return RoundData(
        branch_a=BranchSeries(
            "A",
            base,
            (DayPoint(1, 10, 100), DayPoint(2, 12, 100)),
        ),
        branch_b=BranchSeries(
            "B",
            base * 1.2,
            (DayPoint(1, 20, 100), DayPoint(2, 22, 100)),
        ),
        has_effect=True,
        base_p=base,
    )


def test_csv_rows_shape() -> None:
    rows = session_rounds_to_csv_rows([_round(), _round(0.2)])
    assert len(rows) == 8  # 2 раунда × 2 ветки × 2 дня
    assert rows[0] == {"round": 1, "branch": "A", "date": 1, "value": 0.1}
    assert rows[2]["branch"] == "B"
    assert rows[4]["round"] == 2


def test_csv_text_header() -> None:
    text = session_rounds_to_csv_text([_round()])
    assert text.startswith("round,branch,date,value")
    assert "A" in text and "B" in text
