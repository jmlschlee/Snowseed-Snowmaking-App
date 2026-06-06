"""Tests for the pump horsepower calculator."""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import pump_calculator as pp  # noqa: E402


def test_hydraulic_hp_6gpm_700psi():
    # Hydraulic HP = 6 * 700 / 1714 = 2.449...
    hp = pp.hydraulic_hp(6, 700)
    assert math.isclose(hp, 2.449, abs_tol=0.01)


def test_electric_hp_with_efficiencies():
    # Electric HP = 2.449 / (0.60 * 0.85) = 4.802
    res = pp.calculate(6, 700, pump_efficiency=0.60, motor_efficiency=0.85,
                       safety_margin=0.20)
    assert math.isclose(res.hydraulic_hp, 2.449, abs_tol=0.01)
    assert math.isclose(res.electric_hp, 4.802, abs_tol=0.01)
    # + 20% margin = 5.76
    assert math.isclose(res.recommended_hp, 5.763, abs_tol=0.01)
    # Practical recommendation rounds up to the next whole HP -> 6 HP minimum,
    # matching the worked example in the spec.
    assert res.recommended_motor_hp == 6.0
    assert res.recommended_motor_hp >= res.recommended_hp


def test_plumbing_loss_adds_to_total_psi():
    res = pp.calculate(6, 700, plumbing_loss_psi=100)
    assert res.total_psi == 800
    assert math.isclose(res.hydraulic_hp, 6 * 800 / 1714, abs_tol=1e-6)


def test_round_up_to_motor():
    assert pp.round_up_to_motor(5.76) == 6.0
    assert pp.round_up_to_motor(2.45) == 3.0
    assert pp.round_up_to_motor(0.4) == 0.5
    assert pp.round_up_to_motor(6.0) == 6.0


def test_high_hp_warning():
    res = pp.calculate(50, 1000)  # absurd for a home setup
    assert any("high" in w.lower() for w in res.warnings)
