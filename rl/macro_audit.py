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
from trl_policy import (arrays_to_sd, build_actor_critic,
                        load_merged_state_dict)  # noqa: E402


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


def paired_summary(values, bootstrap=2000, seed=240825, clusters=None):
    """Summary and deterministic bootstrap CI for paired deltas.

    When clusters are supplied, resample cluster means so repeated opponents
    and seats sharing one simulator seed do not masquerade as independent
    evidence.
    """
    x = np.asarray(values, dtype=np.float64)
    out = _describe(x)
    if x.size < 2:
        out.update({"ci95_low": None, "ci95_high": None,
                    "positive_fraction": _finite(np.mean(x > 0)) if x.size else None})
        return out
    sample = x
    if clusters is not None:
        if len(clusters) != x.size:
            raise ValueError("clusters must match paired values")
        grouped = defaultdict(list)
        for cluster, value in zip(clusters, x):
            grouped[cluster].append(float(value))
        sample = np.asarray(
            [np.mean(grouped[key]) for key in sorted(grouped)],
            dtype=np.float64)
        out["clusters"] = int(sample.size)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, sample.size, size=(bootstrap, sample.size))
    means = sample[idx].mean(1)
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


@torch.no_grad()
def _policy_at_temperature(actor_net, td, multi, temperature, generator):
    if temperature <= 0:
        return _policy(actor_net, td, multi)[0]
    outs = actor_net(td["observation"])

    def sample(logits, mask):
        logits = logits.masked_fill(~mask, -1e9) / temperature
        shape = logits.shape[:-1]
        return torch.multinomial(
            logits.softmax(-1).reshape(-1, logits.shape[-1]), 1,
            generator=generator).squeeze(-1).reshape(shape)

    fa = sample(outs[0], td["farmer_mask"])
    ma = sample(outs[1], td["market_mask"])
    if not multi:
        return torch.stack([fa, ma], -1)
    ha = sample(outs[2], td["hand_mask"])
    return torch.cat([fa.unsqueeze(-1), ma.unsqueeze(-1), ha], -1)


def _load_export_actor(path, device):
    arrays = dict(np.load(path))
    if any(key.startswith("d_") for key in arrays):
        raise ValueError("policy_npz does not yet support residual exports")
    hidden1, obs_dim = arrays["l1w"].shape
    hidden2 = arrays["l2w"].shape[0]
    if obs_dim != O.OBS_DIM:
        raise ValueError(
            f"policy_npz observation width {obs_dim} != runtime {O.OBS_DIM}")
    multi = "hw" in arrays
    _, _, actor_net, _ = build_actor_critic(
        O.OBS_DIM, A.N_FARMER, A.N_MARKET,
        hidden1=hidden1, hidden2=hidden2, device=device, multi=multi)
    actor_net.load_state_dict(arrays_to_sd(arrays))
    actor_net.eval()
    return actor_net, multi


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


