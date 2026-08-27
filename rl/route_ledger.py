#!/usr/bin/env python
"""Paired phase ledger for a state-closed route and its open-loop teacher.

Both branches start from the same engine seed and face the same recorded
opponent.  The teacher is used only as a diagnostic ceiling: no teacher action
is emitted by a candidate policy or written into a checkpoint.

Cash ``positive_turns`` and ``negative_turns`` are the positive and negative
parts of each turn's *net* money delta.  They are intentionally not called
receipts/outlays because a turn may execute sales and purchases together.
Order quantities are submitted intent; asset deltas and cash deltas are engine
outcomes.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "rl", ROOT / "rl" / "tensor_env"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import barnyard_t  # noqa: E402
import engine_t  # noqa: E402
import engine_t_idx as X  # noqa: E402
import macro_audit  # noqa: E402
import tape_t  # noqa: E402


POLICIES = ("candidate", "teacher")
PHASE_END_DAYS = (1, 8, 12, 15, 20, 25, 30)
PHASE_NAMES = tuple(
    f"d{start}-{end}" for start, end in zip((0, *PHASE_END_DAYS[:-1]),
                                             PHASE_END_DAYS))


def _phase_index(day):
    for index, end in enumerate(PHASE_END_DAYS):
        if day < end:
            return index
    return len(PHASE_END_DAYS) - 1


def _state(ep, seat):
    B = ep.B
    kind = ep.kind[:, seat]
    board_animals = (ep.animal[:, seat] >= 0).sum((-1, -2)).to(torch.float64)
    active = (torch.arange(ep.unit_inv.shape[2], device=ep.device).view(1, -1)
              <= ep.hands_n[:, seat].to(torch.int64).view(B, 1))
    carried_animals = (
        ep.unit_inv[:, seat, :, engine_t.N_MKT:].to(torch.int64)
        * active.unsqueeze(-1)).sum((1, 2)).to(torch.float64)
    shed_animals = ep.shed[:, seat, engine_t.N_MKT:].sum(1).to(torch.float64)
    return {
        "money": ep.money[:, seat].clone(),
        "opp_money": ep.money[:, 1 - seat].clone(),
        "land": (1 + ep.quad_unlocked[:, seat].sum(1)).to(torch.float64),
        "crops": (kind == engine_t.K_PLANT).sum((-1, -2)).to(torch.float64),
        "herd": board_animals,
        "animals_owned": board_animals + carried_animals + shed_animals,
        "hands": ep.hands_n[:, seat].to(torch.float64),
        "seeds": ep.seeds_t[:, seat].to(torch.float64).clone(),
        "kind": kind.clone(),
    }


def _order_stats(ops, hands_n):
    m_op = ops["m_op"]
    m_item = ops["m_item"]
    m_rem = ops["m_rem"].to(torch.float64)
    unit_ops = torch.stack([ops["f_op"], *ops["h_op"]], 1)
    unit_qty = torch.stack([ops["f_qty"], *ops["h_qty"]], 1).to(torch.float64)
    active = (torch.arange(unit_ops.shape[1], device=unit_ops.device).view(1, -1)
              <= hands_n.to(torch.int64).view(-1, 1))
    stats = {
        "sell_order_units": torch.where(
            m_op == engine_t.OP_SELL, m_rem, 0.0).sum(1),
        "buy_product_order_units": torch.where(
            m_op == engine_t.OP_BUYP, m_rem, 0.0).sum(1),
        "buy_seed_order_units": torch.where(
            m_op == engine_t.OP_SEED, m_rem, 0.0).sum(1),
        "buy_animal_order_units": torch.where(
            m_op == engine_t.OP_ANIMAL, m_rem, 0.0).sum(1),
        "hire_orders": (m_op == X.OP_HIRE).sum(1).to(torch.float64),
        "land_orders": (m_op == X.OP_LAND).sum(1).to(torch.float64),
        "active_unit_turns": active.sum(1).to(torch.float64),
    }
    unit_groups = {
        "pass": (X.U_PASS,),
        "move": (X.U_MOVE_N, X.U_MOVE_S, X.U_MOVE_E, X.U_MOVE_W),
        "water": (X.U_WATER,),
        "harvest": (X.U_HARVEST,),
        "feed": (X.U_FEED,),
        "care": (X.U_CARE,),
        "collect": (X.U_COLLECT,),
        "fertilize": (X.U_FERTILIZE,),
        "build": (X.U_BUILD_COOP, X.U_BUILD_PASTURE),
        "plant": (X.U_PLANT,),
        "place": (X.U_PLACE,),
        "pickup": (X.U_PICKUP,),
        "drop": (X.U_DROP,),
    }
    for name, codes in unit_groups.items():
        selected = torch.zeros_like(active)
        for code in codes:
            selected |= unit_ops == code
        stats[f"unit_{name}"] = (selected & active).sum(1).to(torch.float64)
        if name in {"pickup", "drop"}:
            stats[f"unit_{name}_units"] = torch.where(
                selected & active, unit_qty, 0.0).sum(1)
    for item, name in enumerate(engine_t.PRODUCTS):
        stats[f"sell_{name}_order_units"] = torch.where(
            (m_op == engine_t.OP_SELL) & (m_item == item), m_rem, 0.0).sum(1)
        stats[f"buy_product_{name}_order_units"] = torch.where(
            (m_op == engine_t.OP_BUYP) & (m_item == item), m_rem, 0.0).sum(1)
    for item, name in enumerate(engine_t.CROP_NAMES):
        stats[f"buy_seed_{name}_order_units"] = torch.where(
            (m_op == engine_t.OP_SEED) & (m_item == item), m_rem, 0.0).sum(1)
    return stats


def _new_accumulator(lanes, device):
    return {
        policy: [defaultdict(
            lambda: torch.zeros(lanes, dtype=torch.float64, device=device))
                 for _ in PHASE_NAMES]
        for policy in POLICIES
    }


def _take(values, indices):
    return values.index_select(0, indices).to(torch.float64)


def _summarize(values):
    values = torch.as_tensor(values, dtype=torch.float64).cpu()
    n = int(values.numel())
    mean = float(values.mean()) if n else math.nan
    std = float(values.std(unbiased=True)) if n > 1 else 0.0
    return {"mean": mean, "std": std, "n": n}


def _summarize_cell(raw, lanes, seed, opponent, seat):
    policies = {}
    for policy in POLICIES:
        policies[policy] = {
            phase: {name: _summarize(value)
                    for name, value in raw[policy][index].items()}
            for index, phase in enumerate(PHASE_NAMES)
        }
    deltas = {}
    for index, phase in enumerate(PHASE_NAMES):
        common = sorted(set(raw["candidate"][index])
                        & set(raw["teacher"][index]))
        deltas[phase] = {
            name: _summarize(raw["teacher"][index][name]
                             - raw["candidate"][index][name])
            for name in common
        }
    pair_rows = []
    final = max(index for index in range(len(PHASE_NAMES))
                if "end_margin" in raw["candidate"][index])
    for lane in range(lanes):
        row = {"seed": seed + lane}
        for policy in POLICIES:
            phase = raw[policy][final]
            for metric in ("end_money", "end_opp_money", "end_margin"):
                row[f"{policy}_{metric}"] = float(phase[metric][lane])
        row["teacher_minus_candidate_margin"] = (
            row["teacher_end_margin"] - row["candidate_end_margin"])
        pair_rows.append(row)
    return {
        "opponent": opponent,
        "seat": seat,
        "seed_start": seed,
        "lanes": lanes,
        "policies": policies,
        "teacher_minus_candidate": deltas,
        "pairs": pair_rows,
    }


@torch.no_grad()
def run_cell(profile, teacher_path, opponent_path, checkpoint, lanes, seed,
             seat, device="cpu", steps=720, reference_profile=None):
    # Loading the checkpoint also validates the recorded low-level baseline
    # provenance.  Reward-shaping fields belong to KGTensorEnv, not EpisodeT;
    # this diagnostic reads engine state directly and only needs episode length.
    macro_audit._load_checkpoint(checkpoint, device)
    seeds = [seed + lane for lane in range(lanes) for _ in range(2)]
    ep = engine_t.EpisodeT(seeds, device=device, episode_steps=int(steps))
    B = ep.B
    candidate_indices = torch.arange(0, B, 2, device=ep.device)
    teacher_indices = candidate_indices + 1
    candidate_mask = torch.zeros(B, dtype=torch.bool, device=ep.device)
    candidate_mask[candidate_indices] = True
    teacher_mask = ~candidate_mask
    candidate = barnyard_t.BarnyardOpponent(profile)
    candidate.reset(ep, seat)
    if reference_profile:
        teacher = barnyard_t.BarnyardOpponent(reference_profile)
        teacher.reset(ep, seat)
    else:
        teacher = tape_t.TapeOpponent(teacher_path, device)
    opponent = tape_t.TapeOpponent(opponent_path, device)
    raw = _new_accumulator(lanes, ep.device)
    cumulative_plants = {
        policy: torch.zeros(lanes, dtype=torch.float64, device=ep.device)
        for policy in POLICIES
    }

    while not ep.done:
        day = ep._step // ep.turns_per_day
        phase = _phase_index(day)
        before = _state(ep, seat)
        candidate_ops = candidate(ep, seat, lane_mask=candidate_mask)
        teacher_ops = (teacher(ep, seat, lane_mask=teacher_mask)
                       if reference_profile else teacher(ep, seat))
        opponent_ops = opponent(ep, 1 - seat)
        branch = {
            "candidate": (candidate_indices, candidate_ops),
            "teacher": (teacher_indices, teacher_ops),
        }
        for policy, (indices, ops) in branch.items():
            stats = _order_stats(ops, before["hands"])
            for name, values in stats.items():
                raw[policy][phase][name] += _take(values, indices)

        zero = torch.zeros((B, 2), dtype=torch.int64, device=ep.device)
        ep.step_idx(zero, zero, override=[
            (1 - seat, opponent_ops),
            (seat, candidate_ops, candidate_mask),
            (seat, teacher_ops, teacher_mask),
        ])
        after = _state(ep, seat)
        new_plants = ((after["kind"] == engine_t.K_PLANT)
                      & (before["kind"] != engine_t.K_PLANT)).sum(
                          (-1, -2)).to(torch.float64)
        for policy, (indices, _) in branch.items():
            accumulator = raw[policy][phase]
            money_delta = after["money"] - before["money"]
            accumulator["cash_net"] += _take(money_delta, indices)
            accumulator["cash_positive_turns"] += _take(
                money_delta.clamp(min=0), indices)
            accumulator["cash_negative_turns"] += _take(
                (-money_delta).clamp(min=0), indices)
            accumulator["actual_land_net_additions"] += _take(
                (after["land"] - before["land"]).clamp(min=0), indices)
            accumulator["actual_animal_net_additions"] += _take(
                (after["animals_owned"]
                 - before["animals_owned"]).clamp(min=0), indices)
            accumulator["actual_hires"] += _take(
                (after["hands"] - before["hands"]).clamp(min=0), indices)
            planted = _take(new_plants, indices)
            cumulative_plants[policy] += planted
            accumulator["actual_new_plants"] += planted

        end_phase = None
        if ep._step % ep.turns_per_day == 0:
            ended_day = ep._step // ep.turns_per_day
            if ended_day in PHASE_END_DAYS:
                end_phase = PHASE_END_DAYS.index(ended_day)
        if ep.done and end_phase is None:
            end_phase = phase
        if end_phase is not None:
            for policy, (indices, _) in branch.items():
                accumulator = raw[policy][end_phase]
                for name in ("money", "opp_money", "land", "crops",
                             "herd", "animals_owned", "hands"):
                    accumulator[f"end_{name}"] = _take(after[name], indices)
                accumulator["end_margin"] = _take(
                    after["money"] - after["opp_money"], indices)
                accumulator["cumulative_plants"] = cumulative_plants[
                    policy].clone()

    return _summarize_cell(raw, lanes, seed, opponent_path, seat)


def _combine(cells):
    aggregate = {policy: {} for policy in POLICIES}
    delta = {}
    for phase in PHASE_NAMES:
        for policy in POLICIES:
            keys = set.intersection(*(
                set(cell["policies"][policy][phase]) for cell in cells))
            aggregate[policy][phase] = {}
            for key in sorted(keys):
                values = []
                for cell in cells:
                    stat = cell["policies"][policy][phase][key]
                    values.extend([stat["mean"]] * stat["n"])
                aggregate[policy][phase][key] = _summarize(values)
        keys = set.intersection(*(
            set(cell["teacher_minus_candidate"][phase]) for cell in cells))
        delta[phase] = {}
        for key in sorted(keys):
            values = []
            for cell in cells:
                stat = cell["teacher_minus_candidate"][phase][key]
                values.extend([stat["mean"]] * stat["n"])
            delta[phase][key] = _summarize(values)
    pairs = [row for cell in cells for row in cell["pairs"]]
    margin_gap = [row["teacher_minus_candidate_margin"] for row in pairs]
    return {
        "policies": aggregate,
        "teacher_minus_candidate": delta,
        "final_margin_gap": macro_audit.paired_summary(margin_gap),
        "pairs": pairs,
    }


def _m(table, key):
    return table.get(key, {}).get("mean", math.nan)


def print_report(result):
    aggregate = result["aggregate"]
    print("\nPaired route ledger (teacher - candidate; positive favors teacher)")
    print("phase       cash end C/T/delta       phase net C/T/delta   "
          "positive-turn C/T   negative-turn C/T")
    for phase in PHASE_NAMES:
        candidate = aggregate["policies"]["candidate"][phase]
        teacher = aggregate["policies"]["teacher"][phase]
        gap = aggregate["teacher_minus_candidate"][phase]
        print(
            f"{phase:<10} "
            f"{_m(candidate, 'end_money'):>8.0f}/{_m(teacher, 'end_money'):>8.0f}/"
            f"{_m(gap, 'end_money'):>+8.0f}  "
            f"{_m(candidate, 'cash_net'):>8.0f}/{_m(teacher, 'cash_net'):>8.0f}/"
            f"{_m(gap, 'cash_net'):>+8.0f}  "
            f"{_m(candidate, 'cash_positive_turns'):>8.0f}/"
            f"{_m(teacher, 'cash_positive_turns'):>8.0f}  "
            f"{_m(candidate, 'cash_negative_turns'):>8.0f}/"
            f"{_m(teacher, 'cash_negative_turns'):>8.0f}")
    print("\nphase       end land/crops/herd C -> T    "
          "orders: sell C/T  product C/T  seed C/T  animal C/T  hire C/T")
    for phase in PHASE_NAMES:
        candidate = aggregate["policies"]["candidate"][phase]
        teacher = aggregate["policies"]["teacher"][phase]
        print(
            f"{phase:<10} "
            f"{_m(candidate, 'end_land'):.1f}/{_m(candidate, 'end_crops'):.1f}/"
            f"{_m(candidate, 'end_herd'):.1f} -> "
            f"{_m(teacher, 'end_land'):.1f}/{_m(teacher, 'end_crops'):.1f}/"
            f"{_m(teacher, 'end_herd'):.1f}   "
            f"{_m(candidate, 'sell_order_units'):.0f}/"
            f"{_m(teacher, 'sell_order_units'):.0f}  "
            f"{_m(candidate, 'buy_product_order_units'):.0f}/"
            f"{_m(teacher, 'buy_product_order_units'):.0f}  "
            f"{_m(candidate, 'buy_seed_order_units'):.0f}/"
            f"{_m(teacher, 'buy_seed_order_units'):.0f}  "
            f"{_m(candidate, 'buy_animal_order_units'):.0f}/"
            f"{_m(teacher, 'buy_animal_order_units'):.0f}  "
            f"{_m(candidate, 'hire_orders'):.0f}/"
            f"{_m(teacher, 'hire_orders'):.0f}")
    gap = aggregate["final_margin_gap"]
    low = "n/a" if gap["ci95_low"] is None else f"{gap['ci95_low']:+,.0f}"
    high = "n/a" if gap["ci95_high"] is None else f"{gap['ci95_high']:+,.0f}"
    print("\nfinal teacher-candidate margin gap: "
          f"{gap['mean']:+,.0f} [{low},{high}] over {gap['n']} pairs")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="k01_route_s34")
    parser.add_argument("--teacher", default="agents/champ/k01.py")
    parser.add_argument("--reference-profile",
                        help="compare against another Barnyard profile instead of a tape")
    parser.add_argument(
        "--opponents",
        default="agents/bench3/closer_cleo.py,agents/wrapped/w49.py")
    parser.add_argument("--seats", default="0,1")
    parser.add_argument("--checkpoint", default="rl/runs/anvil/latest.pt")
    parser.add_argument("--lanes", type=int, default=8)
    parser.add_argument("--seed", type=int, default=7080825)
    parser.add_argument("--steps", type=int, default=720)
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.lanes < 1 or args.steps < 1:
        raise SystemExit("--lanes and --steps must be positive")
    torch.set_num_threads(max(1, args.threads))
    teacher = str((ROOT / args.teacher).resolve()
                  if not Path(args.teacher).is_absolute() else args.teacher)
    checkpoint = str((ROOT / args.checkpoint).resolve()
                     if not Path(args.checkpoint).is_absolute()
                     else args.checkpoint)
    opponents = [value.strip() for value in args.opponents.split(",")
                 if value.strip()]
    seats = [int(value) for value in args.seats.split(",")]
    if not opponents or any(seat not in (0, 1) for seat in seats):
        raise SystemExit("need at least one opponent and seats must be 0 or 1")
    cells = []
    for opponent_index, opponent in enumerate(opponents):
        opponent_path = str((ROOT / opponent).resolve()
                            if not Path(opponent).is_absolute() else opponent)
        for seat in seats:
            cell_seed = args.seed + opponent_index * 10_000 + seat * 1_000
            print(f"running {Path(opponent).name} seat={seat} "
                  f"seed={cell_seed} lanes={args.lanes}", flush=True)
            cells.append(run_cell(
                args.profile, teacher, opponent_path, checkpoint, args.lanes,
                cell_seed, seat, args.device, args.steps,
                args.reference_profile))
    result = {
        "schema": 1,
        "candidate": args.profile,
        "teacher": args.teacher,
        "reference_profile": args.reference_profile,
        "opponents": opponents,
        "seats": seats,
        "lanes_per_cell": args.lanes,
        "seed": args.seed,
        "steps": args.steps,
        "cells": cells,
        "aggregate": _combine(cells),
    }
    print_report(result)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
