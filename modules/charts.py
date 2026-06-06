"""
modules/charts.py
=================

Plotly chart builders for the forecast view. Kept separate so the app code
stays focused on layout and the charts stay easy to restyle.
"""

from __future__ import annotations

from typing import List

import plotly.graph_objects as go

from . import config, wetbulb
from .forecast_analysis import NightSummary


def night_quality_bar(nights: List[NightSummary]) -> go.Figure:
    """
    Bar chart ranking each night by its lowest (best) wet bulb temperature,
    colored by snowmaking rating. Lower bars = colder = better snow.
    """
    labels = [n.label for n in nights]
    values = [round(n.min_wet_bulb_f, 1) for n in nights]
    colors = [wetbulb.rating_color(n.rating) for n in nights]
    text = [f"{v:.0f}F<br>{n.rating_label}" for v, n in zip(values, nights)]

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=colors,
            text=text,
            textposition="outside",
            hovertemplate="%{x}<br>Min wet bulb: %{y:.1f}F<extra></extra>",
        )
    )

    # Threshold reference lines (detailed-mode bounds).
    for rating, bound in config.DETAILED_THRESHOLDS:
        fig.add_hline(
            y=bound,
            line_dash="dot",
            line_color=wetbulb.rating_color(rating),
            opacity=0.4,
            annotation_text=f"{wetbulb.rating_label(rating)} <= {bound:.0f}F",
            annotation_position="right",
            annotation_font_size=10,
        )

    fig.update_layout(
        title="Snowmaking outlook by night (lowest wet bulb)",
        yaxis_title="Lowest wet bulb (F)",
        xaxis_title="Night (evening date)",
        margin=dict(l=10, r=120, t=50, b=10),
        height=420,
        plot_bgcolor="white",
        showlegend=False,
    )
    fig.update_yaxes(gridcolor="#eee", zeroline=False)
    return fig


def wetbulb_reference_chart() -> go.Figure:
    """
    Reproduce the wet bulb temperature chart as a heatmap, colored
    by snowmaking rating (computed via the psychrometric method that matches
    the published chart). Rows = air temp (F), columns = relative humidity (%).
    """
    temps, rhs, grid = wetbulb.build_wetbulb_chart()

    # Map each cell's wet bulb -> rating score for coloring.
    score = [[wetbulb.rating_score(wetbulb.rate_wet_bulb(v)) for v in row] for row in grid]
    text = [[str(v) for v in row] for row in grid]

    # Discrete colorscale from Too Warm (low score) to Great (high score).
    colorscale = [
        [0.00, config.RATING_COLORS[config.TOO_WARM]],
        [0.25, config.RATING_COLORS[config.BORDERLINE]],
        [0.50, config.RATING_COLORS[config.MARGINAL]],
        [0.75, config.RATING_COLORS[config.GOOD]],
        [1.00, config.RATING_COLORS[config.EXCELLENT]],
    ]

    fig = go.Figure(
        go.Heatmap(
            z=score,
            x=[f"{rh}%" for rh in rhs],
            y=[str(t) for t in temps],
            text=text,
            texttemplate="%{text}",
            textfont={"size": 10, "color": "white"},
            colorscale=colorscale,
            showscale=False,
            hovertemplate="Air %{y}F, RH %{x}<br>Wet bulb %{text}F<extra></extra>",
        )
    )
    fig.update_layout(
        title="Wet Bulb Chart (wet bulb F by air temp & humidity)",
        xaxis_title="Relative humidity",
        yaxis_title="Air temperature (F)",
        height=560,
        margin=dict(l=10, r=10, t=50, b=10),
    )
    fig.update_yaxes(autorange="reversed")  # coldest at top, like the chart
    return fig


def hourly_wetbulb_line(night: NightSummary) -> go.Figure:
    """Hour-by-hour wet bulb and air temperature for a single night."""
    times = [h.time.strftime("%-I %p") for h in night.hours]
    wb = [round(h.wet_bulb_f, 1) for h in night.hours]
    air = [round(h.temp_f, 1) for h in night.hours]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=times, y=wb, mode="lines+markers", name="Wet bulb (F)",
            line=dict(color="#1565C0", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=times, y=air, mode="lines+markers", name="Air temp (F)",
            line=dict(color="#9E9E9E", width=2, dash="dash"),
        )
    )
    # Borderline snowmaking line at 28 F.
    fig.add_hline(
        y=28, line_dash="dot", line_color="#EF6C00", opacity=0.6,
        annotation_text="28F snowmaking limit", annotation_position="top left",
        annotation_font_size=10,
    )
    fig.update_layout(
        title=f"Hourly detail - {night.label}",
        yaxis_title="Temperature (F)",
        xaxis_title="Hour (local)",
        margin=dict(l=10, r=10, t=50, b=10),
        height=360,
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_yaxes(gridcolor="#eee")
    return fig
