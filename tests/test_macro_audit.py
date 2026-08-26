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
    assert M._parse_option("opening_basket")["kind"] == "opening_basket"
    assert M._parse_option("opening_phase")["kind"] == "opening_phase"
    tape = M._parse_option("tape_prefix:agents/champ/k01.py:24")
    assert tape["kind"] == "tape_prefix"
    assert tape["path"] == "agents/champ/k01.py" and tape["steps"] == 24
    barn = M._parse_option("barnyard_prefix:480")
    assert barn["kind"] == "barnyard_prefix" and barn["steps"] == 480
    assert barn["profile"] == "default" and barn["scope"] == "all"
    industrial = M._parse_option("barnyard_prefix:industrial:480")
    assert industrial["kind"] == "barnyard_prefix"
    assert industrial["profile"] == "industrial"
    assert industrial["scope"] == "all" and industrial["steps"] == 480
    state_guided = M._parse_option("barnyard_prefix:k01_state:480")
    assert state_guided["profile"] == "k01_state"
    state_farm = M._parse_option("barnyard_prefix:k01_state:farm:240")
    assert state_farm["profile"] == "k01_state"
    assert state_farm["scope"] == "farm" and state_farm["steps"] == 240
    state_market = M._parse_option("barnyard_prefix:k01_state:market:240")
    assert state_market["scope"] == "market"
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
    crew = M._parse_option("crew_build_phase:strawberry:sheep:2:28:7")
    assert crew["kind"] == "crew_build_phase"
    assert crew["targets"] == targeted["targets"]
    assert M._option_targets(targeted, 3, 9, 4) == targeted["targets"]
    assert M._option_targets(build, 3, 9, 4) == {
        "land": 3, "crops": 9, "herd": 4}
    farm = M._parse_option("farm_phase:strawberry:sheep:2:28:7")
    assert farm["kind"] == "farm_phase"
    assert farm["targets"] == targeted["targets"]
    assert M._parse_option("hands_auto")["kind"] == "hands_auto"
    policy = M._parse_option("policy_npz:rl/out/model/weights.npz:1.0")
    assert policy["kind"] == "policy_npz"
    assert policy["path"] == "rl/out/model/weights.npz"
    assert policy["temperature"] == 1.0
    combo = M._parse_option(
        "build_then_policy:strawberry:sheep:2:32:8:weights.npz:0.7")
    assert combo["kind"] == "build_then_policy"
    assert combo["targets"] == {"land": 2, "crops": 32, "herd": 8}
    assert combo["path"] == "weights.npz"
    assert combo["temperature"] == 0.7
    cash = M._parse_option("preserve_cash:3000")
    assert cash["kind"] == "preserve_cash"
    assert cash["cash_target"] == 3000
    try:
        M._parse_option("establish_crop:NOT_A_CROP")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown crop should fail")


def test_scheduled_option_trigger():
    assert M._scheduled_option_eligible("barnyard_prefix", 0, 0)
    assert M._scheduled_option_eligible("barnyard_prefix", 120, 5)
    assert M._scheduled_option_eligible("tape_prefix", 120, 5)
    assert not M._scheduled_option_eligible("barnyard_prefix", 119, 5)
    assert not M._scheduled_option_eligible("barnyard_prefix", 121, 5)
    assert M._scheduled_option_eligible("opening_phase", 0, 0)
    assert not M._scheduled_option_eligible("opening_phase", 120, 5)

    ops = {
        "f_op": 1, "f_arg": 2, "f_qty": 3,
        "h_op": 4, "h_arg": 5, "h_qty": 6,
        "m_op": 7, "m_item": 8, "m_rem": 9,
        "task": 10,
    }
    assert set(M._scoped_prefix_ops(ops, "farm")) == {
        "f_op", "f_arg", "f_qty", "h_op", "h_arg", "h_qty"}
    assert set(M._scoped_prefix_ops(ops, "market")) == {
        "m_op", "m_item", "m_rem"}
    assert M._scoped_prefix_ops(ops, "all") is ops


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


def test_opening_basket_masked_override():
    env = M.KGTensorEnv(
        2, device="cpu", seat=0, base_seed=9, opponent="starter")
    td = env.reset()
    env.queue_step_override(
        0, M._opening_basket_ops(env._ep), torch.tensor([False, True]))
    td["action"] = torch.zeros((2, 2), dtype=torch.int64)
    env.step(td)
    ep = env._ep
    assert int(ep.hands_n[0, 0]) == 0
    assert int(ep.hands_n[1, 0]) == 5
    assert int(ep.seeds_t[0, 0].sum()) == 0
    assert int(ep.seeds_t[1, 0, M.engine_t.CROP_IDX["WHEAT"]]) == 7
    assert int(ep.seeds_t[1, 0, M.engine_t.CROP_IDX["MELON"]]) == 12
    assert int(ep.shed[1, 0, M.engine_t.ITEM_IDX["COW"]]) == 2
    assert int(ep.shed[1, 0, M.engine_t.ITEM_IDX["SHEEP"]]) == 2
    # The sixth unit can be unaffordable under a more expensive initial
    # market; the raw order asks for six and the engine buys the affordable
    # prefix exactly as it does for the traced agent.
    assert 1 <= int(ep.shed[1, 0, M.engine_t.WHEAT_I]) <= 6


def test_k01_state_daily_budgets():
    """The state-closed executor keeps its day-scale commitments statefully."""
    import barnyard_t
    import opponents_t

    episode = M.engine_t.EpisodeT(
        [620825], episode_steps=720, device="cpu")
    opponent = barnyard_t.BarnyardOpponent("k01_state")
    hires = [0] * 30
    fertilizer = [0] * 30

    while not episode.done:
        day = episode._step // episode.turns_per_day
        ops = opponent(episode, 1)
        unit_ops = torch.stack([ops["f_op"], *ops["h_op"]], dim=1)
        hires[day] += int((ops["m_op"] == M.engine_t_idx.OP_HIRE).sum())
        fertilizer[day] += int(
            (unit_ops == M.engine_t_idx.U_FERTILIZE).sum())

        starter_f, starter_m = opponents_t.starter_indices(episode, 0)
        farmer = torch.stack([starter_f, torch.zeros_like(starter_f)], dim=1)
        market = torch.stack([starter_m, torch.zeros_like(starter_m)], dim=1)
        episode.step_idx(farmer, market, override=(1, ops))

    assert hires == barnyard_t._K01_HAND_CAP
    assert all(used <= cap for used, cap in zip(
        fertilizer, barnyard_t._K01_FERT_CAP))
    assert sum(fertilizer) > 0


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
    test_scheduled_option_trigger()
    test_legacy_hand_head_adaptation()
    test_cash_reserve()
    test_build_phase_milestone()
    test_opening_basket_masked_override()
    test_k01_state_daily_budgets()
    test_strategic_context()
    test_select_herd_context()
    test_option_oracle_summary()
    print("macro audit tests passed")
