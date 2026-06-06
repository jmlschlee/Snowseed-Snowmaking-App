"""Tests for the bucket-test GPM calculator."""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules import bucket_test as bt  # noqa: E402


def test_5gal_30s_is_10gpm():
    assert math.isclose(bt.gpm_from_bucket(5, 30), 10.0, abs_tol=1e-9)


def test_5gal_60s_is_5gpm():
    assert math.isclose(bt.gpm_from_bucket(5, 60), 5.0, abs_tol=1e-9)


def test_arbitrary_bucket():
    # 3-gallon bucket in 20 s -> 9 GPM
    assert math.isclose(bt.gpm_from_bucket(3, 20), 9.0, abs_tol=1e-9)


def test_calculate_full():
    res = bt.calculate(30, bucket_gallons=5)
    assert math.isclose(res.gpm, 10.0, abs_tol=1e-9)


def test_invalid_inputs_raise():
    import pytest

    with pytest.raises(ValueError):
        bt.gpm_from_bucket(0, 30)
    with pytest.raises(ValueError):
        bt.gpm_from_bucket(5, 0)
