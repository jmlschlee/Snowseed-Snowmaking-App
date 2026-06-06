"""Tests for the pressure calculator (inverse Snow State formula)."""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import nozzle_calculator as nc  # noqa: E402
from modules import pressure_calculator as pc  # noqa: E402


def test_pressure_6gpm_nn14():
    # PSI = 4000 * (6/14)^2 = 734.69...
    psi = pc.pressure_psi(6, 14)
    assert math.isclose(psi, 734.69, abs_tol=0.5)
    assert round(psi) == 735


def test_pressure_2p5gpm_nn6():
    # PSI = 4000 * (2.5/6)^2 = 694.44...
    psi = pc.pressure_psi(2.5, 6)
    assert math.isclose(psi, 694.44, abs_tol=0.5)
    assert round(psi) == 694


def test_inverse_roundtrip():
    # nozzle_number then pressure should recover the original PSI.
    nn = nc.nozzle_number(6, 700)
    psi = pc.pressure_psi(6, nn)
    assert math.isclose(psi, 700, abs_tol=1e-6)


def test_calculate_full_has_warning():
    res = pc.calculate(6, 14)
    assert round(res.psi) == 735
    assert any("theoretical" in w.lower() for w in res.warnings)


def test_invalid_inputs_raise():
    import pytest

    with pytest.raises(ValueError):
        pc.pressure_psi(0, 14)
    with pytest.raises(ValueError):
        pc.pressure_psi(6, 0)
