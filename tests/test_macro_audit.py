#!/usr/bin/env python
"""Small deterministic tests for macro-audit statistics and option parsing."""

import importlib.util
import math
from pathlib import Path

import numpy as np
import torch

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
    clustered = M.paired_summary(
        [10, 10, -2, -2], clusters=[1, 1, 2, 2], bootstrap=500)
    assert clustered["clusters"] == 2
    assert clustered["mean"] == 4


def test_options():
    assert M._parse_option("expand_land")["kind"] == "expand_land"
    crop = M._parse_option("establish_crop:strawberry")
    assert crop["crop"] == "STRAWBERRY"
    assert crop["farmer_index"] >= 0 and crop["market_index"] >= 0
    expanded = M._parse_option("expand_crop:strawberry")
    assert expanded["kind"] == "expand_crop"
    assert expanded["crop"] == "STRAWBERRY"
    herd = M._parse_option("scale_herd:sheep")
    assert herd["kind"] == "scale_herd"
    assert herd["animal"] == "SHEEP"
    assert herd["cost"] == 500
    operated = M._parse_option("operate_herd:sheep")
    assert operated["kind"] == "operate_herd"
    assert operated["species_key"] == "sheep"
    assert operated["animal_board_index"] == M.engine_t.ANIMAL_IDX["SHEEP"]
    selected = M._parse_option("select_herd:sheep")
    assert selected["kind"] == "select_herd"
    assert selected["species_key"] == "sheep"
    build = M._parse_option("build_phase:strawberry:sheep")
    assert build["kind"] == "build_phase"
    assert build["crop"] == "STRAWBERRY"
    assert build["animal"] == "SHEEP"
    assert build["structure_code"] == M.engine_t.K_PASTURE
    targeted = M._parse_option("build_phase:strawberry:sheep:2:28:7")
    assert targeted["targets"] == {"land": 2, "crops": 28, "herd": 7}
    assert M._option_targets(targeted, 3, 9, 4) == targeted["targets"]
    assert M._option_targets(build, 3, 9, 4) == {
        "land": 3, "crops": 9, "herd": 4}
    cash = M._parse_option("preserve_cash:3000")
    assert cash["kind"] == "preserve_cash"
    assert cash["cash_target"] == 3000
    try:
        M._parse_option("establish_crop:NOT_A_CROP")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown crop should fail")


def test_legacy_hand_head_adaptation():
    old_tasks = 8
    hidden = 3
    rows = M.A.MAX_HANDS * old_tasks
    weight = torch.arange(rows * hidden, dtype=torch.float32).view(rows, hidden)
    bias = torch.arange(rows, dtype=torch.float32)
    adapted, info = M.adapt_legacy_hand_head(
        {"hands.weight": weight, "hands.bias": bias, "other": torch.ones(1)})
    assert info["checkpoint_hand_tasks"] == old_tasks
    assert info["runtime_hand_tasks"] == M.A.N_HAND_TASK
    assert info["adapted"]
    got_w = adapted["hands.weight"].view(M.A.MAX_HANDS, M.A.N_HAND_TASK, hidden)
    got_b = adapted["hands.bias"].view(M.A.MAX_HANDS, M.A.N_HAND_TASK)
    old_w = weight.view(M.A.MAX_HANDS, old_tasks, hidden)
    old_b = bias.view(M.A.MAX_HANDS, old_tasks)
    assert torch.equal(got_w[:, :old_tasks], old_w)
    assert torch.equal(got_b[:, :old_tasks], old_b)
    assert torch.equal(got_w[:, old_tasks:], torch.zeros_like(got_w[:, old_tasks:]))
    assert torch.equal(got_b[:, old_tasks:],
                       torch.full_like(got_b[:, old_tasks:], -1e9))

    current, current_info = M.adapt_legacy_hand_head(adapted)
    assert current is adapted
    assert not current_info["adapted"]


def test_cash_reserve():
    assert M._affords_with_reserve(2000, 1000, 1000)
    assert not M._affords_with_reserve(1999, 1000, 1000)


def test_build_phase_milestone():
    start = {"land": 1, "crops": 9, "herd": 4}
    partial = {"land": 2, "crops": 32, "herd": 9}
    done = {"land": 2, "crops": 32, "herd": 10}
    assert not M._build_phase_complete(partial, 2, 32, 10)
    assert M._build_phase_complete(done, 2, 32, 10)
    assert M._build_phase_delta(done, start) == {
        "land": 1, "crops": 23, "herd": 6}


def test_strategic_context():
    episode = M.engine_t.EpisodeT([123], episode_steps=48, device="cpu")
    context = M._strategic_context(episode, 0, 0)
    assert context["day"] == 0 and context["hour"] == 0
    assert context["shops"] == 0
    assert context["price_wool"] == M.engine_t.E.MARKET_PARAMS["WOOL"]["base"]
    assert context["market_wool"] == M.engine_t.E.MARKET_I0
    assert context["demand_wool"] == 0


def test_select_herd_context():
    context = {"money": 1800, "demand_milk": 1}
    assert M._select_herd_context(context, max_money=1900)
    assert not M._select_herd_context(context, max_money=1700)
    assert M._select_herd_context(context, max_demand_milk=1)
    assert not M._select_herd_context(context, max_demand_milk=0)
    assert M._select_herd_context(
        context, max_money=1900, max_demand_milk=1)


def test_option_oracle_summary():
    def cell(option, interventions, successes=(True, True)):
        records = []
        for seed, margin, success in zip((10, 11), interventions, successes):
            base = {"money": 100.0, "opp_money": 120.0, "margin": -20.0}
            changed = {
                "money": 100.0 + margin + 20.0,
                "opp_money": 120.0,
                "margin": float(margin),
            }
            records.append({
                "seed": seed, "triggered": True,
                "option_success": success,
                "baseline": base, "intervention": changed,
            })
        return {"opponent": "wall", "seat": 0, "option": option,
                "records": records}

    cells = [cell("small", (-10, -30)),
             cell("large", (5, 10), successes=(False, True))]
    all_branches = M.option_oracle_summary(
        cells, ["small", "large"], 1, successful_only=False)
    assert all_branches["states"] == 2
    assert all_branches["baseline_wins"] == 0
    assert all_branches["oracle_wins"] == 2
    assert all_branches["choice_counts"] == {"large": 2}
    completed = M.option_oracle_summary(
        cells, ["small", "large"], 1, successful_only=True)
    assert completed["oracle_wins"] == 1
    assert completed["choice_counts"] == {"large": 1, "small": 1}


if __name__ == "__main__":
    test_discounted_returns()
    test_critic_stats()
    test_paired_summary()
    test_options()
    test_legacy_hand_head_adaptation()
    test_cash_reserve()
    test_build_phase_milestone()
    test_strategic_context()
    test_select_herd_context()
    test_option_oracle_summary()
    print("macro audit tests passed")
