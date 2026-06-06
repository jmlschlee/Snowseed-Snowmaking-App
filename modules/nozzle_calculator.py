"""
modules/nozzle_calculator.py
============================

Snow State nozzle math + nozzle-combination helper.

Core formula (validated against the published Snow State chart):

    NozzleNumber = GPM * sqrt(K / PSI)        where K = 4000

Worked example:
    GPM = 6, PSI = 700
    NN  = 6 * sqrt(4000 / 700) = 6 * 2.3905 = 14.34  ->  14

The inverse (pressure from nozzle number) lives in pressure_calculator.py.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from . import config


@dataclass
class NozzleResult:
    gpm: float
    psi: float
    nozzle_number: float          # exact, unrounded
    nozzle_number_rounded: float  # snapped to the nearest chart size
    combos: List[List[float]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def nozzle_number(gpm: float, psi: float) -> float:
    """
    Exact nozzle number from GPM and PSI.

        NN = GPM * sqrt(K / PSI)
    """
    if gpm <= 0:
        raise ValueError("GPM must be positive.")
    if psi <= 0:
        raise ValueError("PSI must be positive.")
    return gpm * math.sqrt(config.NOZZLE_K / psi)


def flow_gpm(nozzle_number: float, psi: float) -> float:
    """
    Flow rate (GPM) for a given total nozzle number and pressure - the inverse
    of the nozzle formula, and exactly what the Snow State FLOW chart tabulates.

        gpm = NN * sqrt(PSI / K)

    Verified against the published chart, e.g. NN 6 @ 700 PSI -> 2.5 GPM,
    NN 60 @ 1200 PSI -> 32.9 GPM.
    """
    if nozzle_number <= 0:
        raise ValueError("Nozzle number must be positive.")
    if psi <= 0:
        raise ValueError("PSI must be positive.")
    return nozzle_number * math.sqrt(psi / config.NOZZLE_K)


def flow_chart_rows() -> List[Dict[str, float]]:
    """
    Reproduce the Snow State nozzle FLOW chart: for each chart nozzle size,
    the flow (GPM, 1 decimal) at each standard pressure column, plus orifice.
    """
    rows: List[Dict[str, float]] = []
    for size in _chart_sizes():
        row: Dict[str, float] = {"Nozzle #": size}
        for psi in config.FLOW_CHART_PRESSURES:
            row[f"{psi}"] = round(flow_gpm(size, psi), 1)
        row["Orifice (in)"] = config.NOZZLE_CHART[size]
        rows.append(row)
    return rows


def _chart_sizes() -> List[float]:
    return sorted(config.NOZZLE_CHART.keys())


def nearest_chart_size(target: float) -> float:
    """Snap a nozzle number to the closest available chart size."""
    sizes = _chart_sizes()
    return min(sizes, key=lambda s: abs(s - target))


def suggest_combinations(
    target: float,
    tolerance: float = 0.25,
    max_nozzles: int = 3,
    max_results: int = 8,
) -> List[List[float]]:
    """
    Suggest practical nozzle combinations whose numbers SUM to ~target.

    Nozzle numbers are additive (two #3 nozzles ~= one #6), so we search for
    1..max_nozzles chart sizes whose total is within `tolerance` of target.

    Returns a list of combos (each a sorted list of chart sizes), best
    (closest total, then fewest nozzles) first, de-duplicated.
    """
    if target <= 0:
        return []

    sizes = _chart_sizes()
    found: List[Tuple[float, int, Tuple[float, ...]]] = []
    seen: set = set()

    def recurse(start_idx: int, current: List[float], remaining_depth: int):
        total = sum(current)
        if current and abs(total - target) <= tolerance:
            key = tuple(sorted(current))
            if key not in seen:
                seen.add(key)
                found.append((abs(total - target), len(current), key))
        if remaining_depth == 0:
            return
        for i in range(start_idx, len(sizes)):
            s = sizes[i]
            if total + s > target + tolerance:
                break  # sizes are sorted; nothing smaller-summing ahead
            recurse(i, current + [s], remaining_depth - 1)

    recurse(0, [], max_nozzles)
    found.sort(key=lambda x: (x[0], x[1], x[2]))
    return [list(combo) for _, _, combo in found[:max_results]]


def calculate(
    gpm: float,
    psi: float,
    combo_tolerance: float = 0.25,
) -> NozzleResult:
    """Full nozzle calculation with rounding, combos, and sanity warnings."""
    from . import validation

    warnings: List[str] = []
    warnings += validation.validate_gpm(gpm)
    warnings += validation.validate_psi(psi)

    nn = nozzle_number(gpm, psi)
    nn_rounded = nearest_chart_size(nn)
    combos = suggest_combinations(nn_rounded, tolerance=combo_tolerance)

    return NozzleResult(
        gpm=gpm,
        psi=psi,
        nozzle_number=nn,
        nozzle_number_rounded=nn_rounded,
        combos=combos,
        warnings=warnings,
    )


def orifice_for(nozzle_size: float) -> float | None:
    """Orifice diameter (inches) for an exact chart nozzle size, if known."""
    return config.NOZZLE_CHART.get(nozzle_size)


def chart_rows() -> List[Dict[str, float]]:
    """The full nozzle-number -> orifice-diameter chart as table rows."""
    return [
        {"Nozzle #": size, "Orifice (in)": dia}
        for size, dia in sorted(config.NOZZLE_CHART.items())
    ]
