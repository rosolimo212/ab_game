# coding: utf-8
"""
Plotly-график двух веток A/B для одного раунда.

Цель:
    По RoundData построить фигуру: дневная доля по оси Y, день — по X.
    Ось Y: всегда от 0 до max(rate)*1.15.
    Легенда — под графиком (не пересекается с заголовком/текстом сверху).

Подписи осей и hover — из data/dialog_messages.json.
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from core.messages import message
from core.models import BranchSeries, RoundData


def _branch_trace(
    branch: BranchSeries,
    color: str,
    *,
    channel: str,
) -> go.Scatter:
    """Одна линия ветки; доля в hover — проценты с 2 знаками (Plotly `.2%`)."""
    days = [point.day for point in branch.points]
    rates = [point.rate for point in branch.points]
    nums = [point.numerator for point in branch.points]
    dens = [point.denominator for point in branch.points]

    # hovertemplate: {branch} подставляем мы; %{…} — плейсхолдеры Plotly.
    hover = message("chart_hover", channel, branch=branch.name)

    return go.Scatter(
        x=days,
        y=rates,
        mode="lines+markers",
        name=branch.name,
        line={"color": color, "width": 2},
        marker={"size": 7},
        customdata=list(zip(nums, dens)),
        hovertemplate=hover,
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
    title: str | None = "",
    channel: str = "streamlit",
) -> go.Figure:
    """
    Строит график двух временных рядов (ветка A и B).

    :param round_data: данные раунда
    :param title: заголовок; "" — взять chart_title из JSON; None — без title
    :param channel: канал для текстов из dialog_messages.json
    :return: Figure
    """
    fig = go.Figure()
    fig.add_trace(
        _branch_trace(round_data.branch_a, color="#1f77b4", channel=channel)
    )
    fig.add_trace(
        _branch_trace(round_data.branch_b, color="#ff7f0e", channel=channel)
    )

    y0, y1 = y_axis_range(round_data)
    # Легенда снизу: не перекрывает markdown над графиком и title сверху.
    layout: dict[str, Any] = {
        "xaxis_title": message("chart_xaxis", channel),
        "yaxis_title": message("chart_yaxis", channel),
        "yaxis": {
            "range": [y0, y1],
            "tickformat": ".2%",
            "rangemode": "tozero",
        },
        "legend": {
            "orientation": "h",
            "yanchor": "top",
            "y": -0.22,
            "xanchor": "left",
            "x": 0,
        },
        "margin": {"l": 56, "r": 24, "t": 48, "b": 96},
        "hovermode": "x unified",
    }
    if title is None:
        pass
    elif title == "":
        layout["title"] = message("chart_title", channel)
    else:
        layout["title"] = title
    fig.update_layout(**layout)
    return fig
