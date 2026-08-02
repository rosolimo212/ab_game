# coding: utf-8
"""
Plotly-график двух веток A/B для одного раунда.

Цель:
    По RoundData построить фигуру: дневная доля метрики по оси Y, день — по X.
    Hover показывает rate, числитель и знаменатель. Без Streamlit и без I/O.

Вход:
    RoundData (ветки A и B с DayPoint).

Выход:
    plotly.graph_objects.Figure.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from core.models import BranchSeries, RoundData


def _branch_trace(branch: BranchSeries, color: str) -> go.Scatter:
    """Одна линия ветки с кастомным hover."""
    days = [point.day for point in branch.points]
    rates = [point.rate for point in branch.points]
    nums = [point.numerator for point in branch.points]
    dens = [point.denominator for point in branch.points]

    return go.Scatter(
        x=days,
        y=rates,
        mode="lines+markers",
        name=branch.name,
        line={"color": color, "width": 2},
        marker={"size": 7},
        customdata=list(zip(nums, dens)),
        hovertemplate=(
            f"Ветка {branch.name}<br>"
            "День %{x}<br>"
            "Доля %{y:.4f}<br>"
            "Числитель %{customdata[0]}<br>"
            "Знаменатель %{customdata[1]}"
            "<extra></extra>"
        ),
    )


def build_ab_chart(
    round_data: RoundData,
    *,
    title: str | None = "A/B: дневная доля метрики",
) -> go.Figure:
    """
    Строит график двух временных рядов (ветка A и B).

    :param round_data: данные раунда
    :param title: заголовок; None — без title
    :return: Figure (готово к st.plotly_chart / fig.show)
    """
    fig = go.Figure()
    fig.add_trace(_branch_trace(round_data.branch_a, color="#1f77b4"))
    fig.add_trace(_branch_trace(round_data.branch_b, color="#ff7f0e"))

    layout: dict[str, Any] = {
        "xaxis_title": "День",
        "yaxis_title": "Доля",
        "yaxis": {"range": [0, 1], "tickformat": ".0%"},
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        "margin": {"l": 48, "r": 24, "t": 56, "b": 48},
        "hovermode": "x unified",
    }
    if title is not None:
        layout["title"] = title
    fig.update_layout(**layout)
    return fig
