"""Tests for the nozzle calculator math (standard snowmaking formula)."""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import nozzle_calculator as nc  # noqa: E402


def test_nozzle_6gpm_700psi():
    # NN = 6 * sqrt(4000/700) = 14.34...
    nn = nc.nozzle_number(6, 700)
    assert math.isclose(nn, 14.345, abs_tol=0.01)
    assert round(nn) == 14


def test_nozzle_2p5gpm_700psi():
    # NN = 2.5 * sqrt(4000/700) = 5.977...
    nn = nc.nozzle_number(2.5, 700)
    assert math.isclose(nn, 5.977, abs_tol=0.01)
    assert round(nn) == 6


def test_nearest_chart_size():
    # 14.345 sits between chart sizes 13 and 15; 15 is closer (|0.655| < |1.345|).
    assert nc.nearest_chart_size(14.345) == 15.0
    assert nc.nearest_chart_size(5.977) == 6.0
    # exact chart sizes snap to themselves
    assert nc.nearest_chart_size(6.0) == 6.0


def test_combinations_sum_to_target():
    combos = nc.suggest_combinations(6.0, tolerance=0.0)
    assert combos, "expected at least one exact combo for target 6"
    for combo in combos:
        assert math.isclose(sum(combo), 6.0, abs_tol=1e-9)
    # one #6 nozzle should be among the suggestions
    assert [6.0] in combos


def test_combinations_include_multi():
    combos = nc.suggest_combinations(6.0, tolerance=0.0, max_nozzles=3)
    sums = [tuple(c) for c in combos]
    # two #3 nozzles (3+3) and #4+#2 etc. should be reachable
    assert (3.0, 3.0) in sums


def test_calculate_full():
    res = nc.calculate(6, 700)
    assert round(res.nozzle_number) == 14
    assert res.nozzle_number_rounded in nc._chart_sizes()


def test_invalid_inputs_raise():
    import pytest

    with pytest.raises(ValueError):
        nc.nozzle_number(0, 700)
    with pytest.raises(ValueError):
        nc.nozzle_number(6, 0)


# --- Flow lookup (gpm = NN * sqrt(PSI/4000)) vs published snowmaking chart ---
# (nozzle_number, PSI, chart GPM) read from the nozzle flow chart.
FLOW_CELLS = [
    (6, 700, 2.5),
    (1, 100, 0.2),
    (25, 500, 8.8),
    (60, 1200, 32.9),
    (40, 100, 6.3),
    (15, 700, 6.3),
    (13, 700, 5.4),
]


def test_flow_matches_published_chart():
    for nn, psi, expected in FLOW_CELLS:
        got = round(nc.flow_gpm(nn, psi), 1)
        assert abs(got - expected) <= 0.1, f"NN{nn}@{psi} -> {got}, chart {expected}"


def test_flow_inverts_nozzle_number():
    # nozzle_number(gpm, psi) and flow_gpm(nn, psi) are inverses.
    nn = nc.nozzle_number(6, 700)
    assert math.isclose(nc.flow_gpm(nn, 700), 6.0, abs_tol=1e-9)


def test_flow_invalid_inputs_raise():
    import pytest

    with pytest.raises(ValueError):
        nc.flow_gpm(0, 700)
    with pytest.raises(ValueError):
        nc.flow_gpm(6, 0)
