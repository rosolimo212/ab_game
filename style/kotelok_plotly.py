"""Стиль kotelok для Plotly (vendored в ab_game/style/).

Устройство шапки (одна строка, фиксированные пиксели):
- слева заголовок графика, справа «Kotelok» + логотип на том же уровне;
- заголовок позиционируется через yref='container' + pad (пиксели от верха фигуры);
- «Kotelok» — annotation с якорем y=1 (верх области графика) + yshift в пикселях;
- логотип — big_kettler.png рядом с этим модулем.

Важно: paper-координаты (yref='paper') — доли области графика
(высота минус margin.t и margin.b), а не всей фигуры. Пиксели в paper-доли
переводим только делением на размер области графика.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Iterable

import plotly.graph_objects as go
import plotly.io as pio

STYLE_NAME = 'kotelok'
FONT = 'Helvetica'

TITLE_SIZE = 24
BRAND_TITLE_SIZE = 20
LINE_HEIGHT = 1.15

# Шапка: пиксели от верха фигуры.
HEADER_PAD_TOP = 10
HEADER_HEIGHT = 30
HEADER_GAP = 16

MARGIN_TOP = HEADER_PAD_TOP + HEADER_HEIGHT + HEADER_GAP
MARGIN_BOTTOM = 80
MARGIN_LEFT = 48
MARGIN_RIGHT = 16

Y_NTICKS = 3
AXIS_LINEWIDTH = 2
AXIS_TICK_SIZE = 14
TICK_LEN = 5
DEFAULT_WIDTH = 980
DEFAULT_HEIGHT = 420

LOGO_PATH = Path(__file__).with_name('big_kettler.png')
LOGO_ASPECT = 1576 / 1920  # ширина / высота
LOGO_HEIGHT_PX = 30
LOGO_GAP_PX = 8

PAIRED = [
    '#a6cee3', '#1f78b4', '#b2df8a', '#33a02c', '#fb9a99', '#e31a1c',
    '#fdbf6f', '#ff7f00', '#cab2d6', '#6a3d9a', '#ffff99', '#b15928',
]
COLORWAY = [PAIRED[i] for i in range(1, len(PAIRED), 2)]
INK_COLOR = PAIRED[1]

_TITLE = dict(
    font=dict(family=FONT, size=TITLE_SIZE, color=INK_COLOR),
    x=0,
    xref='paper',
    xanchor='left',
    y=1,
    yref='container',
    yanchor='top',
    pad=dict(t=HEADER_PAD_TOP, b=0, l=0, r=0),
)

_LEGEND = dict(
    orientation='h',
    x=0,
    xanchor='left',
    y=-0.24,
    yanchor='top',
    font=dict(family=FONT, size=11, color=INK_COLOR),
)

_AXIS = dict(
    showgrid=False,
    gridwidth=0,
    zeroline=False,
    zerolinewidth=0,
    zerolinecolor='rgba(0,0,0,0)',
    showline=True,
    linewidth=AXIS_LINEWIDTH,
    linecolor=INK_COLOR,
    mirror=False,
    ticks='outside',
    ticklen=TICK_LEN,
    tickwidth=AXIS_LINEWIDTH,
    tickcolor=INK_COLOR,
)


def _axis_layout() -> dict[str, Any]:
    tickfont = dict(family=FONT, size=AXIS_TICK_SIZE, color=INK_COLOR)
    return dict(
        xaxis=dict(**_AXIS, tickfont=tickfont),
        yaxis=dict(
            **_AXIS,
            tickfont=tickfont,
            autorangeoptions=dict(include='window'),
            nticks=Y_NTICKS,
        ),
    )


KOTELOK_TEMPLATE = go.layout.Template(
    layout=dict(
        font=dict(family=FONT, size=12, color=INK_COLOR),
        colorway=COLORWAY,
        paper_bgcolor='#FFFFFF',
        plot_bgcolor='#FFFFFF',
        margin=dict(l=MARGIN_LEFT, r=MARGIN_RIGHT, t=MARGIN_TOP, b=MARGIN_BOTTOM),
        title=_TITLE,
        legend=_LEGEND,
        hoverlabel=dict(
            bgcolor='#FFFFFF',
            bordercolor=INK_COLOR,
            font=dict(family=FONT, size=11, color=INK_COLOR),
        ),
        **_axis_layout(),
    ),
    data=dict(
        scatter=[
            dict(
                mode='lines',
                line=dict(shape='spline', smoothing=1.0, width=3),
            )
        ],
    ),
)


def register() -> None:
    pio.templates[STYLE_NAME] = KOTELOK_TEMPLATE


def color(i: int = 0) -> str:
    return COLORWAY[i % len(COLORWAY)]


def _to_list(values: Any) -> list[Any]:
    if values is None:
        return []
    tolist = getattr(values, 'tolist', None)
    if callable(tolist):
        return tolist()
    return list(values)


def _plot_box(fig: go.Figure) -> tuple[float, float]:
    """Размер области графика в пикселях (paper-единица = эта область)."""
    w = fig.layout.width or DEFAULT_WIDTH
    h = fig.layout.height or DEFAULT_HEIGHT
    margin = fig.layout.margin
    ml = margin.l if margin.l is not None else MARGIN_LEFT
    mr = margin.r if margin.r is not None else MARGIN_RIGHT
    mt = margin.t if margin.t is not None else MARGIN_TOP
    mb = margin.b if margin.b is not None else MARGIN_BOTTOM
    return w - ml - mr, h - mt - mb


def _logo_data_uri() -> str:
    mime = {
        '.png': 'image/png',
        '.svg': 'image/svg+xml',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.webp': 'image/webp',
    }.get(LOGO_PATH.suffix.lower(), 'application/octet-stream')
    encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode('ascii')
    return f'data:{mime};base64,{encoded}'


def _apply_branding(fig: go.Figure) -> None:
    plot_w, plot_h = _plot_box(fig)
    mt = fig.layout.margin.t if fig.layout.margin.t is not None else MARGIN_TOP

    logo_w_px = LOGO_HEIGHT_PX * LOGO_ASPECT
    has_logo = LOGO_PATH.exists()

    # Центр текста и центр логотипа — на одной горизонтали.
    text_center_px = HEADER_PAD_TOP + BRAND_TITLE_SIZE * LINE_HEIGHT / 2
    logo_top_px = text_center_px - LOGO_HEIGHT_PX / 2

    annotations = [
        dict(
            text='Kotelok',
            xref='paper',
            x=1,
            xanchor='right',
            xshift=-(logo_w_px + LOGO_GAP_PX) if has_logo else 0,
            yref='paper',
            y=1,
            yanchor='top',
            # Пиксельный сдвиг вверх: от верха области графика до линии шапки.
            yshift=mt - HEADER_PAD_TOP,
            showarrow=False,
            font=dict(family=FONT, size=BRAND_TITLE_SIZE, color=INK_COLOR),
        )
    ]

    images: list[dict[str, Any]] = []
    if has_logo:
        images.append(
            dict(
                source=_logo_data_uri(),
                xref='paper',
                yref='paper',
                x=1,
                xanchor='right',
                # Пиксели -> paper-доли: делим на размер области графика.
                y=1 + (mt - logo_top_px) / plot_h,
                yanchor='top',
                sizex=logo_w_px / plot_w,
                sizey=LOGO_HEIGHT_PX / plot_h,
                sizing='contain',
                layer='above',
            )
        )

    fig.update_layout(images=images, annotations=annotations)


def _align_title(fig: go.Figure, text: str | None = None) -> None:
    title = dict(_TITLE)
    if text is not None:
        title['text'] = text
    elif fig.layout.title is not None and fig.layout.title.text:
        title['text'] = fig.layout.title.text
    if title.get('text'):
        fig.update_layout(title=title)


def _apply_layout(
    fig: go.Figure,
    *,
    width: int | None = None,
    height: int | None = None,
) -> go.Figure:
    """Явно задаём layout: без наследования plotly (none+kotelok)."""
    register()
    layout_kwargs: dict[str, Any] = dict(
        template=f'none+{STYLE_NAME}',
        font=dict(family=FONT, size=12, color=INK_COLOR),
        colorway=COLORWAY,
        paper_bgcolor='#FFFFFF',
        plot_bgcolor='#FFFFFF',
        margin=dict(l=MARGIN_LEFT, r=MARGIN_RIGHT, t=MARGIN_TOP, b=MARGIN_BOTTOM),
        title=dict(_TITLE),
        legend=dict(_LEGEND),
        hoverlabel=dict(
            bgcolor='#FFFFFF',
            bordercolor=INK_COLOR,
            font=dict(family=FONT, size=11, color=INK_COLOR),
        ),
        **_axis_layout(),
    )
    if width is not None:
        layout_kwargs['width'] = width
    if height is not None:
        layout_kwargs['height'] = height
    fig.update_layout(**layout_kwargs)
    _align_title(fig)
    _apply_branding(fig)
    return fig


def apply(
    fig: go.Figure,
    *,
    width: int | None = None,
    height: int | None = None,
) -> go.Figure:
    """Надеть стиль kotelok на готовую фигуру (line/bar/scatter/heatmap).

    Не трогает данные и режимы трейсов: scatter с маркерами останется
    с маркерами, дефолты (линии-сплайны) приходят из шаблона только там,
    где трейc сам ничего не задал.
    """
    return _apply_layout(fig, width=width, height=height)


def line(
    x: Iterable[Any],
    y: Iterable[Any],
    *,
    name: str | None = None,
    color_index: int = 0,
    title: str | None = None,
    width: int | None = None,
    height: int | None = None,
    **kwargs: Any,
) -> go.Figure:
    """Lineplot в стиле kotelok."""
    fig = go.Figure(
        data=[
            go.Scatter(
                x=_to_list(x),
                y=_to_list(y),
                name=name,
                mode='lines',
                line=dict(
                    color=color(color_index),
                    shape='spline',
                    smoothing=1.0,
                    width=3,
                ),
                **kwargs,
            )
        ],
    )
    _apply_layout(fig, width=width, height=height)
    if title is not None:
        _align_title(fig, text=title)
    fig.update_layout(showlegend=False)
    return fig


register()
