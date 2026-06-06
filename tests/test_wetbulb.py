"""Tests for wet bulb calculations and snowmaking rating."""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import config  # noqa: E402
from modules import wetbulb as wb  # noqa: E402


def test_unit_conversions_roundtrip():
    for f in (-40, 0, 32, 72, 212):
        assert math.isclose(wb.c_to_f(wb.f_to_c(f)), f, abs_tol=1e-9)
    assert math.isclose(wb.f_to_c(32), 0.0, abs_tol=1e-9)
    assert math.isclose(wb.c_to_f(100), 212.0, abs_tol=1e-9)


def test_dewpoint_blend_is_affine():
    # Tw = (2/3)T + (1/3)Td. With T=Td (saturated), Tw == T.
    assert math.isclose(wb.wet_bulb_dewpoint_f(30, 30), 30.0, abs_tol=1e-9)
    # T=30, Td=15 -> 25
    assert math.isclose(wb.wet_bulb_dewpoint_f(30, 15), 25.0, abs_tol=1e-9)


def test_stull_at_saturation_close_to_air_temp():
    # At 100% RH, wet bulb ~= dry bulb. Stull approximation is within ~1F.
    tw = wb.wet_bulb_stull_f(30.0, 100.0)
    assert abs(tw - 30.0) < 1.5


def test_stull_below_air_temp_when_dry():
    # Drier air -> wet bulb meaningfully below dry bulb.
    tw = wb.wet_bulb_stull_f(30.0, 50.0)
    assert tw < 30.0


def test_wet_bulb_f_auto_is_psychrometric():
    # auto should use the accurate psychrometric method when RH is present.
    via_auto = wb.wet_bulb_f(30.0, rh_percent=50.0, dewpoint_f=10.0, method="auto")
    via_psy = wb.wet_bulb_psychrometric_f(30.0, 50.0)
    assert math.isclose(via_auto, via_psy, abs_tol=1e-9)


# --- Validate the psychrometric method against published Snow State cells ---
# (temp_F, RH%, chart wet bulb F). These are read directly from the official
# Snow State Wet Bulb Temperature Chart.
SNOW_STATE_CELLS = [
    (14, 20, 9),
    (14, 100, 14),
    (20, 20, 14),
    (27, 50, 23),
    (30, 50, 25),
    (30, 100, 30),
    (38, 100, 38),
    (24, 40, 20),
]


def test_psychrometric_matches_snow_state_chart():
    for temp, rh, expected in SNOW_STATE_CELLS:
        got = wb.chart_value(temp, rh)
        assert abs(got - expected) <= 1, (
            f"{temp}F/{rh}% -> got {got}, chart says {expected}"
        )


def test_psychrometric_beats_stull_in_cold_dry_air():
    # At 14F/20% the chart says 9F. Psychrometric should be much closer than Stull.
    psy = wb.wet_bulb_psychrometric_f(14, 20)
    stull = wb.wet_bulb_stull_f(14, 20)
    assert abs(psy - 9) < abs(stull - 9)


def test_chart_invariants():
    temps, rhs, grid = wb.build_wetbulb_chart()
    # At 100% RH wet bulb equals dry bulb.
    assert rhs[-1] == 100
    for i, t in enumerate(temps):
        assert abs(grid[i][-1] - t) <= 1
        # Each row is non-decreasing left (dry) to right (humid).
        for j in range(1, len(rhs)):
            assert grid[i][j] >= grid[i][j - 1] - 0  # monotonic non-decreasing


def test_saturation_vapor_pressure():
    # e_s at 0C ~ 0.6108 kPa.
    assert math.isclose(wb.saturation_vapor_pressure_kpa(0.0), 0.6108, abs_tol=1e-4)


def test_rh_from_dewpoint():
    # Dew point == temp -> 100% RH.
    assert math.isclose(wb.rh_from_dewpoint(30, 30), 100.0, abs_tol=0.5)
    # Lower dew point -> lower RH.
    assert wb.rh_from_dewpoint(30, 10) < 100.0


def test_rating_detailed_mode():
    assert wb.rate_wet_bulb(18, strict=False) == config.EXCELLENT
    assert wb.rate_wet_bulb(20, strict=False) == config.EXCELLENT
    assert wb.rate_wet_bulb(22, strict=False) == config.GOOD
    assert wb.rate_wet_bulb(26, strict=False) == config.MARGINAL
    assert wb.rate_wet_bulb(28, strict=False) == config.BORDERLINE
    assert wb.rate_wet_bulb(30, strict=False) == config.TOO_WARM


def test_rating_strict_mode():
    assert wb.rate_wet_bulb(27, strict=True) == config.POSSIBLE
    assert wb.rate_wet_bulb(28, strict=True) == config.BORDERLINE
    assert wb.rate_wet_bulb(29, strict=True) == config.TOO_WARM


def test_missing_inputs_raise():
    import pytest

    with pytest.raises(ValueError):
        wb.wet_bulb_f(30.0, method="auto")  # no RH, no dew point
