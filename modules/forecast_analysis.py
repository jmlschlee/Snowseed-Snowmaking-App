"""
modules/forecast_analysis.py
============================

Turn raw hourly forecast data into snowmaking-friendly daily/overnight
summaries: wet bulb per hour, best overnight window, rating, and a
plain-English recommendation.

A "snowmaking night" is keyed by the DATE the evening starts on. The default
overnight window is 6 PM -> 9 AM next morning (see config). For each night we
find the hour with the LOWEST wet bulb (best instant) and summarize.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from . import config, wetbulb
from .weather import Forecast, HourlyPoint


@dataclass
class HourlyAnalysis:
    time: datetime
    temp_f: float
    humidity_pct: Optional[float]
    dewpoint_f: Optional[float]
    wind_mph: Optional[float]
    wet_bulb_f: float
    rating: str


@dataclass
class NightSummary:
    date: datetime                 # the evening's calendar date
    label: str                     # e.g. "Mon Jan 12"
    window_start: datetime
    window_end: datetime
    best_time: datetime            # hour of lowest wet bulb
    min_wet_bulb_f: float
    temp_at_best_f: float
    humidity_at_best: Optional[float]
    wind_at_best: Optional[float]
    rating: str
    rating_label: str
    recommendation: str
    hours: List[HourlyAnalysis] = field(default_factory=list)


def _parse_iso(ts: str) -> datetime:
    # Open-Meteo returns local naive ISO like "2026-01-12T23:00"
    return datetime.fromisoformat(ts)


def analyze_hour(point: HourlyPoint, strict: bool, method: str) -> HourlyAnalysis:
    wb = wetbulb.wet_bulb_f(
        temp_f=point.temp_f,
        rh_percent=point.humidity_pct,
        dewpoint_f=point.dewpoint_f,
        method=method,
    )
    return HourlyAnalysis(
        time=_parse_iso(point.time_iso),
        temp_f=point.temp_f,
        humidity_pct=point.humidity_pct,
        dewpoint_f=point.dewpoint_f,
        wind_mph=point.wind_mph,
        wet_bulb_f=wb,
        rating=wetbulb.rate_wet_bulb(wb, strict=strict),
    )


def _belongs_to_night(t: datetime) -> Optional[datetime]:
    """
    Return the 'evening date' a timestamp belongs to within the overnight
    window, or None if it's a daytime hour outside the window.

    Window is [OVERNIGHT_START_HOUR .. midnight) on day D plus
    [midnight .. OVERNIGHT_END_HOUR) on day D+1, all keyed to day D.
    """
    start = config.OVERNIGHT_START_HOUR
    end = config.OVERNIGHT_END_HOUR
    if t.hour >= start:
        return datetime(t.year, t.month, t.day)
    if t.hour < end:
        prev = t - timedelta(days=1)
        return datetime(prev.year, prev.month, prev.day)
    return None


def _recommendation(night: "NightSummary", all_min_wb: List[float]) -> str:
    r = night.rating
    parts: List[str] = []

    start_s = night.window_start.strftime("%a %-I %p")
    end_s = night.window_end.strftime("%a %-I %p")
    best_s = night.best_time.strftime("%a %-I %p")

    parts.append(
        f"Best window: {start_s} - {end_s}. Lowest wet bulb ~{night.min_wet_bulb_f:.0f}F "
        f"around {best_s}."
    )
    parts.append(wetbulb.rating_explanation(r))

    # Is this one of the best nights in the forecast?
    if all_min_wb and night.min_wet_bulb_f <= min(all_min_wb) + 0.5 and r in (
        config.EXCELLENT,
        config.GOOD,
        config.POSSIBLE,
    ):
        parts.append("This is likely one of the best snowmaking windows in the forecast.")

    # Wind caution
    if night.wind_at_best is not None and night.wind_at_best >= config.WIND_CAUTION_MPH:
        parts.append(
            f"Heads up: ~{night.wind_at_best:.0f} mph wind at the best hour - wind hurts "
            "hang time and snow quality. Calmer is better."
        )
    return " ".join(p for p in parts if p)


def summarize_nights(
    forecast: Forecast,
    strict: bool = False,
    method: str = "auto",
) -> List[NightSummary]:
    """
    Group the forecast into overnight snowmaking windows and summarize each.
    Returns nights in chronological order.
    """
    # Analyze every hour first.
    analyzed = [analyze_hour(p, strict=strict, method=method) for p in forecast.hourly]

    # Bucket hours into nights.
    nights: dict = {}
    for ha in analyzed:
        key = _belongs_to_night(ha.time)
        if key is None:
            continue
        nights.setdefault(key, []).append(ha)

    summaries: List[NightSummary] = []
    for date_key in sorted(nights.keys()):
        hours = sorted(nights[date_key], key=lambda h: h.time)
        if not hours:
            continue
        best = min(hours, key=lambda h: h.wet_bulb_f)
        rating = wetbulb.rate_wet_bulb(best.wet_bulb_f, strict=strict)
        summary = NightSummary(
            date=date_key,
            label=date_key.strftime("%a %b %-d"),
            window_start=hours[0].time,
            window_end=hours[-1].time,
            best_time=best.time,
            min_wet_bulb_f=best.wet_bulb_f,
            temp_at_best_f=best.temp_f,
            humidity_at_best=best.humidity_pct,
            wind_at_best=best.wind_mph,
            rating=rating,
            rating_label=wetbulb.rating_label(rating),
            recommendation="",  # filled below
            hours=hours,
        )
        summaries.append(summary)

    all_min = [s.min_wet_bulb_f for s in summaries]
    for s in summaries:
        s.recommendation = _recommendation(s, all_min)

    return summaries


def can_make_snow_this_week(nights: List[NightSummary]) -> bool:
    """True if any night rates better than 'too warm'."""
    return any(n.rating != config.TOO_WARM for n in nights)
