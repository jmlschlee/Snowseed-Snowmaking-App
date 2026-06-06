"""
modules/wetbulb.py
==================

Wet bulb temperature calculations + snowmaking quality rating.

THREE wet bulb methods are provided, in order of accuracy:

  Method P - Psychrometric (DEFAULT, matches the Snow State chart).
      Solves the psychrometer equation iteratively:
          e_actual = e_s(Tw) - gamma * (T - Tw)
      where e_s() is saturation vapor pressure (Tetens, over water) and
      gamma is the psychrometric constant (~0.000665 * P). This is the
      physically correct wet bulb and reproduces the Snow State Wet Bulb
      Temperature Chart to within rounding (e.g. 14F/20%RH -> 9F, 30F/50% ->
      25F). Stull is notably off in the cold, dry air typical of snowmaking,
      so psychrometric is the default.

  Method A - Stull (2011) approximation from temperature + relative humidity.
      Fast closed-form approximation; kept as an option for comparison. Least
      accurate in cold/dry conditions, so NOT the default.

  Method B - Dew point approximation:
      Tw = (2/3) * T + (1/3) * Td   (rough linear blend, kept for transparency)

All public functions take and return DEGREES FAHRENHEIT unless noted.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from . import config


# ---------------------------------------------------------------------------
# Temperature unit helpers
# ---------------------------------------------------------------------------
def f_to_c(temp_f: float) -> float:
    """Fahrenheit -> Celsius."""
    return (temp_f - 32.0) * 5.0 / 9.0


def c_to_f(temp_c: float) -> float:
    """Celsius -> Fahrenheit."""
    return temp_c * 9.0 / 5.0 + 32.0


# ---------------------------------------------------------------------------
# Vapor pressure (Tetens formula, over water) and humidity helpers
# ---------------------------------------------------------------------------
def saturation_vapor_pressure_kpa(temp_c: float) -> float:
    """Saturation vapor pressure (kPa) over water via the Tetens equation."""
    return 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))


def rh_from_dewpoint(temp_f: float, dewpoint_f: float) -> float:
    """Relative humidity (%) from air temp and dew point (both F)."""
    t_c = f_to_c(temp_f)
    td_c = f_to_c(dewpoint_f)
    rh = 100.0 * saturation_vapor_pressure_kpa(td_c) / saturation_vapor_pressure_kpa(t_c)
    return max(1.0, min(100.0, rh))


# ---------------------------------------------------------------------------
# Method P: Psychrometric (default)
# ---------------------------------------------------------------------------
def wet_bulb_psychrometric_c(
    temp_c: float,
    rh_percent: float,
    pressure_kpa: float = config.STANDARD_PRESSURE_KPA,
) -> float:
    """
    Psychrometric wet bulb (Celsius) solved by bisection.

    f(Tw) = e_s(Tw) - gamma*(T - Tw) - e_actual  is monotonically increasing
    in Tw, with f(T) >= 0 and f(very cold) < 0, so bisection is robust.
    """
    rh = max(1.0, min(100.0, rh_percent))
    e_actual = (rh / 100.0) * saturation_vapor_pressure_kpa(temp_c)
    gamma = 0.000665 * pressure_kpa  # kPa/C

    def f(tw: float) -> float:
        return saturation_vapor_pressure_kpa(tw) - gamma * (temp_c - tw) - e_actual

    lo, hi = -80.0, temp_c
    # Guard: if even at lo f>=0 (extremely dry/cold edge), clamp.
    if f(lo) > 0:
        return lo
    for _ in range(100):
        mid = (lo + hi) / 2.0
        if f(mid) > 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


def wet_bulb_psychrometric_f(
    temp_f: float,
    rh_percent: float,
    pressure_kpa: float = config.STANDARD_PRESSURE_KPA,
) -> float:
    """Psychrometric wet bulb (Fahrenheit) from Fahrenheit + %RH."""
    return c_to_f(wet_bulb_psychrometric_c(f_to_c(temp_f), rh_percent, pressure_kpa))


# ---------------------------------------------------------------------------
# Method A: Stull (RH-based approximation)
# ---------------------------------------------------------------------------
def wet_bulb_stull_c(temp_c: float, rh_percent: float) -> float:
    """Stull (2011) wet bulb approximation. Celsius / %RH in, Celsius out."""
    rh = max(1.0, min(100.0, rh_percent))
    t = temp_c
    return (
        t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(t + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
        - 4.686035
    )


def wet_bulb_stull_f(temp_f: float, rh_percent: float) -> float:
    """Stull wet bulb in Fahrenheit from Fahrenheit + %RH."""
    return c_to_f(wet_bulb_stull_c(f_to_c(temp_f), rh_percent))


# ---------------------------------------------------------------------------
# Method B: Dew point approximation
# ---------------------------------------------------------------------------
def wet_bulb_dewpoint_f(temp_f: float, dewpoint_f: float) -> float:
    """Simple dew point wet bulb approximation: Tw = (2/3)T + (1/3)Td."""
    return (2.0 / 3.0) * temp_f + (1.0 / 3.0) * dewpoint_f


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------
def wet_bulb_f(
    temp_f: float,
    rh_percent: float | None = None,
    dewpoint_f: float | None = None,
    method: str = "auto",
) -> float:
    """
    Compute wet bulb in Fahrenheit using the requested method.

    method:
      "psychrometric" -> accurate iterative solver (needs RH, or dew point
                         which is converted to RH). DEFAULT for "auto".
      "stull"         -> Stull approximation (needs RH).
      "dewpoint"      -> (2/3,1/3) blend (needs dew point).
      "auto"          -> psychrometric using RH if present, else convert dew
                         point to RH and use psychrometric, else error.

    Raises ValueError if the required inputs are missing.
    """
    if method == "psychrometric" or method == "auto":
        if rh_percent is not None:
            return wet_bulb_psychrometric_f(temp_f, rh_percent)
        if dewpoint_f is not None:
            return wet_bulb_psychrometric_f(temp_f, rh_from_dewpoint(temp_f, dewpoint_f))
        raise ValueError("Psychrometric method needs relative humidity or dew point.")

    if method == "stull":
        if rh_percent is None:
            raise ValueError("Stull method requires relative humidity.")
        return wet_bulb_stull_f(temp_f, rh_percent)

    if method == "dewpoint":
        if dewpoint_f is None:
            raise ValueError("Dew point method requires a dew point.")
        return wet_bulb_dewpoint_f(temp_f, dewpoint_f)

    raise ValueError(f"Unknown wet bulb method: {method}")


# ---------------------------------------------------------------------------
# Snow State Wet Bulb Temperature Chart (generated from the psychrometric
# method, which matches the published chart). Returned as integer F like the
# chart. Validated against published cells in tests/test_wetbulb_chart.py.
# ---------------------------------------------------------------------------
def chart_value(temp_f: int, rh_percent: int) -> int:
    """The Snow State chart's wet bulb (rounded F) for a (temp, RH) cell."""
    return round(wet_bulb_psychrometric_f(float(temp_f), float(rh_percent)))