def _strategic_context(ep, lane, seat):
    """Small observable macro state saved at an option decision point."""
    active = ep.shops_seq[lane] >= 0
    if bool(active.any()):
        demand = ep._shop_cons_t[
            ep.shops_seq[lane, active].to(torch.int64)].sum(0)
    else:
        demand = torch.zeros(
            len(engine_t.PRODUCTS), dtype=torch.int32, device=ep.device)
    out = {
        "day": int(ep._step // ep.turns_per_day),
        "hour": int(ep._step % ep.turns_per_day),
        "shops": int(active.sum()),
    }
    for index, item in enumerate(engine_t.PRODUCTS):
        name = item.lower()
        out[f"price_{name}"] = int(ep.mkt_price[lane, index])
        out[f"market_{name}"] = int(ep.mkt_inv[lane, index])
        out[f"demand_{name}"] = int(demand[index])
    return out


def _select_herd_context(context, max_money=0, max_demand_milk=-1):
    """Apply preregistered observable gates to a one-shot herd option."""
    return ((max_money <= 0 or context["money"] <= max_money)
            and (max_demand_milk < 0
                 or context["demand_milk"] <= max_demand_milk))


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
    if text == "hands_auto":
        return {"name": text, "kind": text}
    if text.startswith("policy_npz:"):
        payload = text.split(":", 1)[1]
        try:
            path, temperature = payload.rsplit(":", 1)
            temperature = float(temperature)
        except ValueError as exc:
            raise ValueError(
                "policy_npz must be policy_npz:<path>:<temperature>") from exc
        if not path or temperature < 0:
            raise ValueError("policy_npz requires a path and temperature >= 0")
        return {"name": text, "kind": "policy_npz", "path": path,
                "temperature": temperature}
    if text.startswith(("build_phase:", "farm_phase:",
                        "build_then_policy:")):
        parts = text.split(":")
        composite = parts[0] == "build_then_policy"
        valid_lengths = (8,) if composite else (3, 6)
        if len(parts) not in valid_lengths:
            raise ValueError(
                "build/farm phase must be <kind>:<crop>:<animal> or "
                "<kind>:<crop>:<animal>:<land>:<crops>:<herd>; "
                "build_then_policy additionally needs :<npz_path>:<temperature>")
        crop, animal = parts[1].upper(), parts[2].upper()
        if crop not in A.CROP_LIST:
            raise ValueError(f"unknown crop in option {text!r}")
        if animal not in A.ANIMAL_LIST:
            raise ValueError(f"unknown animal in option {text!r}")
        structure = engine_t.E.ANIMALS[animal]["structure"]
        parsed = {
            "name": text,
            "kind": parts[0],
            "crop": crop,
            "crop_index": A.CROP_LIST.index(crop),
            "seed_market_index": A.MARKET_ACTIONS.index(f"BUY_SEED_{crop}"),
            "plant_index": A.FARMER_ACTIONS.index(f"PLANT_{crop}"),
            "animal": animal,
            "animal_index": engine_t.ITEM_IDX[animal],
            "animal_board_index": engine_t.ANIMAL_IDX[animal],
            "animal_market_index": A.MARKET_ACTIONS.index(f"BUY_{animal}"),
            "place_index": A.FARMER_ACTIONS.index(f"PLACE_{animal}"),
            "build_index": A.FARMER_ACTIONS.index(f"BUILD_{structure}"),
            "structure_code": engine_t.STRUCT_CODE[structure],
            "animal_cost": engine_t.E.ANIMALS[animal]["cost"],
        }
        if len(parts) >= 6:
            try:
                land, crops, herd = (int(value) for value in parts[3:6])
            except ValueError as exc:
                raise ValueError(
                    f"non-integer build_phase target in {text!r}") from exc
            if land < 1 or crops < 0 or herd < 0:
                raise ValueError(
                    "build_phase targets must be non-negative and land >= 1")
            parsed["targets"] = {
                "land": land, "crops": crops, "herd": herd}
        if composite:
            try:
                temperature = float(parts[7])
            except ValueError as exc:
                raise ValueError(
                    f"invalid policy temperature in {text!r}") from exc
            if not parts[6] or temperature < 0:
                raise ValueError(
                    "build_then_policy needs an npz path and temperature >= 0")
            parsed["path"] = parts[6]
            parsed["temperature"] = temperature
        return parsed
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
        "opp_money": float(ep.money[lane, opp]),
        "margin": float(ep.money[lane, seat] - ep.money[lane, opp]),
        "future_worth": float(env._pot(ep, seat)[lane]),
        **{f"final_{key}": float(value[lane]) for key, value in current.items()},
        **{f"max_{key}": float(value[lane]) for key, value in max_state.items()},
    }


def _paired_delta_record(base, intervention):
    return {key: intervention[key] - base[key] for key in base}


def _affords_with_reserve(money, cost, cash_reserve):
    return float(money) >= float(cost) + float(cash_reserve)


def _option_targets(option, land, crops, herd):
    return option.get("targets", {
        "land": int(land), "crops": int(crops), "herd": int(herd)})


def _build_phase_state(ep, lane, seat, option):
    """Observable execution state for an absolute construction milestone."""
    animal_i = option["animal_index"]
    return {
        "land": 1 + int(ep.quad_unlocked[lane, seat].sum()),
        "crops": int((ep.kind[lane, seat] == engine_t.K_PLANT).sum()),
        "herd": int((ep.animal[lane, seat] >= 0).sum()),
        "seeds": int(ep.seeds_t[lane, seat, option["crop_index"]]),
        "unplaced": (
            int(ep.shed[lane, seat, animal_i])
            + int(ep.unit_inv[lane, seat, :, animal_i].sum())),
        "open_structure": int((
            (ep.kind[lane, seat] == option["structure_code"])
            & (ep.animal[lane, seat] < 0)).sum()),
        "wheat": (
            int(ep.shed[lane, seat, engine_t.WHEAT_I])
            + int(ep.unit_inv[lane, seat, :, engine_t.WHEAT_I].sum())),
        "unfed": int(((ep.animal[lane, seat] >= 0)
                      & ~ep.fed[lane, seat]).sum()),
    }


