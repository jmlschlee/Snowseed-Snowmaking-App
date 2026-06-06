"""
modules/bucket_test.py
======================

Bucket-test flow rate (GPM) from a fill-time measurement.

    GPM = (bucket_gallons * 60) / fill_time_seconds

For a 5-gallon bucket:  GPM = 300 / seconds.

Worked example:
    5-gallon bucket fills in 30 s -> 300 / 30 = 10 GPM
    5-gallon bucket fills in 60 s -> 300 / 60 =  5 GPM
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from . import config


@dataclass
class BucketResult:
    bucket_gallons: float
    fill_time_seconds: float
    gpm: float
    warnings: List[str] = field(default_factory=list)


def gpm_from_bucket(bucket_gallons: float, fill_time_seconds: float) -> float:
    """GPM = (gallons * 60) / seconds."""
    if bucket_gallons <= 0:
        raise ValueError("Bucket size must be positive.")
    if fill_time_seconds <= 0:
        raise ValueError("Fill time must be positive.")
    return (bucket_gallons * 60.0) / fill_time_seconds


def calculate(
    fill_time_seconds: float,
    bucket_gallons: float = config.DEFAULT_BUCKET_GALLONS,
) -> BucketResult:
    """Full bucket-test calculation with basic warnings."""
    from . import validation

    warnings: List[str] = []
    warnings += validation.validate_positive(bucket_gallons, "Bucket size")
    warnings += validation.validate_positive(fill_time_seconds, "Fill time")

    gpm = gpm_from_bucket(bucket_gallons, fill_time_seconds)

    if fill_time_seconds < 3:
        warnings.append(
            "Very short fill time - timing error has a big effect. "
            "Use a bigger bucket or time several fills and average."
        )
    return BucketResult(
        bucket_gallons=bucket_gallons,
        fill_time_seconds=fill_time_seconds,
        gpm=gpm,
        warnings=warnings,
    )
