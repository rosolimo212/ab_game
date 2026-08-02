# coding: utf-8
"""Тесты Plotly-графика A/B."""

from __future__ import annotations

from core.models import BranchSeries, DayPoint, RoundData
from ui.charts import build_ab_chart


def _sample_round() -> RoundData:
    branch_a = BranchSeries(
        name="A",
        true_p=0.1,
        points=(
            DayPoint(1, 10, 100),
            DayPoint(2, 12, 100),
            DayPoint(3, 8, 100),
        ),
    )
    branch_b = BranchSeries(
        name="B",
        true_p=0.2,
        points=(
            DayPoint(1, 20, 100),
            DayPoint(2, 22, 100),
            DayPoint(3, 18, 100),
        ),
    )
    return RoundData(
        branch_a=branch_a,
        branch_b=branch_b,
        has_effect=True,
        base_p=0.1,
    )


def test_build_ab_chart_two_traces() -> None:
    fig = build_ab_chart(_sample_round())
    assert len(fig.data) == 2
    assert fig.data[0].name == "A"
    assert fig.data[1].name == "B"
    assert list(fig.data[0].x) == [1, 2, 3]
    assert list(fig.data[1].x) == [1, 2, 3]
    assert fig.data[0].y[0] == 0.1
    assert fig.data[1].y[0] == 0.2
    assert fig.layout.xaxis.title.text == "День"
    assert fig.layout.yaxis.title.text == "Доля"
    # ось Y: 0 .. max*1.15 (max rate = 0.22)
    assert fig.layout.yaxis.range[0] == 0.0
    assert abs(fig.layout.yaxis.range[1] - 0.22 * 1.15) < 1e-9


def test_build_ab_chart_hover_has_counts() -> None:
    fig = build_ab_chart(_sample_round())
    # customdata: (numerator, denominator) на точку
    assert tuple(fig.data[0].customdata[0]) == (10, 100)
    assert tuple(fig.data[1].customdata[2]) == (18, 100)
    assert "Числитель" in fig.data[0].hovertemplate
    assert "Знаменатель" in fig.data[0].hovertemplate
    assert "Доля" in fig.data[0].hovertemplate


def test_build_ab_chart_title_optional() -> None:
    fig = build_ab_chart(_sample_round(), title=None)
    title = fig.layout.title
    text = getattr(title, "text", None) if title is not None else None
    assert text in (None, "")