def _build_phase_complete(progress, land_target, crop_target, herd_target):
    return (progress["land"] >= land_target
            and progress["crops"] >= crop_target
            and progress["herd"] >= herd_target)


def _build_phase_delta(progress, start):
    return {key: progress[key] - start[key]
            for key in ("land", "crops", "herd")}


def _apply_build_phase(action, td, ep, lane, seat, option, counters,
                       land_target, crop_target, herd_target, cash_reserve):
    """Advance one coupled land/crop/herd milestone with minimal overrides."""
    p = _build_phase_state(ep, lane, seat, option)
    money = float(ep.money[lane, seat])

    # The farmer only handles construction. Repeated PLANT intent monopolises
    # it for long walks and starves the existing farm; planting is delegated to
    # a bounded number of hands below.
    if p["herd"] < herd_target and p["unplaced"] > 0 and bool(
            td["farmer_mask"][lane, option["place_index"]]):
        if int(action[lane, 0]) != option["place_index"]:
            counters["place_animal"] += 1
        action[lane, 0] = option["place_index"]
    elif (p["herd"] + p["unplaced"] < herd_target
          and p["open_structure"] <= p["unplaced"]
          and bool(td["farmer_mask"][lane, option["build_index"]])):
        if int(action[lane, 0]) != option["build_index"]:
            counters["build_structure"] += 1
        action[lane, 0] = option["build_index"]

    # Reserve at most two hands per missing task family. Prefer slots the
    # policy already left IDLE/AUTO and leave every other hand decision intact;
    # rewriting the entire crew to AUTO was itself a large intervention.
    if action.shape[-1] > 2:
        live_hands = min(int(ep.hands_n[lane, seat]), A.MAX_HANDS)
        desired = []
        if p["unfed"] > 0 and p["wheat"] > 0:
            desired.extend([A.HAND_TASKS.index("FEED")] * min(2, p["unfed"]))
        if p["crops"] < crop_target and p["seeds"] > 0:
            desired.extend([A.HAND_TASKS.index("PLANT")] * min(2, p["seeds"]))
        idle_i = A.HAND_TASKS.index("IDLE")
        auto_i = A.HAND_TASKS.index("AUTO")
        slots = sorted(
            range(live_hands),
            key=lambda slot: (
                int(action[lane, 2 + slot]) not in (idle_i, auto_i), slot))
        for slot, task_i in zip(slots, desired):
            if not bool(td["hand_mask"][lane, slot, task_i]):
                continue
            if int(action[lane, 2 + slot]) != task_i:
                counters[f"hand_{A.HAND_TASKS[task_i].lower()}"] += 1
            action[lane, 2 + slot] = task_i

    # Preserve the policy's morning hiring burst before spending on assets.
    hour = int(ep._step % ep.turns_per_day)
    if hour <= 3 and int(action[lane, 1]) == _HIRE:
        return

    # Capacity, daily feed, livestock, then seed. If no required purchase is
    # affordable, preserve the frozen policy action, including income sales.
    if p["land"] < land_target:
        extra_land = int(ep.quad_unlocked[lane, seat].sum())
        land_cost = engine_t.E.LAND_PRICES[
            min(extra_land, len(engine_t.E.LAND_PRICES) - 1)]
        if (bool(td["market_mask"][lane, _BUY_LAND])
                and _affords_with_reserve(money, land_cost, cash_reserve)):
            if int(action[lane, 1]) != _BUY_LAND:
                counters["buy_land"] += 1
            action[lane, 1] = _BUY_LAND
            return

    owned_herd = p["herd"] + p["unplaced"]
    if owned_herd < herd_target:
        feed_target = min(28, 3 * min(herd_target, p["herd"] + 1))
        wheat_qty = max(5, 2 * p["herd"])
        wheat_cost = wheat_qty * float(ep.mkt_price[lane, engine_t.WHEAT_I])
        if (p["wheat"] < feed_target
                and bool(td["market_mask"][lane, _BUY_WHEAT])
                and _affords_with_reserve(money, wheat_cost, cash_reserve)):
            if int(action[lane, 1]) != _BUY_WHEAT:
                counters["buy_wheat"] += 1
            action[lane, 1] = _BUY_WHEAT
            return
        if (p["unplaced"] == 0
                and bool(td["market_mask"][lane, option["animal_market_index"]])
                and _affords_with_reserve(
                    money, option["animal_cost"], cash_reserve)):
            if int(action[lane, 1]) != option["animal_market_index"]:
                counters["buy_animal"] += 1
            action[lane, 1] = option["animal_market_index"]
            return

    crop_committed = p["crops"] + p["seeds"]
    seed_cost = engine_t.CROP_SEED_COST[option["crop_index"]]
    if (crop_committed < crop_target
            and bool(td["market_mask"][lane, option["seed_market_index"]])
            and _affords_with_reserve(money, seed_cost, cash_reserve)):
        if int(action[lane, 1]) != option["seed_market_index"]:
            counters["buy_seed"] += 1
        action[lane, 1] = option["seed_market_index"]


