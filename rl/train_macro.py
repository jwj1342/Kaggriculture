#!/usr/bin/env python
"""Train the option-lite high-level controller with variable-duration PPO."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

import torch

_HERE = Path(__file__).resolve().parent
_TENSOR = _HERE / "tensor_env"
for _path in (_HERE, _TENSOR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from macro_hierarchy import (MACRO_OBS_DIM, N_OPTIONS, OPTION_NAMES,  # noqa: E402
                             TERMINATION_NAMES, MacroActorCritic,
                             MacroGame, masked_categorical,
                             semimdp_gae)


DEFAULT_OPPONENTS = (
    "tape:agents/bench3/closer_cleo.py",
    "tape:agents/bench3/ledger_lena.py",
    "tape:agents/bench3/broker_bea.py",
)


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", default="rl/runs/anvil/latest.pt")
    parser.add_argument("--opponents", default=",".join(DEFAULT_OPPONENTS))
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--threads", type=int, default=0)
    parser.add_argument("--B", type=int, default=32,
                        help="full seasons collected per PPO iteration")
    parser.add_argument("--iters", type=int, default=20)
    parser.add_argument("--seed", type=int, default=5080825)
    parser.add_argument("--seat", choices=("0", "1", "alt"), default="alt")
    parser.add_argument("--gamma", type=float, default=0.999)
    parser.add_argument("--lam", type=float, default=0.95)
    parser.add_argument("--option-timeout", type=int, default=240)
    parser.add_argument("--steps", type=int, default=720,
                        help="season length; 720 for all scored experiments")
    parser.add_argument("--hidden", type=int, nargs=2, default=(256, 128))
    parser.add_argument("--route-bias", type=float, default=1.5)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--clip", type=float, default=0.2)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--minibatches", type=int, default=4)
    parser.add_argument("--ent-coef", type=float, default=0.01)
    parser.add_argument("--vf-coef", type=float, default=0.5)
    parser.add_argument("--max-grad-norm", type=float, default=0.5)
    parser.add_argument("--save", default="")
    parser.add_argument("--resume", default="")
    parser.add_argument("--log", default="")
    parser.add_argument("--max-minutes", type=float, default=0.0)
    parser.add_argument("--eval-every", type=int, default=0)
    parser.add_argument("--eval-lanes", type=int, default=16)
    parser.add_argument(
        "--eval-opponents",
        default="tape:agents/bench3/closer_cleo.py,tape:agents/wrapped/w49.py")
    parser.add_argument("--quiet", action="store_true")
    return parser


def _atomic_save(value, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(value, temporary)
    os.replace(temporary, path)


def _append_jsonl(path, value):
    if not path:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")


def _seat(args, iteration):
    return iteration % 2 if args.seat == "alt" else int(args.seat)


def _flatten(chunks):
    keys = chunks[0].keys()
    return {key: torch.cat([chunk[key] for chunk in chunks], 0)
            for key in keys}


@torch.no_grad()
def collect(controller, args, opponent, seat, seed, deterministic=False):
    game = MacroGame(
        args.checkpoint, opponent, args.B, seed, args.device, seat,
        args.gamma, args.option_timeout, steps_override=args.steps)
    game.reset()
    chunks = []
    sequence = torch.zeros(args.B, dtype=torch.int64, device=game.device)
    trajectory_base = seed * args.B

    while True:
        inactive = ~game.lifecycle.active
        if bool(inactive.any()):
            state = game.observation()
            action_mask = game.action_mask()
            logits, value = controller(state)
            distribution = masked_categorical(logits, action_mask)
            option_id = (logits.masked_fill(~action_mask, -1e9).argmax(-1)
                         if deterministic else distribution.sample())
            game.start_options(
                inactive, option_id, state, action_mask,
                distribution.log_prob(option_id), value, distribution.probs)

        completed, done = game.step()
        for chunk in completed:
            lanes = chunk["lane"]
            chunk["trajectory"] = lanes + trajectory_base
            chunk["sequence"] = sequence[lanes].clone()
            sequence[lanes] += 1
            chunks.append(chunk)
        if done:
            break

    transitions = _flatten(chunks)
    _, next_value = controller(transitions["next_state"])
    transitions["next_value"] = next_value
    terminal = game.terminal_metrics()
    metrics = summarize_rollout(transitions, terminal, sequence, opponent, seat)
    return transitions, metrics


def summarize_rollout(transitions, terminal, decisions, opponent, seat):
    action = transitions["action"]
    tau = transitions["tau"].to(torch.float32)
    probs = transitions["old_probs"].clamp_min(1e-12)
    result = {
        "opponent": opponent,
        "seat": int(seat),
        "episodes": int(terminal["margin"].numel()),
        "decisions": int(action.numel()),
        "decisions_per_episode": float(decisions.float().mean()),
        "money": float(terminal["money"].mean()),
        "opp_money": float(terminal["opp_money"].mean()),
        "margin": float(terminal["margin"].mean()),
        "win": float(terminal["win"].mean()),
        "entropy": float((-(probs * probs.log()).sum(-1)).mean()),
        "options": {},
        "terminations": {},
    }
    for option_id, name in enumerate(OPTION_NAMES):
        selected = action == option_id
        contribution = -(probs[:, option_id] * probs[:, option_id].log())
        completed = selected & (
            transitions["reason"] != TERMINATION_NAMES.index("TIMEOUT"))
        result["options"][name] = {
            "count": int(selected.sum()),
            "mean_tau": float(tau[selected].mean()) if bool(selected.any()) else None,
            "completion_rate": (float(completed.sum()) / int(selected.sum())
                                if bool(selected.any()) else None),
            "mean_discounted_return": (
                float(transitions["reward"][selected].mean())
                if bool(selected.any()) else None),
            "entropy_contribution": float(contribution.mean()),
        }
    for reason_id, name in enumerate(TERMINATION_NAMES):
        count = int((transitions["reason"] == reason_id).sum())
        if count:
            result["terminations"][name] = count
    return result


def prepare_advantages(controller, transitions, lam):
    with torch.no_grad():
        _, next_value = controller(transitions["next_state"])
        advantage, target = semimdp_gae(
            transitions["reward"], transitions["old_value"], next_value,
            transitions["gamma_tau"], transitions["done"],
            transitions["trajectory"], transitions["sequence"], lam)
        advantage = (advantage - advantage.mean()) / (
            advantage.std(unbiased=False) + 1e-8)
    transitions["advantage"] = advantage
    transitions["value_target"] = target
    return transitions


def ppo_update(controller, optimizer, transitions, args):
    count = transitions["action"].numel()
    batch_size = max(1, count // args.minibatches)
    totals = defaultdict(float)
    updates = 0
    controller.train()
    for _ in range(args.epochs):
        permutation = torch.randperm(count, device=transitions["action"].device)
        for start in range(0, count, batch_size):
            index = permutation[start:start + batch_size]
            logits, value = controller(transitions["state"][index])
            distribution = masked_categorical(
                logits, transitions["action_mask"][index])
            log_prob = distribution.log_prob(transitions["action"][index])
            ratio = (log_prob - transitions["old_log_prob"][index]).exp()
            advantage = transitions["advantage"][index]
            policy_loss = -torch.minimum(
                ratio * advantage,
                ratio.clamp(1.0 - args.clip, 1.0 + args.clip) * advantage,
            ).mean()
            old_value = transitions["old_value"][index]
            target = transitions["value_target"][index]
            clipped_value = old_value + (value - old_value).clamp(
                -args.clip, args.clip)
            value_loss = 0.5 * torch.maximum(
                (value - target).square(),
                (clipped_value - target).square()).mean()
            entropy = distribution.entropy().mean()
            loss = policy_loss + args.vf_coef * value_loss - args.ent_coef * entropy
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            grad_norm = torch.nn.utils.clip_grad_norm_(
                controller.parameters(), args.max_grad_norm)
            optimizer.step()
            approx_kl = ((ratio - 1.0) - ratio.log()).mean()
            clip_fraction = ((ratio - 1.0).abs() > args.clip).float().mean()
            for key, value_ in {
                    "loss": loss, "policy_loss": policy_loss,
                    "value_loss": value_loss, "entropy_update": entropy,
                    "approx_kl": approx_kl, "clip_fraction": clip_fraction,
                    "grad_norm": grad_norm}.items():
                totals[key] += float(value_.detach())
            updates += 1
    return {key: value / updates for key, value in totals.items()}


@torch.no_grad()
def evaluate(controller, args, iteration):
    old_B = args.B
    args.B = args.eval_lanes
    rows = []
    try:
        for opponent_index, opponent in enumerate(
                value for value in args.eval_opponents.split(",") if value):
            for seat in (0, 1):
                seed = args.seed + 90_000_000 + iteration * 10_000 \
                    + opponent_index * 1_000 + seat * 100
                _, row = collect(
                    controller, args, opponent, seat, seed,
                    deterministic=True)
                rows.append(row)
    finally:
        args.B = old_B
    total = sum(row["episodes"] for row in rows)
    return {
        "episodes": total,
        "win": sum(row["win"] * row["episodes"] for row in rows) / total,
        "margin": sum(row["margin"] * row["episodes"] for row in rows) / total,
        "cells": rows,
    }


def checkpoint_payload(controller, optimizer, args, iteration, episodes):
    return {
        "schema": 1,
        "kind": "option_lite_ppo",
        "model": controller.state_dict(),
        "optimizer": optimizer.state_dict(),
        "iter": int(iteration),
        "episodes": int(episodes),
        "macro_obs_dim": MACRO_OBS_DIM,
        "option_names": OPTION_NAMES,
        "args": vars(args),
        "torch_rng_state": torch.get_rng_state(),
    }


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.threads:
        torch.set_num_threads(args.threads)
    if args.B <= 0 or args.iters <= 0:
        raise ValueError("--B and --iters must be positive")
    if not 0.0 < args.gamma <= 1.0 or not 0.0 <= args.lam <= 1.0:
        raise ValueError("gamma and lambda must be probabilities")
    opponents = [value for value in args.opponents.split(",") if value]
    if not opponents:
        raise ValueError("--opponents must contain at least one opponent")
    device = torch.device(args.device)
    torch.manual_seed(args.seed)
    controller = MacroActorCritic(
        hidden=args.hidden, route_bias=args.route_bias).to(device)
    optimizer = torch.optim.Adam(controller.parameters(), lr=args.lr, eps=1e-5)
    first_iteration = 0
    total_episodes = 0
    if args.resume:
        saved = torch.load(args.resume, map_location=device, weights_only=False)
        if tuple(saved.get("option_names", ())) != OPTION_NAMES:
            raise ValueError("resume checkpoint has a different Option vocabulary")
        controller.load_state_dict(saved["model"])
        optimizer.load_state_dict(saved["optimizer"])
        first_iteration = int(saved.get("iter", -1)) + 1
        total_episodes = int(saved.get("episodes", 0))
        if saved.get("torch_rng_state") is not None:
            torch.set_rng_state(saved["torch_rng_state"].cpu())

    started = time.perf_counter()
    for iteration in range(first_iteration, args.iters):
        before = time.perf_counter()
        opponent = opponents[iteration % len(opponents)]
        seat = _seat(args, iteration)
        seed = args.seed + iteration * 100_000
        controller.eval()
        transitions, rollout = collect(
            controller, args, opponent, seat, seed, deterministic=False)
        transitions = prepare_advantages(controller, transitions, args.lam)
        update = ppo_update(controller, optimizer, transitions, args)
        total_episodes += args.B
        row = {
            "iter": iteration,
            "episodes": total_episodes,
            "seconds": time.perf_counter() - before,
            **rollout,
            **update,
        }
        if args.eval_every and (
                (iteration + 1) % args.eval_every == 0
                or iteration + 1 == args.iters):
            controller.eval()
            row["eval"] = evaluate(controller, args, iteration)
        _append_jsonl(args.log, row)
        if args.save:
            _atomic_save(checkpoint_payload(
                controller, optimizer, args, iteration, total_episodes),
                args.save)
        if not args.quiet:
            counts = "/".join(
                str(row["options"][name]["count"]) for name in OPTION_NAMES)
            message = (
                f"it {iteration:03d} ep {total_episodes:5d} "
                f"dec {row['decisions']:4d} opts {counts} "
                f"win {row['win']:.3f} margin {row['margin']:+,.0f} "
                f"ent {row['entropy']:.3f} pg {row['policy_loss']:+.4f} "
                f"vf {row['value_loss']:.4f} {row['seconds']:.1f}s")
            if "eval" in row:
                message += (f" eval {row['eval']['win']:.3f}/"
                            f"{row['eval']['margin']:+,.0f}")
            print(message, flush=True)
        if args.max_minutes and (
                time.perf_counter() - started) / 60.0 >= args.max_minutes:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