def build_wetbulb_chart() -> Tuple[List[int], List[int], List[List[int]]]:
    """
    Return (temps_F, rh_columns, grid) reproducing the Snow State chart.
    grid[i][j] = wet bulb (F) at temps_F[i], rh_columns[j].
    """
    temps = config.WETBULB_CHART_TEMPS_F
    rhs = config.WETBULB_CHART_RH
    grid = [[chart_value(t, rh) for rh in rhs] for t in temps]
    return temps, rhs, grid


# ---------------------------------------------------------------------------
# Snowmaking quality rating
# ---------------------------------------------------------------------------
def _thresholds(strict: bool) -> List[Tuple[str, float]]:
    return config.STRICT_THRESHOLDS if strict else config.DETAILED_THRESHOLDS


def rate_wet_bulb(wet_bulb_f_value: float, strict: bool = False) -> str:
    """
    Map a wet bulb temperature (F) to a snowmaking rating key.

    Thresholds follow the Snow State chart (Borderline = 28F, Too Warm >= 29F).
    Anything warmer than the last threshold is config.TOO_WARM.
    """
    for rating, upper in _thresholds(strict):
        if wet_bulb_f_value <= upper:
            return rating
    return config.TOO_WARM


def rating_label(rating_key: str) -> str:
    return config.RATING_LABELS.get(rating_key, rating_key)


def rating_color(rating_key: str) -> str:
    return config.RATING_COLORS.get(rating_key, "#777777")


def rating_explanation(rating_key: str) -> str:
    return config.RATING_EXPLANATIONS.get(rating_key, "")


def rating_score(rating_key: str) -> int:
    return config.RATING_SCORE.get(rating_key, 0)