def _apply_auto_hands(action, td, ep, lane, seat, counters):
    """Delegate all currently hired hands to the engine's scripted scheduler."""
    if action.shape[-1] <= 2:
        return
    auto_i = A.HAND_TASKS.index("AUTO")
    live_hands = min(int(ep.hands_n[lane, seat]), A.MAX_HANDS)
    for slot in range(live_hands):
        if not bool(td["hand_mask"][lane, slot, auto_i]):
            continue
        if int(action[lane, 2 + slot]) != auto_i:
            counters["hand_auto"] += 1
        action[lane, 2 + slot] = auto_i


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
                        max_trigger_demand_milk=-1, land_target=2,
                        steps_override=0):
    _, saved, actor_net, _, multi = _load_checkpoint(checkpoint, device)
    option = _parse_option(option_text)
    targets = _option_targets(
        option, land_target, crop_target, herd_target)
    land_target = targets["land"]
    crop_target = targets["crops"]
    herd_target = targets["herd"]
    option_actor = option_multi = option_generator = None
    if option["kind"] in {"policy_npz", "build_then_policy"}:
        option_actor, option_multi = _load_export_actor(option["path"], device)
        if option_multi != multi:
            raise ValueError(
                "policy_npz hand-head shape must match the baseline checkpoint")
        option_generator = torch.Generator(device=device)
        option_generator.manual_seed(seed + 0x5EED)
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
        alternate_action = None
        if option_actor is not None:
            alternate_action = _policy_at_temperature(
                option_actor, td, option_multi, option["temperature"],
                option_generator)
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
                if option["kind"] in {
                        "build_phase", "farm_phase", "hands_auto",
                        "policy_npz", "build_then_policy"}:
                    eligible = True
                elif option["kind"] in {"expand_land", "expand_crop"}:
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
                    context = {
                        key: int(value[odd]) for key, value in state.items()}
                    context.update({
                        "money": float(ep.money[odd, seat]),
                        "opp_money": float(ep.money[odd, 1 - seat]),
                        "future_worth": float(env._pot(ep, seat)[odd]),
                    })
                    context.update(_strategic_context(ep, odd, seat))
                    selected[pair] = (
                        option["kind"] != "select_herd"
                        or _select_herd_context(
                            context, max_trigger_money,
                            max_trigger_demand_milk))
                    trigger_step[pair] = ep._step
                    start_value[pair] = context
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
                elif option["kind"] in {
                        "build_phase", "farm_phase", "build_then_policy"}:
                    completion_target_delta[pair] = _build_phase_delta(
                        _build_phase_state(ep, odd, seat, option),
                        start_value[pair])
                elif option["kind"] == "hands_auto":
                    success[pair] = True
                    completion_target_delta[pair] = sum(
                        forced_actions[pair].values())
                elif option["kind"] == "policy_npz":
                    success[pair] = True
                    completion_target_delta[pair] = timeout
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
            if option["kind"] in {
                    "build_phase", "farm_phase", "build_then_policy"}:
                milestone_met = _build_phase_complete(
                    _build_phase_state(ep, odd, seat, option),
                    land_target, crop_target, herd_target)
                if option["kind"] == "farm_phase" and milestone_met:
                    _apply_auto_hands(
                        action, td, ep, odd, seat, forced_actions[pair])
                elif option["kind"] == "build_then_policy" and milestone_met:
                    if not torch.equal(action[odd], alternate_action[odd]):
                        forced_actions[pair]["policy_steps"] += 1
                    action[odd] = alternate_action[odd]
                else:
                    _apply_build_phase(
                        action, td, ep, odd, seat, option, forced_actions[pair],
                        land_target, crop_target, herd_target, cash_reserve)
            elif option["kind"] == "hands_auto":
                _apply_auto_hands(
                    action, td, ep, odd, seat, forced_actions[pair])
            elif option["kind"] == "policy_npz":
                if not torch.equal(action[odd], alternate_action[odd]):
                    forced_actions[pair]["policy_steps"] += 1
                action[odd] = alternate_action[odd]
            elif option["kind"] in {"expand_land", "expand_crop"} and not land_complete:
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
                elif option["kind"] in {
                        "build_phase", "farm_phase", "build_then_policy"}:
                    milestone_met = _build_phase_complete(
                        _build_phase_state(ep, odd, seat, option),
                        land_target, crop_target, herd_target)
                    success[pair] = success[pair] or milestone_met
                elif option["kind"] == "hands_auto":
                    success[pair] = elapsed >= timeout or bool(ep.done)
                elif option["kind"] == "policy_npz":
                    success[pair] = elapsed >= timeout or bool(ep.done)
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
                persistent = option["kind"] in {
                    "operate_herd", "farm_phase", "hands_auto",
                    "policy_npz", "build_then_policy"}
                finished[pair] = ((success[pair] and not persistent)
                                  or elapsed >= timeout or (persistent and ep.done))
                if finished[pair]:
                    completion_elapsed[pair] = min(timeout, elapsed)
                    if option["kind"] == "preserve_cash":
                        completion_target_delta[pair] = (
                            float(ep.money[odd, seat]) - start_value[pair]["money"])
                    elif option["kind"] in {
                            "build_phase", "farm_phase", "build_then_policy"}:
                        completion_target_delta[pair] = _build_phase_delta(
                            _build_phase_state(ep, odd, seat, option),
                            start_value[pair])
                    elif option["kind"] == "hands_auto":
                        completion_target_delta[pair] = sum(
                            forced_actions[pair].values())
                    elif option["kind"] == "policy_npz":
                        completion_target_delta[pair] = min(timeout, elapsed)
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
        "targets": (targets if option["kind"] in {
            "build_phase", "farm_phase", "build_then_policy"} else None),
        "lanes": lanes,
        "triggered": len(used),
        "successes": sum(bool(row.get("option_success")) for row in used),
        "summary": summary,
        "records": records,
    }


