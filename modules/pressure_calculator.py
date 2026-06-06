"""
modules/pressure_calculator.py
==============================

Inverse of the standard snowmaking nozzle formula: estimate operating pressure from
flow and total nozzle number.

Derivation (from NN = GPM * sqrt(K / PSI), K = 4000):

    NN / GPM            = sqrt(K / PSI)
    (NN / GPM)^2        = K / PSI
    PSI                 = K * (GPM / NN)^2

Worked example:
    GPM = 6, NN = 14
    PSI = 4000 * (6 / 14)^2 = 734.7  ->  735

IMPORTANT: this is the *theoretical* pressure the nozzle would need to pass
that flow. Real pressure at the pump/gun differs because of hose length,
fittings, elevation, and restrictions. Always measure with a gauge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from . import config


@dataclass
class PressureResult:
    gpm: float
    nozzle_number: float
    psi: float
    warnings: List[str] = field(default_factory=list)


def pressure_psi(gpm: float, nozzle_number: float) -> float:
    """
    Estimated water pressure (PSI).

        PSI = K * (GPM / NN)^2
    """
    if gpm <= 0:
        raise ValueError("GPM must be positive.")
    if nozzle_number <= 0:
        raise ValueError("Nozzle number must be positive.")
    return config.NOZZLE_K * (gpm / nozzle_number) ** 2


def calculate(gpm: float, nozzle_number: float) -> PressureResult:
    """Full pressure calculation with sanity warnings."""
    from . import validation

    warnings: List[str] = []
    warnings += validation.validate_gpm(gpm)
    warnings += validation.validate_nozzle_number(nozzle_number)

    psi = pressure_psi(gpm, nozzle_number)
    warnings += validation.validate_psi(psi)
    warnings.append(
        "This is theoretical nozzle pressure. Real pressure at your pump or "
        "gun will differ due to hose length, fittings, elevation, and "
        "restrictions. Measure with a gauge to confirm."
    )
    return PressureResult(
        gpm=gpm,
        nozzle_number=nozzle_number,
        psi=psi,
        warnings=warnings,
    )
