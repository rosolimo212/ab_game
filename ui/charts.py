# coding: utf-8
"""
Plotly-график двух веток A/B для одного раунда.

Цель:
    По RoundData построить фигуру: дневная доля метрики по оси Y, день — по X.
    Ось Y: всегда от 0 до max(rate)*1.15 (без «прыгающего» автоскейла к 100%).
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


def y_axis_range(round_data: RoundData, *, headroom: float = 1.15) -> tuple[float, float]:
    """
    Диапазон оси Y: минимум 0, максимум = max(rate) * headroom.

    Если все точки 0 — небольшой запас, чтобы ось не схлопнулась.
    """
    rates = [p.rate for p in round_data.branch_a.points] + [
        p.rate for p in round_data.branch_b.points
    ]
    peak = max(rates) if rates else 0.0
    y_max = peak * headroom
    if y_max <= 0.0:
        y_max = 0.05
    return 0.0, y_max


def build_ab_chart(
    round_data: RoundData,
    *,
    title: str | None = "A/B: дневная доля метрики",
) -> go.Figure:
    """
    Строит график двух временных рядов (ветка A и B).

    :param round_data: данные раунда
    :param title: заголовок; None — без title
    :return: Figure
    """
    fig = go.Figure()
    fig.add_trace(_branch_trace(round_data.branch_a, color="#1f77b4"))
    fig.add_trace(_branch_trace(round_data.branch_b, color="#ff7f0e"))

    y0, y1 = y_axis_range(round_data)
    layout: dict[str, Any] = {
        "xaxis_title": "День",
        "yaxis_title": "Доля",
        "yaxis": {"range": [y0, y1], "tickformat": ".0%", "rangemode": "tozero"},
        "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        "margin": {"l": 48, "r": 24, "t": 56, "b": 48},
        "hovermode": "x unified",
    }
    if title is not None:
        layout["title"] = title
    fig.update_layout(**layout)
    return fig
