"""
modules/pump_calculator.py
==========================

Pump / motor horsepower math using standard hydraulic horsepower.

    Hydraulic HP        = (GPM * TotalPSI) / 1714
    Brake (pump) HP     = Hydraulic HP / pump_efficiency
    Electric HP         = Hydraulic HP / (pump_efficiency * motor_efficiency)
    Recommended HP      = Electric HP * (1 + safety_margin)

Where:
    TotalPSI = desired gun PSI + estimated plumbing loss PSI

Worked example:
    GPM = 6, desired PSI = 700, plumbing loss = 0
    Hydraulic HP = 6 * 700 / 1714 = 2.45 HP
    Electric HP  = 2.45 / (0.60 * 0.85) = 4.80 HP
    + 20% margin = 5.76 HP  -> recommend a 6 HP motor minimum
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List

from . import config


@dataclass
class PumpResult:
    gpm: float
    desired_psi: float
    plumbing_loss_psi: float
    total_psi: float
    pump_efficiency: float
    motor_efficiency: float
    safety_margin: float
    hydraulic_hp: float
    brake_hp: float
    electric_hp: float
    recommended_hp: float          # electric_hp * (1 + safety_margin)
    recommended_motor_hp: float    # rounded up to a practical motor size
    warnings: List[str] = field(default_factory=list)


def hydraulic_hp(gpm: float, total_psi: float) -> float:
    """Hydraulic horsepower = (GPM * PSI) / 1714."""
    return (gpm * total_psi) / config.HP_CONSTANT


def round_up_to_motor(hp: float) -> float:
    """
    Practical minimum motor size: round the required HP UP to the next whole
    horsepower (e.g. 5.76 -> 6 HP minimum, matching the worked example).
    Sub-1 HP keeps a 0.25 HP granularity so tiny pumps aren't over-spec'd.
    """
    if hp <= 0:
        return 0.0
    if hp < 1.0:
        return math.ceil(hp * 4.0) / 4.0  # 0.25 HP steps under 1 HP
    return float(math.ceil(hp))


def calculate(
    gpm: float,
    desired_psi: float,
    pump_efficiency: float = config.DEFAULT_PUMP_EFFICIENCY,
    motor_efficiency: float = config.DEFAULT_MOTOR_EFFICIENCY,
    plumbing_loss_psi: float = config.DEFAULT_PLUMBING_LOSS_PSI,
    safety_margin: float = config.DEFAULT_SAFETY_MARGIN,
) -> PumpResult:
    """Full pump horsepower calculation with safety margin and warnings."""
    from . import validation

    warnings: List[str] = []
    warnings += validation.validate_gpm(gpm)
    warnings += validation.validate_positive(desired_psi, "Desired PSI")
    warnings += validation.validate_efficiency(pump_efficiency, "Pump efficiency")
    warnings += validation.validate_efficiency(motor_efficiency, "Motor efficiency")
    if plumbing_loss_psi < 0:
        warnings.append("Plumbing loss PSI cannot be negative.")
    if safety_margin < 0:
        warnings.append("Safety margin cannot be negative.")

    total_psi = desired_psi + max(0.0, plumbing_loss_psi)

    hyd = hydraulic_hp(gpm, total_psi)
    brake = hyd / pump_efficiency
    electric = hyd / (pump_efficiency * motor_efficiency)
    recommended = electric * (1.0 + safety_margin)
    recommended_motor = round_up_to_motor(recommended)

    if electric > config.HP_SANITY_WARN:
        warnings.append(
            f"Estimated electric HP ({electric:.1f}) is very high for a home "
            "setup. Double-check your GPM and PSI - you may be over-spec'd."
        )

    return PumpResult(
        gpm=gpm,
        desired_psi=desired_psi,
        plumbing_loss_psi=plumbing_loss_psi,
        total_psi=total_psi,
        pump_efficiency=pump_efficiency,
        motor_efficiency=motor_efficiency,
        safety_margin=safety_margin,
        hydraulic_hp=hyd,
        brake_hp=brake,
        electric_hp=electric,
        recommended_hp=recommended,
        recommended_motor_hp=recommended_motor,
        warnings=warnings,
    )
