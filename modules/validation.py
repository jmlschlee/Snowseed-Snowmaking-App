"""
modules/validation.py
=====================

Small, reusable input validators. Each returns a list of human-readable
warning/error strings (empty list == all good). Keeping validation separate
keeps the calculators clean and the UI consistent.
"""

from __future__ import annotations

from typing import List

from . import config


def validate_positive(value: float, name: str) -> List[str]:
    msgs: List[str] = []
    if value is None:
        msgs.append(f"{name} is required.")
    elif value <= 0:
        msgs.append(f"{name} must be greater than zero.")
    return msgs


def validate_psi(psi: float) -> List[str]:
    msgs = validate_positive(psi, "PSI")
    if not msgs:
        if psi < config.PSI_MIN_TYPICAL:
            msgs.append(
                f"{psi:.0f} PSI is below the typical snow-gun range "
                f"({config.PSI_MIN_TYPICAL:.0f}-{config.PSI_MAX_TYPICAL:.0f} PSI)."
            )
        elif psi > config.PSI_MAX_TYPICAL:
            msgs.append(
                f"{psi:.0f} PSI is above the typical snow-gun range "
                f"({config.PSI_MIN_TYPICAL:.0f}-{config.PSI_MAX_TYPICAL:.0f} PSI)."
            )
    return msgs


def validate_gpm(gpm: float) -> List[str]:
    return validate_positive(gpm, "GPM")


def validate_nozzle_number(nn: float) -> List[str]:
    return validate_positive(nn, "Nozzle number")


def validate_efficiency(value: float, name: str) -> List[str]:
    msgs: List[str] = []
    if value is None or value <= 0:
        msgs.append(f"{name} must be greater than 0%.")
    elif value > 1.0:
        msgs.append(f"{name} cannot exceed 100%.")
    return msgs


def validate_zip(zip_code: str) -> List[str]:
    msgs: List[str] = []
    z = (zip_code or "").strip()
    if not z:
        msgs.append("Please enter a ZIP code.")
    elif not (len(z) == 5 and z.isdigit()):
        msgs.append("Enter a valid 5-digit US ZIP code (e.g. 80424).")
    return msgs
