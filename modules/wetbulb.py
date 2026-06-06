"""
modules/wetbulb.py
==================

Wet bulb temperature calculations + snowmaking quality rating.

Two wet bulb methods are provided:

  Method A - Stull (2011) approximation from temperature + relative humidity.
      Reference: Stull, R. (2011). "Wet-Bulb Temperature from Relative
      Humidity and Air Temperature." J. Applied Meteorology and Climatology.
      The formula is defined for CELSIUS and %RH at roughly sea-level
      pressure, so we convert F -> C, compute, then convert C -> F.

  Method B - Dew point approximation:
      Tw = (2/3) * T + (1/3) * Td
      This is a linear (affine) blend of temperatures, so it gives the same
      answer whether you feed it Fahrenheit or Celsius. We use Fahrenheit.

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
# Method A: Stull (RH-based)
# ---------------------------------------------------------------------------
def wet_bulb_stull_c(temp_c: float, rh_percent: float) -> float:
    """
    Stull wet bulb approximation. Inputs in Celsius / %RH, output in Celsius.

    Tw = T*atan(0.151977*(RH+8.313659)^0.5)
         + atan(T+RH) - atan(RH-1.676331)
         + 0.00391838*RH^1.5*atan(0.023101*RH)
         - 4.686035
    """
    rh = max(1.0, min(100.0, rh_percent))  # formula is unstable at RH<~5%
    t = temp_c
    tw = (
        t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(t + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
        - 4.686035
    )
    return tw


def wet_bulb_stull_f(temp_f: float, rh_percent: float) -> float:
    """Stull wet bulb in Fahrenheit from Fahrenheit + %RH."""
    tw_c = wet_bulb_stull_c(f_to_c(temp_f), rh_percent)
    return c_to_f(tw_c)


# ---------------------------------------------------------------------------
# Method B: Dew point approximation
# ---------------------------------------------------------------------------
def wet_bulb_dewpoint_f(temp_f: float, dewpoint_f: float) -> float:
    """
    Simple dew point wet bulb approximation:  Tw = (2/3)T + (1/3)Td.
    Affine in temperature, so Fahrenheit in -> Fahrenheit out is exact.
    """
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
    Compute wet bulb in Fahrenheit using the best available method.

    method:
      "stull"    -> require RH, use Stull.
      "dewpoint" -> require dew point, use the (2/3,1/3) blend.
      "auto"     -> prefer Stull (RH) if RH is present, else dew point.

    Raises ValueError if the required inputs are missing.
    """
    if method == "stull":
        if rh_percent is None:
            raise ValueError("Stull method requires relative humidity.")
        return wet_bulb_stull_f(temp_f, rh_percent)

    if method == "dewpoint":
        if dewpoint_f is None:
            raise ValueError("Dew point method requires a dew point.")
        return wet_bulb_dewpoint_f(temp_f, dewpoint_f)

    # auto
    if rh_percent is not None:
        return wet_bulb_stull_f(temp_f, rh_percent)
    if dewpoint_f is not None:
        return wet_bulb_dewpoint_f(temp_f, dewpoint_f)
    raise ValueError("Need either relative humidity or dew point to compute wet bulb.")


# ---------------------------------------------------------------------------
# Snowmaking quality rating
# ---------------------------------------------------------------------------
def _thresholds(strict: bool) -> List[Tuple[str, float]]:
    return config.STRICT_THRESHOLDS if strict else config.DETAILED_THRESHOLDS


def rate_wet_bulb(wet_bulb_f_value: float, strict: bool = False) -> str:
    """
    Map a wet bulb temperature (F) to a snowmaking rating key.

    Returns one of the rating keys from config (e.g. config.EXCELLENT).
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
