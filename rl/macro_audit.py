#!/usr/bin/env python
"""Phase 0/1 audits for long-horizon strategic credit assignment.

The baseline command compares checkpoints on one frozen tensor field and
measures critic calibration by game phase.  The counterfactual command creates
paired lanes from one forked EpisodeT state, changes only a persistent macro
option in the odd lane, and reports paired outcomes at fixed horizons.

This is deliberately an audit tool, not a trainer.  A macro option must move a
real terminal outcome here before it is exposed to a learned controller.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

_HERE = Path(__file__).resolve().parent
_TENSOR = _HERE / "tensor_env"
for _path in (_HERE, _TENSOR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import actions as A  # noqa: E402
import bank_t  # noqa: E402
import engine_t  # noqa: E402
import engine_t_idx  # noqa: F401,E402
import features_t  # noqa: E402
import obs as O  # noqa: E402
import verify  # noqa: E402
from trl_env import KGTensorEnv  # noqa: E402
from trl_policy import build_actor_critic, load_merged_state_dict  # noqa: E402


PHASES = ((0, 4), (5, 11), (12, 19), (20, 29))
DEFAULT_FIELD = (
    "starter",
    "barnyard",
    "tape:agents/bench3/closer_cleo.py",
    "tape:agents/wrapped/w49.py",
)
DEFAULT_OPTIONS = ("expand_land", "establish_crop:STRAWBERRY")

_BUY_LAND = A.MARKET_ACTIONS.index("BUY_LAND")
_BUY_WHEAT = A.MARKET_ACTIONS.index("BUY_WHEAT")
_HIRE = A.MARKET_ACTIONS.index("HIRE")
_BUY_SEED = tuple(i for i, n in enumerate(A.MARKET_ACTIONS)
                  if n.startswith("BUY_SEED_"))
_BUY_ANIMAL = tuple(i for i, n in enumerate(A.MARKET_ACTIONS)
                    if n.startswith("BUY_")
                    and n[len("BUY_"):] in A.ANIMAL_LIST)
_PURCHASE_MARKET = tuple(i for i, n in enumerate(A.MARKET_ACTIONS)
                         if n.startswith("BUY_") or n == "HIRE")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _atomic_json(data, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True, allow_nan=False)
        fh.write("\n")
    os.replace(tmp, path)


def _finite(value):
    value = float(value)
    return value if math.isfinite(value) else None


def _describe(values):
    x = np.asarray(values, dtype=np.float64)
    if not x.size:
        return {"n": 0, "mean": None, "median": None, "p05": None,
                "p95": None}
    return {
        "n": int(x.size),
        "mean": _finite(x.mean()),
        "median": _finite(np.median(x)),
        "p05": _finite(np.percentile(x, 5)),
        "p95": _finite(np.percentile(x, 95)),
    }


def discounted_returns(rewards, gamma):
    """Discounted return-to-go for a (lanes, time) numpy array."""
    rewards = np.asarray(rewards, dtype=np.float64)
    out = np.empty_like(rewards)
    running = np.zeros(rewards.shape[0], dtype=np.float64)
    for t in range(rewards.shape[1] - 1, -1, -1):
        running = rewards[:, t] + float(gamma) * running
        out[:, t] = running
    return out


def critic_stats(targets, values):
    targets = np.asarray(targets, dtype=np.float64).reshape(-1)
    values = np.asarray(values, dtype=np.float64).reshape(-1)
    if not targets.size:
        return {"n": 0, "explained_variance": None, "rmse": None,
                "bias": None}
    err = targets - values
    var = float(np.var(targets))
    ev = None if var <= 1e-12 else 1.0 - float(np.var(err)) / var
    return {
        "n": int(targets.size),
        "explained_variance": _finite(ev) if ev is not None else None,
        "rmse": _finite(np.sqrt(np.mean(err * err))),
        "bias": _finite(np.mean(values - targets)),
    }


def paired_summary(values, bootstrap=2000, seed=240825):
    """Summary and deterministic bootstrap CI for paired deltas."""
    x = np.asarray(values, dtype=np.float64)
    out = _describe(x)
    if x.size < 2:
        out.update({"ci95_low": None, "ci95_high": None,
                    "positive_fraction": _finite(np.mean(x > 0)) if x.size else None})
        return out
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, x.size, size=(bootstrap, x.size))
    means = x[idx].mean(1)
    out.update({
        "ci95_low": _finite(np.percentile(means, 2.5)),
        "ci95_high": _finite(np.percentile(means, 97.5)),
        "positive_fraction": _finite(np.mean(x > 0)),
    })
    return out


def adapt_legacy_hand_head(model):
    """Pad an append-only legacy hand vocabulary without enabling new tasks."""
    if "hands.weight" not in model:
        return model, {"checkpoint_hand_tasks": None,
                       "runtime_hand_tasks": A.N_HAND_TASK,
                       "adapted": False}
    rows, hidden = model["hands.weight"].shape
    if rows % A.MAX_HANDS:
        raise ValueError(
            f"hand head has {rows} rows, not divisible by {A.MAX_HANDS} hands")
    old_tasks = rows // A.MAX_HANDS
    info = {"checkpoint_hand_tasks": old_tasks,
            "runtime_hand_tasks": A.N_HAND_TASK,
            "adapted": old_tasks != A.N_HAND_TASK}
    if old_tasks == A.N_HAND_TASK:
        return model, info
    if old_tasks > A.N_HAND_TASK:
        raise ValueError(
            f"checkpoint has {old_tasks} hand tasks but runtime has "
            f"{A.N_HAND_TASK}; shrinking is not safe")

    out = dict(model)
    weight, bias = model["hands.weight"], model["hands.bias"]
    new_weight = weight.new_zeros((A.MAX_HANDS * A.N_HAND_TASK, hidden))
    new_bias = bias.new_full((A.MAX_HANDS * A.N_HAND_TASK,), -1e9)
    for hand in range(A.MAX_HANDS):
        old = slice(hand * old_tasks, (hand + 1) * old_tasks)
        new = slice(hand * A.N_HAND_TASK,
                    hand * A.N_HAND_TASK + old_tasks)
        new_weight[new] = weight[old]
        new_bias[new] = bias[old]
    out["hands.weight"], out["hands.bias"] = new_weight, new_bias
    info["new_task_logits"] = "disabled at -1e9; legacy task rows copied exactly"
    return out, info


def _load_checkpoint(path, device):
    ck = torch.load(path, map_location="cpu", weights_only=False)
    saved = dict(ck.get("args", {}))
    hidden = list(ck.get("hidden", saved.get("hidden", [512, 256])))
    v_hidden = int(ck.get("v_hidden", saved.get("v_hidden", 256)))
    multi = bool(saved.get("multi_head", "hands.weight" in ck["model"]))
    residual = str(saved.get("residual_base", ""))
    actor, critic, actor_net, critic_net = build_actor_critic(
        O.OBS_DIM, A.N_FARMER, A.N_MARKET,
        hidden1=hidden[0], hidden2=hidden[1], v_hidden=v_hidden,
        device=device, residual_base=residual, multi=multi)
    model, compatibility = adapt_legacy_hand_head(ck["model"])
    load_merged_state_dict(actor_net, critic_net, model)
    ck = dict(ck)
    ck["audit_compatibility"] = compatibility
    actor_net.eval()
    critic_net.eval()
    return ck, saved, actor_net, critic_net, multi


def _env_kwargs(saved):
    return {
        "episode_steps": int(saved.get("steps", 720)),
        "win_bonus": float(saved.get("win_bonus", 1.5)),
        "margin_bonus": float(saved.get("margin_bonus", 0.0)),
        "margin_scale": float(saved.get("margin_scale", 30000.0)),
        "potential": saved.get("potential", "networth"),
        "shape_scale": float(saved.get("shape_scale", 3000.0)),
        "shape_gamma": float(saved.get("shape_gamma", 0.0)),
        "opp_lambda": float(saved.get("opp_lambda", 0.0)),
        "build_bonus": float(saved.get("build_bonus", 0.0)),
        "fert_credit": float(saved.get("fert_credit", 0.0)),
        "land_value": float(saved.get("land_value", 0.0)),
    }


@torch.no_grad()
def _policy(actor_net, td, multi):
    outs = actor_net(td["observation"])
    fl, ml = outs[0], outs[1]
    fl = fl.masked_fill(~td["farmer_mask"], -1e9)
    ml = ml.masked_fill(~td["market_mask"], -1e9)
    fa = fl.argmax(-1)
    ma = ml.argmax(-1)
    if multi:
        hl = outs[2].masked_fill(~td["hand_mask"], -1e9)
        ha = hl.argmax(-1)
        action = torch.cat([fa.unsqueeze(-1), ma.unsqueeze(-1), ha], -1)
    else:
        action = torch.stack([fa, ma], -1)
    return action, ml.softmax(-1)


def _state_metrics(ep, seat, max_state=None):
    dev = ep.device
    land = 1 + ep.quad_unlocked[:, seat].sum(-1).to(torch.int64)
    seeds = ep.seeds_t[:, seat].sum(-1).to(torch.int64)
    herd = (ep.animal[:, seat] >= 0).sum((-1, -2)).to(torch.int64)
    crops = (ep.kind[:, seat] == engine_t.K_PLANT).sum((-1, -2)).to(torch.int64)
    crew = ep.hands_n[:, seat].to(torch.int64)
    values = {"land": land, "seeds": seeds, "herd": herd,
              "crops": crops, "crew": crew}
    for animal, animal_i in engine_t.ANIMAL_IDX.items():
        values[animal.lower()] = (
            ep.animal[:, seat] == animal_i).sum((-1, -2)).to(torch.int64)
    if max_state is not None:
        for key, value in values.items():
            max_state[key] = torch.maximum(max_state[key], value)
    return values


def _new_max_state(ep, seat):
    values = _state_metrics(ep, seat)
    return {key: value.clone() for key, value in values.items()}


def _terminal_metrics(env, max_state):
    ep, seat = env._ep, env.seat
    opp = 1 - seat
    money = ep.money[:, seat]
    opp_money = ep.money[:, opp]
    final = _state_metrics(ep, seat)
    out = {
        "money": money.detach().cpu().numpy(),
        "opp_money": opp_money.detach().cpu().numpy(),
        "margin": (money - opp_money).detach().cpu().numpy(),
        "win": ((money > opp_money).to(torch.float64)
                + 0.5 * (money == opp_money).to(torch.float64)).cpu().numpy(),
    }
    for key, value in final.items():
        out[f"final_{key}"] = value.detach().cpu().numpy()
        out[f"max_{key}"] = max_state[key].detach().cpu().numpy()
    return out


def _group_probability(probs, mask, indices):
    idx = torch.as_tensor(indices, dtype=torch.int64, device=probs.device)
    legal = mask.index_select(-1, idx).any(-1)
    mass = probs.index_select(-1, idx).sum(-1)
    return legal, mass


@torch.no_grad()
def baseline_cell(checkpoint, opponent, seat, lanes, seed, device,
                  steps_override=0):
    ck, saved, actor_net, critic_net, multi = _load_checkpoint(checkpoint, device)
    kwargs = _env_kwargs(saved)
    if steps_override:
        kwargs["episode_steps"] = int(steps_override)
    env = KGTensorEnv(lanes, device=device, seat=seat, base_seed=seed,
                      opponent=opponent, multi_head=multi, **kwargs)
    td = env.reset()
    rewards, values = [], []
    phase_steps = []
    max_state = _new_max_state(env._ep, seat)
    behavior = {name: {"legal": 0, "selected": 0, "prob_sum": 0.0}
                for name in ("buy_land", "buy_seed", "buy_animal", "hire")}
    groups = {"buy_land": (_BUY_LAND,), "buy_seed": _BUY_SEED,
              "buy_animal": _BUY_ANIMAL, "hire": (_HIRE,)}

    while True:
        values.append(critic_net(td["observation"]).squeeze(-1).cpu().numpy())
        action, mprob = _policy(actor_net, td, multi)
        chosen = action[:, 1]
        for name, indices in groups.items():
            legal, mass = _group_probability(mprob, td["market_mask"], indices)
            selected = torch.zeros_like(legal)
            for idx in indices:
                selected |= chosen == idx
            behavior[name]["legal"] += int(legal.sum())
            behavior[name]["selected"] += int((selected & legal).sum())
            behavior[name]["prob_sum"] += float(mass[legal].sum())
        phase_steps.append(env._ep._step)
        td["action"] = action
        stepped = env.step(td)
        nxt = stepped["next"]
        rewards.append(nxt["reward"].squeeze(-1).cpu().numpy())
        _state_metrics(env._ep, seat, max_state)
        if bool(nxt["done"].all()):
            break
        td = nxt.exclude("reward")

    reward = np.stack(rewards, 1)
    value = np.stack(values, 1)
    returns = discounted_returns(reward, float(saved.get("gamma", 0.999)))
    steps = np.asarray(phase_steps)
    phase = {}
    for d0, d1 in PHASES:
        use = (steps // 24 >= d0) & (steps // 24 <= d1)
        phase[f"day_{d0}_{d1}"] = critic_stats(returns[:, use], value[:, use])

    terminal = _terminal_metrics(env, max_state)
    behavior_out = {}
    for name, row in behavior.items():
        legal = row["legal"]
        behavior_out[name] = {
            "legal_turns": legal,
            "selected": row["selected"],
            "selection_rate_when_legal": row["selected"] / legal if legal else None,
            "mean_probability_when_legal": row["prob_sum"] / legal if legal else None,
        }
    return {
        "checkpoint_iter": int(ck.get("iter", -1)),
        "opponent": opponent,
        "seat": int(seat),
        "lanes": int(lanes),
        "seed": int(seed),
        "critic": phase,
        "behavior": behavior_out,
        "terminal": {key: [float(v) for v in values]
                     for key, values in terminal.items()},
    }


def run_baseline(args):
    cells = []
    manifests = {}
    for checkpoint in args.checkpoint:
        checkpoint = str(Path(checkpoint))
        ck = torch.load(checkpoint, map_location="cpu", weights_only=False)
        _, compatibility = adapt_legacy_hand_head(ck["model"])
        manifests[checkpoint] = {
            "sha256": _sha256(checkpoint),
            "iter": int(ck.get("iter", -1)),
            "training_source_commit": None,
            "provenance_note": (
                "legacy checkpoint predates run manifests; the original "
                "training commit is not embedded, so reproducibility is "
                "anchored by this hash and the audit source commit"),
            "checkpoint_args": ck.get("args", {}),
            "compatibility": compatibility,
        }
        for opponent in args.opponent:
            for seat in (0, 1):
                print(f"BASELINE checkpoint={checkpoint} opponent={opponent} "
                      f"seat={seat} lanes={args.lanes}", flush=True)
                cell = baseline_cell(
                    checkpoint, opponent, seat, args.lanes, args.seed,
                    args.device, args.steps)
                cell["checkpoint"] = checkpoint
                cells.append(cell)

    summary = {}
    for checkpoint in args.checkpoint:
        mine = [c for c in cells if c["checkpoint"] == checkpoint]
        merged = defaultdict(list)
        for cell in mine:
            for key, values in cell["terminal"].items():
                merged[key].extend(values)
        critics = {}
        for d0, d1 in PHASES:
            name = f"day_{d0}_{d1}"
            # Weight means by observation count; EV itself cannot be pooled
            # without raw predictions, so report its distribution over cells.
            critics[name] = {
                "explained_variance_by_cell": [c["critic"][name]["explained_variance"]
                                                for c in mine],
                "rmse_by_cell": [c["critic"][name]["rmse"] for c in mine],
            }
        behavior = {}
        for name in ("buy_land", "buy_seed", "buy_animal", "hire"):
            legal = sum(c["behavior"][name]["legal_turns"] for c in mine)
            selected = sum(c["behavior"][name]["selected"] for c in mine)
            prob_sum = sum(
                c["behavior"][name]["mean_probability_when_legal"]
                * c["behavior"][name]["legal_turns"]
                for c in mine if c["behavior"][name]["legal_turns"])
            behavior[name] = {
                "legal_turns": legal,
                "selected": selected,
                "selection_rate_when_legal": selected / legal if legal else None,
                "mean_probability_when_legal": prob_sum / legal if legal else None,
            }
        summary[checkpoint] = {
            "terminal": {key: _describe(values) for key, values in merged.items()},
            "critic": critics,
            "behavior": behavior,
        }
        row = summary[checkpoint]["terminal"]
        print(f"SUMMARY checkpoint={checkpoint} win={row['win']['mean']:.3f} "
              f"margin={row['margin']['mean']:+,.0f} "
              f"money={row['money']['median']:,.0f}", flush=True)

    ranking = sorted(
        ({"checkpoint": checkpoint,
          "mean_margin": summary[checkpoint]["terminal"]["margin"]["mean"],
          "p05_money": summary[checkpoint]["terminal"]["money"]["p05"]}
         for checkpoint in args.checkpoint),
        key=lambda row: (row["mean_margin"], row["p05_money"]), reverse=True)
    out = {
        "schema": 1,
        "mode": "baseline",
        "source_commit": _git_commit(),
        "device": args.device,
        "steps_override": args.steps or None,
        "field": list(args.opponent),
        "seats": [0, 1],
        "lanes_per_cell": args.lanes,
        "seed": args.seed,
        "checkpoints": manifests,
        "selection_rule": (
            "highest mean terminal margin over the equal-weight frozen field "
            "and both seats; p05 learner money breaks an exact tie"),
        "ranking": ranking,
        "selected_checkpoint": ranking[0]["checkpoint"],
        "summary": summary,
        "cells": cells,
    }
    _atomic_json(out, args.output)
    print(f"wrote {args.output}")


def _repeat_forked_initial_state(env, seeds):
    source = engine_t.EpisodeT(seeds, episode_steps=env.episode_steps,
                               device=env.device)
    state = bank_t.fork(source)
    src = [i for i in range(len(seeds)) for _ in (0, 1)]
    bank_t.restore_lanes(env._ep, state, src)
    env._prev_w = env._pot(env._ep, env.seat)
    if env.opp_lambda:
        env._prev_wo = env._pot(env._ep, 1 - env.seat)
    return env._obs_td()


def _parse_option(text):
    if text == "expand_land":
        return {"name": text, "kind": text}
    if text.startswith(("establish_crop:", "expand_crop:")):
        crop = text.split(":", 1)[1].upper()
        if crop not in A.CROP_LIST:
            raise ValueError(f"unknown crop in option {text!r}")
        kind = text.split(":", 1)[0]
        return {"name": text, "kind": kind, "crop": crop,
                "crop_index": A.CROP_LIST.index(crop),
                "farmer_index": A.FARMER_ACTIONS.index(f"PLANT_{crop}"),
                "market_index": A.MARKET_ACTIONS.index(f"BUY_SEED_{crop}")}
    if text.startswith(("scale_herd:", "operate_herd:", "select_herd:")):
        animal = text.split(":", 1)[1].upper()
        if animal not in A.ANIMAL_LIST:
            raise ValueError(f"unknown animal in option {text!r}")
        structure = engine_t.E.ANIMALS[animal]["structure"]
        return {
            "name": text, "kind": text.split(":", 1)[0], "animal": animal,
            "animal_index": engine_t.ITEM_IDX[animal],
            "animal_board_index": engine_t.ANIMAL_IDX[animal],
            "species_key": animal.lower(),
            "market_index": A.MARKET_ACTIONS.index(f"BUY_{animal}"),
            "place_index": A.FARMER_ACTIONS.index(f"PLACE_{animal}"),
            "build_index": A.FARMER_ACTIONS.index(f"BUILD_{structure}"),
            "cost": engine_t.E.ANIMALS[animal]["cost"],
        }
    if text.startswith("preserve_cash:"):
        target = int(text.split(":", 1)[1])
        if target <= 0:
            raise ValueError("preserve_cash target must be positive")
        return {"name": text, "kind": "preserve_cash",
                "cash_target": target}
    raise ValueError(f"unknown option {text!r}")


def _pair_snapshot_equal(ep, pair):
    left, right = ep.snapshot(2 * pair), ep.snapshot(2 * pair + 1)
    return verify.first_diff(left, right)


def _branch_metrics(env, max_state, lane):
    ep, seat = env._ep, env.seat
    opp = 1 - seat
    current = _state_metrics(ep, seat)
    return {
        "money": float(ep.money[lane, seat]),
        "margin": float(ep.money[lane, seat] - ep.money[lane, opp]),
        "future_worth": float(env._pot(ep, seat)[lane]),
        **{f"final_{key}": float(value[lane]) for key, value in current.items()},
        **{f"max_{key}": float(value[lane]) for key, value in max_state.items()},
    }


def _paired_delta_record(base, intervention):
    return {key: intervention[key] - base[key] for key in base}


def _affords_with_reserve(money, cost, cash_reserve):
    return float(money) >= float(cost) + float(cash_reserve)


def _operate_herd(action, td, ep, lane, seat, counters, cash_reserve):
    """Keep existing animals productive while disturbing as few hands as possible."""
    animal = ep.animal[lane, seat] >= 0
    herd = int(animal.sum())
    if herd <= 0:
        return

    wheat = int(ep.shed[lane, seat, engine_t.WHEAT_I])
    wheat += int(ep.unit_inv[lane, seat, :, engine_t.WHEAT_I].sum())
    buy_qty = max(5, 2 * herd)
    wheat_price = float(ep.mkt_price[lane, engine_t.WHEAT_I])
    if (wheat < herd and bool(td["market_mask"][lane, _BUY_WHEAT])
            and _affords_with_reserve(
                ep.money[lane, seat], buy_qty * wheat_price, cash_reserve)):
        if int(action[lane, 1]) != _BUY_WHEAT:
            counters["buy_wheat"] += 1
        action[lane, 1] = _BUY_WHEAT

    if action.shape[-1] <= 2:
        return
    needs = (
        ("FEED", int((animal & ~ep.fed[lane, seat]).sum())),
        ("CARE", int((animal & ~ep.cared[lane, seat]).sum())),
        ("HARVEST", int((animal & (ep.yield_units[lane, seat] > 0)).sum())),
    )
    next_slot = 0
    live_hands = min(int(ep.hands_n[lane, seat]), A.MAX_HANDS)
    for task, count in needs:
        task_i = A.HAND_TASKS.index(task)
        assigned = 0
        while next_slot < live_hands and assigned < count:
            slot = next_slot
            next_slot += 1
            if not bool(td["hand_mask"][lane, slot, task_i]):
                continue
            if int(action[lane, 2 + slot]) != task_i:
                counters[task.lower()] += 1
            action[lane, 2 + slot] = task_i
            assigned += 1


@torch.no_grad()
def counterfactual_cell(checkpoint, opponent, seat, lanes, seed, device,
                        option_text, min_day, timeout, crop_target,
                        cash_reserve=0, herd_target=2, max_trigger_money=0,
                        steps_override=0):
    _, saved, actor_net, _, multi = _load_checkpoint(checkpoint, device)
    option = _parse_option(option_text)
    kwargs = _env_kwargs(saved)
    if steps_override:
        kwargs["episode_steps"] = int(steps_override)
    env = KGTensorEnv(2 * lanes, device=device, seat=seat, base_seed=seed,
                      opponent=opponent, multi_head=multi, **kwargs)
    env.reset()
    seeds = [seed + i for i in range(lanes)]
    td = _repeat_forked_initial_state(env, seeds)
    ep = env._ep
    max_state = _new_max_state(ep, seat)

    triggered = [False] * lanes
    selected = [False] * lanes
    trigger_step = [-1] * lanes
    finished = [False] * lanes
    success = [False] * lanes
    completion_elapsed = [None] * lanes
    completion_target_delta = [None] * lanes
    start_value = [None] * lanes
    horizons = (24, 72, 168)
    observations = [{str(h): None for h in horizons} for _ in range(lanes)]
    forced_actions = [defaultdict(int) for _ in range(lanes)]

    while True:
        action, _ = _policy(actor_net, td, multi)
        # Before a pair is changed, both policy and full simulator state must
        # be identical.  This catches accidental unpaired RNG or seat drift.
        for pair in range(lanes):
            if not triggered[pair] and not torch.equal(
                    action[2 * pair], action[2 * pair + 1]):
                raise AssertionError(f"policy diverged before trigger in pair {pair}")

        state = _state_metrics(ep, seat)
        for pair in range(lanes):
            odd = 2 * pair + 1
            if not triggered[pair] and ep._step >= min_day * 24:
                if option["kind"] in {"expand_land", "expand_crop"}:
                    extra_land = int(ep.quad_unlocked[odd, seat].sum())
                    land_cost = engine_t.E.LAND_PRICES[
                        min(extra_land, len(engine_t.E.LAND_PRICES) - 1)]
                    eligible = (bool(td["market_mask"][odd, _BUY_LAND])
                                and _affords_with_reserve(
                                    ep.money[odd, seat], land_cost, cash_reserve))
                elif option["kind"] in {"establish_crop", "expand_crop"}:
                    seed_cost = engine_t.CROP_SEED_COST[option["crop_index"]]
                    eligible = (bool(td["market_mask"][odd, option["market_index"]])
                                and _affords_with_reserve(
                                    ep.money[odd, seat], seed_cost, cash_reserve))
                elif option["kind"] in {
                        "scale_herd", "operate_herd", "select_herd"}:
                    eligible = (bool(td["market_mask"][odd, option["market_index"]])
                                and _affords_with_reserve(
                                    ep.money[odd, seat], option["cost"], cash_reserve))
                else:
                    eligible = float(ep.money[odd, seat]) < option["cash_target"]
                if eligible:
                    diff = _pair_snapshot_equal(ep, pair)
                    if diff:
                        raise AssertionError(
                            f"state diverged before trigger in pair {pair}: {diff}")
                    triggered[pair] = True
                    selected[pair] = (
                        option["kind"] != "select_herd"
                        or float(ep.money[odd, seat]) <= max_trigger_money)
                    trigger_step[pair] = ep._step
                    start_value[pair] = {
                        key: int(value[odd]) for key, value in state.items()}
                    start_value[pair].update({
                        "money": float(ep.money[odd, seat]),
                        "opp_money": float(ep.money[odd, 1 - seat]),
                        "future_worth": float(env._pot(ep, seat)[odd]),
                    })
                    if not selected[pair]:
                        finished[pair] = True
                        completion_elapsed[pair] = 0
                        completion_target_delta[pair] = 0

            if not triggered[pair] or finished[pair]:
                continue
            elapsed = ep._step - trigger_step[pair]
            if elapsed >= timeout:
                finished[pair] = True
                completion_elapsed[pair] = timeout
                if option["kind"] == "preserve_cash":
                    completion_target_delta[pair] = (
                        float(ep.money[odd, seat]) - start_value[pair]["money"])
                else:
                    target_key = ("land" if option["kind"] == "expand_land" else
                                  option["species_key"] if option["kind"] in {
                                      "scale_herd", "operate_herd", "select_herd"} else
                                  "crops")
                    completion_target_delta[pair] = (
                        int(state[target_key][odd]) - start_value[pair][target_key])
                    if option["kind"] == "operate_herd":
                        success[pair] = completion_target_delta[pair] >= herd_target
                continue
            land_complete = int(state["land"][odd]) > start_value[pair]["land"]
            if option["kind"] in {"expand_land", "expand_crop"} and not land_complete:
                if bool(td["market_mask"][odd, _BUY_LAND]):
                    action[odd, 1] = _BUY_LAND
            elif option["kind"] in {"establish_crop", "expand_crop"}:
                planted = int(state["crops"][odd]) - start_value[pair]["crops"]
                remaining = max(0, crop_target - planted)
                crop_i = option["crop_index"]
                seed_stock = int(ep.seeds_t[odd, seat, crop_i])
                can_reserve = _affords_with_reserve(
                    ep.money[odd, seat], engine_t.CROP_SEED_COST[crop_i],
                    cash_reserve)
                if (remaining > seed_stock and can_reserve and bool(
                        td["market_mask"][odd, option["market_index"]])):
                    action[odd, 1] = option["market_index"]
                if remaining > 0 and bool(
                        td["farmer_mask"][odd, option["farmer_index"]]):
                    action[odd, 0] = option["farmer_index"]
            elif option["kind"] in {
                    "scale_herd", "operate_herd", "select_herd"}:
                remaining = max(0, herd_target - (
                    int(state[option["species_key"]][odd])
                    - start_value[pair][option["species_key"]]))
                animal_i = option["animal_index"]
                unplaced = int(ep.shed[odd, seat, animal_i])
                unplaced += int(ep.unit_inv[odd, seat, :, animal_i].sum())
                can_reserve = _affords_with_reserve(
                    ep.money[odd, seat], option["cost"], cash_reserve)
                if (remaining > unplaced and can_reserve and bool(
                        td["market_mask"][odd, option["market_index"]])):
                    if int(action[odd, 1]) != option["market_index"]:
                        forced_actions[pair]["buy_animal"] += 1
                    action[odd, 1] = option["market_index"]
                if remaining > 0:
                    if bool(td["farmer_mask"][odd, option["place_index"]]):
                        if int(action[odd, 0]) != option["place_index"]:
                            forced_actions[pair]["place_animal"] += 1
                        action[odd, 0] = option["place_index"]
                    elif bool(td["farmer_mask"][odd, option["build_index"]]):
                        if int(action[odd, 0]) != option["build_index"]:
                            forced_actions[pair]["build_structure"] += 1
                        action[odd, 0] = option["build_index"]
                if option["kind"] == "operate_herd":
                    _operate_herd(action, td, ep, odd, seat,
                                  forced_actions[pair], cash_reserve)
            elif option["kind"] == "preserve_cash":
                if int(action[odd, 1]) in _PURCHASE_MARKET:
                    action[odd, 1] = 0

        td["action"] = action
        stepped = env.step(td)
        nxt = stepped["next"]
        state = _state_metrics(ep, seat, max_state)

        for pair in range(lanes):
            if not triggered[pair]:
                continue
            odd = 2 * pair + 1
            elapsed = ep._step - trigger_step[pair]
            if not finished[pair]:
                if option["kind"] == "expand_land":
                    success[pair] = int(state["land"][odd]) > start_value[pair]["land"]
                elif option["kind"] == "expand_crop":
                    success[pair] = (
                        int(state["land"][odd]) > start_value[pair]["land"]
                        and int(state["crops"][odd]) - start_value[pair]["crops"]
                        >= crop_target)
                elif option["kind"] in {
                        "scale_herd", "operate_herd", "select_herd"}:
                    success[pair] = (
                        int(state[option["species_key"]][odd])
                        - start_value[pair][option["species_key"]] >= herd_target)
                elif option["kind"] == "preserve_cash":
                    success[pair] = (float(ep.money[odd, seat])
                                     >= option["cash_target"])
                else:
                    success[pair] = (int(state["crops"][odd])
                                     - start_value[pair]["crops"] >= crop_target)
                persistent = option["kind"] == "operate_herd"
                finished[pair] = ((success[pair] and not persistent)
                                  or elapsed >= timeout or (persistent and ep.done))
                if finished[pair]:
                    completion_elapsed[pair] = min(timeout, elapsed)
                    if option["kind"] == "preserve_cash":
                        completion_target_delta[pair] = (
                            float(ep.money[odd, seat]) - start_value[pair]["money"])
                    else:
                        target_key = (
                            "land" if option["kind"] == "expand_land" else
                            option["species_key"] if option["kind"] in {
                                "scale_herd", "operate_herd", "select_herd"} else
                            "crops")
                        completion_target_delta[pair] = (
                            int(state[target_key][odd])
                            - start_value[pair][target_key])
            for horizon in horizons:
                key = str(horizon)
                if observations[pair][key] is None and elapsed >= horizon:
                    base = _branch_metrics(env, max_state, 2 * pair)
                    changed = _branch_metrics(env, max_state, odd)
                    observations[pair][key] = _paired_delta_record(base, changed)

        if bool(nxt["done"].all()):
            break
        td = nxt.exclude("reward")

    records = []
    for pair in range(lanes):
        if not triggered[pair]:
            records.append({"pair": pair, "seed": seeds[pair],
                            "triggered": False})
            continue
        base = _branch_metrics(env, max_state, 2 * pair)
        changed = _branch_metrics(env, max_state, 2 * pair + 1)
        base_win = float(base["margin"] > 0) + 0.5 * float(base["margin"] == 0)
        changed_win = (float(changed["margin"] > 0)
                       + 0.5 * float(changed["margin"] == 0))
        delta = _paired_delta_record(base, changed)
        delta["win"] = changed_win - base_win
        records.append({
            "pair": pair,
            "seed": seeds[pair],
            "triggered": True,
            "trigger_step": trigger_step[pair],
            "trigger_day": trigger_step[pair] // 24,
            "trigger_state": start_value[pair],
            "option_selected": selected[pair],
            "option_success": success[pair],
            "option_elapsed": (completion_elapsed[pair]
                               if completion_elapsed[pair] is not None
                               else min(timeout, ep._step - trigger_step[pair])),
            "completion_target_delta": completion_target_delta[pair],
            "forced_actions": dict(forced_actions[pair]),
            "baseline": base,
            "intervention": changed,
            "delta": delta,
            "horizons": observations[pair],
        })

    used = [row for row in records if row.get("triggered")]
    metric_names = sorted({key for row in used for key in row["delta"]})
    summary = {key: paired_summary([row["delta"][key] for row in used],
                                   seed=seed + i)
               for i, key in enumerate(metric_names)}
    return {
        "opponent": opponent,
        "seat": seat,
        "option": option_text,
        "lanes": lanes,
        "triggered": len(used),
        "successes": sum(bool(row.get("option_success")) for row in used),
        "summary": summary,
        "records": records,
    }


def run_counterfactual(args):
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    _, compatibility = adapt_legacy_hand_head(checkpoint["model"])
    manifest = {
        "path": args.checkpoint,
        "sha256": _sha256(args.checkpoint),
        "compatibility": compatibility,
    }
    cells = []
    for option in args.option:
        for opponent in args.opponent:
            for seat in (0, 1):
                print(f"COUNTERFACTUAL option={option} opponent={opponent} "
                      f"seat={seat} pairs={args.lanes}", flush=True)
                cells.append(counterfactual_cell(
                    args.checkpoint, opponent, seat, args.lanes, args.seed,
                    args.device, option, args.min_day, args.timeout,
                    args.crop_target, args.cash_reserve, args.herd_target,
                    args.max_trigger_money, args.steps))

    option_summary = {}
    for option in args.option:
        mine = [c for c in cells if c["option"] == option]
        rows = [row for cell in mine for row in cell["records"]
                if row.get("triggered")]
        metrics = sorted({key for row in rows for key in row["delta"]})
        forced = sorted({key for row in rows for key in row["forced_actions"]})
        option_summary[option] = {
            "triggered": len(rows),
            "selected": sum(bool(row.get("option_selected")) for row in rows),
            "successes": sum(bool(row.get("option_success")) for row in rows),
            "metrics": {key: paired_summary(
                [row["delta"][key] for row in rows], seed=args.seed + i)
                for i, key in enumerate(metrics)},
            "forced_actions": {
                key: _describe([row["forced_actions"].get(key, 0) for row in rows])
                for key in forced
            },
            "heldout_margin_by_cell": {
                f"{cell['opponent']}@seat{cell['seat']}":
                    cell["summary"].get("margin")
                for cell in mine if cell["opponent"] == args.heldout},
        }
        margin = option_summary[option]["metrics"].get("margin", {})
        print(f"SUMMARY option={option} triggered={len(rows)} "
              f"success={option_summary[option]['successes']} "
              f"margin={margin.get('mean')}", flush=True)

    out = {
        "schema": 1,
        "mode": "counterfactual",
        "source_commit": _git_commit(),
        "device": args.device,
        "steps_override": args.steps or None,
        "checkpoint": manifest,
        "field": list(args.opponent),
        "heldout": args.heldout,
        "seats": [0, 1],
        "pairs_per_cell": args.lanes,
        "seed": args.seed,
        "min_day": args.min_day,
        "timeout": args.timeout,
        "crop_target": args.crop_target,
        "herd_target": args.herd_target,
        "cash_reserve": args.cash_reserve,
        "max_trigger_money": args.max_trigger_money or None,
        "options": list(args.option),
        "gate": (
            "terminal paired margin bootstrap CI excludes zero and heldout "
            "cells keep the same sign; option must complete and move the "
            "target behavior"),
        "summary": option_summary,
        "cells": cells,
    }
    _atomic_json(out, args.output)
    print(f"wrote {args.output}")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    base = sub.add_parser("baseline", help="compare frozen checkpoints")
    base.add_argument("--checkpoint", action="append", required=True)
    base.add_argument("--opponent", action="append", default=[])
    base.add_argument("--lanes", type=int, default=32)
    base.add_argument("--seed", type=int, default=240825)
    base.add_argument("--device", default="cpu")
    base.add_argument("--steps", type=int, default=0,
                      help="test-only episode length override")
    base.add_argument("--output", required=True)

    cf = sub.add_parser("counterfactual", help="paired persistent-option audit")
    cf.add_argument("--checkpoint", required=True)
    cf.add_argument("--option", action="append", default=[])
    cf.add_argument("--opponent", action="append", default=[])
    cf.add_argument("--heldout", default="tape:agents/wrapped/w49.py")
    cf.add_argument("--lanes", type=int, default=32,
                    help="paired seeds per opponent and seat")
    cf.add_argument("--seed", type=int, default=240825)
    cf.add_argument("--device", default="cpu")
    cf.add_argument("--steps", type=int, default=0,
                    help="test-only episode length override")
    cf.add_argument("--min-day", type=int, default=0)
    cf.add_argument("--timeout", type=int, default=48)
    cf.add_argument("--crop-target", type=int, default=4)
    cf.add_argument("--herd-target", type=int, default=2)
    cf.add_argument("--max-trigger-money", type=int, default=0,
                    help="select_herd takes the option only at or below this cash")
    cf.add_argument("--cash-reserve", type=int, default=0,
                    help="minimum money retained after forced purchases")
    cf.add_argument("--output", required=True)

    args = parser.parse_args(argv)
    if not args.opponent:
        args.opponent = list(DEFAULT_FIELD)
    if args.command == "counterfactual" and not args.option:
        args.option = list(DEFAULT_OPTIONS)
    if args.lanes < 1:
        parser.error("--lanes must be positive")
    if (args.command == "counterfactual"
            and any(option.startswith("select_herd:") for option in args.option)
            and args.max_trigger_money <= 0):
        parser.error("select_herd requires a positive --max-trigger-money")
    return args


def main(argv=None):
    args = parse_args(argv)
    torch.set_num_threads(max(1, int(os.environ.get("SLURM_CPUS_PER_TASK", "1"))))
    if args.command == "baseline":
        run_baseline(args)
    else:
        run_counterfactual(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