def _win_from_margin(margin):
    return float(margin > 0) + 0.5 * float(margin == 0)


def option_oracle_summary(cells, options, seed, successful_only=False):
    """Optimistic state-wise upper bound over independently rolled options."""
    grouped = defaultdict(dict)
    for cell in cells:
        option = cell["option"]
        for row in cell["records"]:
            if not row.get("triggered"):
                continue
            key = (cell["opponent"], int(cell["seat"]), int(row["seed"]))
            grouped[key][option] = row

    oracle_rows = []
    incomplete_states = 0
    for (opponent, seat, state_seed), by_option in sorted(grouped.items()):
        if any(option not in by_option for option in options):
            incomplete_states += 1
            continue
        first = by_option[options[0]]["baseline"]
        for option in options[1:]:
            other = by_option[option]["baseline"]
            if first != other:
                raise AssertionError(
                    f"baseline mismatch for oracle state "
                    f"{opponent}@seat{seat}/seed{state_seed}")

        chosen_name = "FOLLOW_POLICY"
        chosen = first
        for option in options:
            row = by_option[option]
            if successful_only and not row.get("option_success"):
                continue
            candidate = row["intervention"]
            if candidate["margin"] > chosen["margin"]:
                chosen_name, chosen = option, candidate
        delta = _paired_delta_record(first, chosen)
        delta["win"] = (_win_from_margin(chosen["margin"])
                        - _win_from_margin(first["margin"]))
        oracle_rows.append({
            "opponent": opponent,
            "seat": seat,
            "seed": state_seed,
            "choice": chosen_name,
            "baseline": first,
            "oracle": chosen,
            "delta": delta,
        })

    clusters = [row["seed"] for row in oracle_rows]
    metrics = sorted({key for row in oracle_rows for key in row["delta"]})
    by_cell = {}
    for opponent, seat in sorted({
            (row["opponent"], row["seat"]) for row in oracle_rows}):
        rows = [row for row in oracle_rows
                if row["opponent"] == opponent and row["seat"] == seat]
        by_cell[f"{opponent}@seat{seat}"] = {
            "n": len(rows),
            "baseline_wins": sum(
                _win_from_margin(row["baseline"]["margin"]) for row in rows),
            "oracle_wins": sum(
                _win_from_margin(row["oracle"]["margin"]) for row in rows),
            "baseline_margin": _describe(
                [row["baseline"]["margin"] for row in rows]),
            "oracle_margin": _describe(
                [row["oracle"]["margin"] for row in rows]),
            "margin_delta": paired_summary(
                [row["delta"]["margin"] for row in rows],
                seed=seed, clusters=[row["seed"] for row in rows]),
        }
    choices = defaultdict(int)
    for row in oracle_rows:
        choices[row["choice"]] += 1
    return {
        "label": ("completed options only" if successful_only
                  else "all rolled option branches"),
        "optimistic_upper_bound": True,
        "states": len(oracle_rows),
        "states_missing_an_option": incomplete_states,
        "choice_counts": dict(sorted(choices.items())),
        "baseline_wins": sum(
            _win_from_margin(row["baseline"]["margin"])
            for row in oracle_rows),
        "oracle_wins": sum(
            _win_from_margin(row["oracle"]["margin"])
            for row in oracle_rows),
        "metrics": {
            key: paired_summary(
                [row["delta"][key] for row in oracle_rows],
                seed=seed + i, clusters=clusters)
            for i, key in enumerate(metrics)
        },
        "by_cell": by_cell,
        "records": oracle_rows,
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
                    args.max_trigger_money, args.max_trigger_demand_milk,
                    args.land_target, args.steps))

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
                [row["delta"][key] for row in rows], seed=args.seed + i,
                clusters=[row["seed"] for row in rows])
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

    oracle = None
    if len(args.option) > 1:
        oracle = {
            "all_branches": option_oracle_summary(
                cells, args.option, args.seed, successful_only=False),
            "completed_only": option_oracle_summary(
                cells, args.option, args.seed, successful_only=True),
        }
        for name, result in oracle.items():
            margin = result["metrics"].get("margin", {})
            print(f"ORACLE kind={name} states={result['states']} "
                  f"wins={result['baseline_wins']}->{result['oracle_wins']} "
                  f"margin_delta={margin.get('mean')}", flush=True)

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
        "land_target": args.land_target,
        "cash_reserve": args.cash_reserve,
        "max_trigger_money": args.max_trigger_money or None,
        "max_trigger_demand_milk": (
            args.max_trigger_demand_milk
            if args.max_trigger_demand_milk >= 0 else None),
        "options": list(args.option),
        "gate": (
            "terminal paired margin bootstrap CI excludes zero and heldout "
            "cells keep the same sign; option must complete and move the "
            "target behavior"),
        "summary": option_summary,
        "oracle": oracle,
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
    cf.add_argument("--land-target", type=int, default=2,
                    help="absolute land milestone for build_phase")
    cf.add_argument("--max-trigger-money", type=int, default=0,
                    help="select_herd takes the option only at or below this cash")
    cf.add_argument("--max-trigger-demand-milk", type=int, default=-1,
                    help="select_herd takes the option only at or below this "
                         "unlocked-shop milk demand (-1 disables the gate)")
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
            and any(option.startswith(("build_phase:", "farm_phase:",
                                       "build_then_policy:"))
                    for option in args.option)
            and (args.land_target < 1 or args.crop_target < 0
                 or args.herd_target < 0)):
        parser.error("build_phase targets must be non-negative and land >= 1")
    if (args.command == "counterfactual"
            and any(option.startswith("select_herd:") for option in args.option)
            and args.max_trigger_money <= 0
            and args.max_trigger_demand_milk < 0):
        parser.error("select_herd requires at least one trigger gate")
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
