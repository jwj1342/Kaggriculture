#!/usr/bin/env python
"""Small deterministic tests for macro-audit statistics and option parsing."""

import importlib.util
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "macro_audit", ROOT / "rl" / "macro_audit.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


def test_discounted_returns():
    rewards = np.array([[1.0, 2.0, 3.0], [0.0, 1.0, 0.0]])
    got = M.discounted_returns(rewards, 0.5)
    want = np.array([[2.75, 3.5, 3.0], [0.5, 1.0, 0.0]])
    assert np.allclose(got, want), (got, want)


def test_critic_stats():
    target = np.arange(10.0)
    perfect = M.critic_stats(target, target)
    assert math.isclose(perfect["explained_variance"], 1.0)
    assert math.isclose(perfect["rmse"], 0.0)
    flat = M.critic_stats(target, np.zeros_like(target))
    assert math.isclose(flat["explained_variance"], 0.0)


def test_paired_summary():
    pos = M.paired_summary([1, 2, 3, 4], bootstrap=500)
    assert pos["ci95_low"] > 0
    assert pos["positive_fraction"] == 1.0
    singleton = M.paired_summary([2])
    assert singleton["ci95_low"] is None


def test_options():
    assert M._parse_option("expand_land")["kind"] == "expand_land"
    crop = M._parse_option("establish_crop:strawberry")
    assert crop["crop"] == "STRAWBERRY"
    assert crop["farmer_index"] >= 0 and crop["market_index"] >= 0
    try:
        M._parse_option("establish_crop:NOT_A_CROP")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown crop should fail")


if __name__ == "__main__":
    test_discounted_returns()
    test_critic_stats()
    test_paired_summary()
    test_options()
    print("macro audit tests passed")
