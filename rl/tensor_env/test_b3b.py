#!/usr/bin/env python
"""B3b acceptance gate: tensor-native action path (DESIGN.md §4 B3b).

Contract under test -- engine_t_idx (attaches EpisodeT.step_idx):
    ep.step_idx(f_idx, m_idx)   # (B, 2) indices into actions.FARMER_ACTIONS /
                                # MARKET_ACTIONS, per lane per player
must be byte-equivalent to step_raw fed per-lane actions.decode(...) dicts.

  G5 equivalence   TWO EpisodeT instances over the same seeds run in
                   parallel: A driven by step_idx with random LEGAL indices
                   (legality sampled from features_t.masks_t), B driven by
                   step_raw with dicts from actions.decode on the
                   snapshot-reconstructed obs using THE SAME indices. After
                   EVERY step, verify.first_diff(A.snapshot, B.snapshot)
                   must be clean for every lane. Lanes: >=2 random-policy
                   seeds, 1 market-storm-style lane (sell storms, HIRE burst
                   pressure, buy mixes) and 1 rancher lane (herd building for
                   herd-scaled BUY_WHEAT, a hoarded multi-product shed for
                   the day-29 liquidation compound sells and near-capacity
                   deposits). A scripted warm-up prologue (identical raw
                   dicts fed to BOTH instances) loads hired hands past the
                   >=8-carry threshold so the dispatcher's DROP leg is
                   exercised deterministically before the index-driven
                   comparison begins.
  G6 throughput    step_idx at B=256 / B=1024 on CPU under the realistic
                   policy-driven load (actions sampled from masks_t each
                   step), reported as lane-steps/s next to step_raw replay
                   measured on the same host (bench.py's load) and the
                   DESIGN §4.5 reference numbers.

    source setup_env.sh && python rl/tensor_env/test_b3b.py --steps 72
    source setup_env.sh && python rl/tensor_env/test_b3b.py         # full 720

Ends with B3B-PASS / B3B-FAIL.
"""

import argparse
import os
import sys
import time
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
for _p in (_HERE, _RL):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np
import torch

import actions as A
import engine_t
import engine_t_idx                      # noqa: F401  (attaches step_idx)
import features_t
from verify import first_diff


def _obs(step, snap, player):
    """verify_t._np_obs shape, from an EpisodeT lane snapshot."""
    return {"player": player, "step": step, "day": snap["day"],
            "hour": snap["hour"], "farms": snap["farms"],
            "market": {"inventory": snap["market"]["inventory"],
                       "prices": snap["market"]["prices"]},
            "town": snap["town"], "private": snap["private"][player]}


def _pick(rng, mask):
    return int(rng.choice(np.flatnonzero(mask)))


def _pick_pref(mask, prefs):
    for i in prefs:
        if mask[i]:
            return int(i)
    return None


def _storm_indices(rng, t, fm, mm):
    """Market-storm-style sampling, all mask-legal (verify_t._storm_stream's
    idea expressed as head indices): build days grow a dense farm with a
    hired crew (loaded hands -> the >=8-carry DROP leg), sell days dump the
    shed and buy herd wheat, mix days buy animals/land (herd-scaled
    BUY_WHEAT), days 27-28 hoard so day 29 exercises the liquidation
    compound sell."""
    day = t // 24
    f = _pick_pref(fm, [6, 5, 15, 7] + list(range(20, 23)))  # HARVEST WATER
    if f is None or rng.random() < 0.2:                      # PLANT_WHEAT FEED
        f = _pick(rng, fm)                                   # PLACE_*
    sells = [1 + (t + k) % 9 for k in range(9)]              # SELL_* rotation
    if day >= 29:
        prefs = sells                                        # liquidation
    elif day >= 26:
        # hoard: BUY_WHEAT storms a season of sell income into the shed --
        # capacity-limited deposits, then a full-shed day-29 liquidation.
        # NOOP tail: never fall through to a sell.
        prefs = [15, 16, 17, 18, 21, 10, 0]
    else:
        phase = day % 3
        if phase == 0:                                       # build
            prefs = [10, 21, 11, 21] if t % 2 else [21, 10, 10, 11]
        elif phase == 1:                                     # sell storm
            prefs = sells + [15]
        else:                                                # buy mix
            prefs = [17, 18, 15, 21, 16, 20, 14] + sells
    m = _pick_pref(mm, prefs)
    if m is None:
        m = _pick(rng, mm)
    return f, m


def _rancher_indices(rng, t, fm, mm):
    """Herd lane: feed/place/care first, buy animals and herd wheat, never
    sell before day 29 (NOOP tail keeps the shed multi-product), then
    liquidate. Sustained herd -> BUY_WHEAT decodes with 2*herd > 5."""
    day = t // 24
    f = _pick_pref(fm, [7, 20, 21, 22, 9, 8, 6, 5, 15])      # FEED PLACE_*
    if f is None or rng.random() < 0.15:                     # COLLECT CARE
        f = _pick(rng, fm)
    if day >= 29:
        prefs = [1 + (t + k) % 9 for k in range(9)]          # liquidation
    else:
        prefs = [17, 18, 19, 15, 10, 21, 0]                  # animals, wheat
    m = _pick_pref(mm, prefs)
    if m is None:
        m = _pick(rng, mm)
    return f, m


# One scripted warm-up step per prologue entry, fed VERBATIM to both
# instances via step_raw (states stay equal by construction): buy wheat and
# fertilizer, hire two hands, load them past the >=8-carry threshold with
# mixed-item pickups (insertion order FERTILIZER-then-WHEAT on hand 1), walk
# them off the shed tiles. The index-driven steps that follow must then take
# the dispatcher's DROP leg: walk back to the shed and DROP.
_PROLOGUE = [
    {"farmer": ["PASS"], "hands": [],
     "market": [["BUY_PRODUCT", "WHEAT", 40], ["BUY_PRODUCT", "FERTILIZER", 6]]},
    {"farmer": ["PASS"], "hands": [], "market": [["HIRE"], ["HIRE"]]},
    {"farmer": ["PASS"], "hands": [["PICKUP", "WHEAT", 12],
                                   ["PICKUP", "FERTILIZER", 5]], "market": []},
    {"farmer": ["PASS"], "hands": [["EAST"], ["PICKUP", "WHEAT", 4]],
     "market": []},
    {"farmer": ["PASS"], "hands": [["EAST"], ["SOUTH"]], "market": []},
    {"farmer": ["PASS"], "hands": [["NORTH"], ["SOUTH"]], "market": []},
]

# Capacity scenario (run with shed_capacity=40 on BOTH instances -- buys
# clamp at capacity, which pins the shed at exact values regardless of price
# drift; masks keep using R.SHED_CAPACITY=100, which only makes them more
# permissive, and both engines see the same capacity).
# Lane A: shed 39, hand 0 carries 9 WHEAT (>= 8): the dispatcher's DROP leg
#   walks it back and deposits into room 1 -- in-step partial truncation.
# Lane B: shed 39, hand 0 idles (carry 6 < 8, no chores on day 0) holding
#   FERTILIZER-then-WHEAT (1+5): the END-OF-DAY drop finds room for exactly
#   one unit, so dict insertion order decides that the FERTILIZER lands and
#   the 5 WHEAT are discarded.
_CAP_PROLOGUES = [
    [   # lane A
        {"farmer": ["PASS"], "hands": [],
         "market": [["BUY_PRODUCT", "FERTILIZER", 1], ["BUY_PRODUCT", "WHEAT", 45]]},
        {"farmer": ["PASS"], "hands": [], "market": [["HIRE"], ["HIRE"]]},
        {"farmer": ["PASS"],
         "hands": [["PICKUP", "WHEAT", 9], ["PICKUP", "WHEAT", 1]], "market": []},
        {"farmer": ["PASS"], "hands": [["EAST"], ["PASS"]],
         "market": [["BUY_PRODUCT", "WHEAT", 9]]},
        {"farmer": ["PASS"], "hands": [["EAST"], ["PASS"]], "market": []},
        {"farmer": ["PASS"], "hands": [["NORTH"], ["PASS"]], "market": []},
    ],
    [   # lane B
        {"farmer": ["PASS"], "hands": [],
         "market": [["BUY_PRODUCT", "FERTILIZER", 1], ["BUY_PRODUCT", "WHEAT", 45]]},
        {"farmer": ["PASS"], "hands": [], "market": [["HIRE"]]},
        {"farmer": ["PASS"], "hands": [["PICKUP", "FERTILIZER", 1]], "market": []},
        {"farmer": ["PASS"], "hands": [["PICKUP", "WHEAT", 5]], "market": []},
        {"farmer": ["PASS"], "hands": [["PASS"]],
         "market": [["BUY_PRODUCT", "WHEAT", 5]]},
        {"farmer": ["PASS"], "hands": [["PASS"]], "market": []},
    ],
]


def _cap_indices(rng, t, fm, mm):
    """Capacity lanes: random-legal farmer, market NOOP through day 0 so the
    shed stays pinned at capacity for the end-of-day truncation, then
    random-legal."""
    return _pick(rng, fm), (0 if t < 24 else _pick(rng, mm))


_POLICIES = {"storm": _storm_indices, "ranch": _rancher_indices,
             "cap": _cap_indices}


def gate_g5(steps, seeds, kinds, device, prologue=None, label="G5",
            shed_capacity=100):
    B = len(seeds)
    a = engine_t.EpisodeT(seeds, episode_steps=steps, device=device,
                          shed_capacity=shed_capacity)
    b = engine_t.EpisodeT(seeds, episode_steps=steps, device=device,
                          shed_capacity=shed_capacity)
    rngs = [np.random.default_rng(1_000 + s) for s in seeds]
    if prologue and isinstance(prologue[0], dict):
        prologue = [prologue] * B                # same script for every lane
    print(f"  {label} lanes: {B} {kinds}, seeds {seeds}"
          + (f", {len(prologue[0])} scripted warm-up steps" if prologue else "")
          + (f", shed_capacity={shed_capacity}" if shed_capacity != 100 else ""),
          flush=True)

    n = 0
    for i in range(len(prologue[0]) if prologue else 0):
        acts = [[prologue[lane][i], prologue[lane][i]] for lane in range(B)]
        a.step_raw(acts)
        b.step_raw(acts)
        n += 1

    snaps_b = [b.snapshot(lane) for lane in range(B)]
    while not a.done:
        masks = []
        for p in (0, 1):
            fm, mm = features_t.masks_t(a, p)
            masks.append((fm.cpu().numpy(), mm.cpu().numpy()))
        f_idx = np.zeros((B, 2), dtype=np.int64)
        m_idx = np.zeros((B, 2), dtype=np.int64)
        for lane in range(B):
            pol = _POLICIES.get(kinds[lane])
            for p in (0, 1):
                fm, mm = masks[p][0][lane], masks[p][1][lane]
                if pol is not None:
                    f_idx[lane, p], m_idx[lane, p] = pol(rngs[lane], n, fm, mm)
                else:
                    f_idx[lane, p] = _pick(rngs[lane], fm)
                    m_idx[lane, p] = _pick(rngs[lane], mm)

        acts = []
        for lane in range(B):
            pair = []
            for p in (0, 1):
                obs = _obs(b._step, snaps_b[lane], p)
                pair.append(A.decode(obs, int(f_idx[lane, p]),
                                     int(m_idx[lane, p])))
            acts.append(pair)

        a.step_idx(torch.as_tensor(f_idx), torch.as_tensor(m_idx))
        b.step_raw(acts)
        n += 1

        snaps_b = []
        for lane in range(B):
            sb = b.snapshot(lane)
            d = first_diff(sb, a.snapshot(lane))
            if d:
                raise AssertionError(
                    f"{label} DIVERGED step {n} lane {lane} "
                    f"(seed {seeds[lane]}, {kinds[lane]}): {d}")
            snaps_b.append(sb)
        if n % 120 == 0:
            print(f"  ... step {n}: every lane byte-exact so far", flush=True)
    print(f"  {label}: {n} steps x {B} lanes, snapshot-exact after every "
          f"index-driven step", flush=True)
    return n


def bench_step_idx(B, steps, device):
    ep = engine_t.EpisodeT(list(range(81_000, 81_000 + B)),
                           episode_steps=steps + 2, device=device)
    g = torch.Generator().manual_seed(4242)
    t_mask = t_step = 0.0
    t0 = time.perf_counter()
    for _ in range(steps):
        tm = time.perf_counter()
        fs, ms = [], []
        for p in (0, 1):
            fm, mm = features_t.masks_t(ep, p)
            fs.append(torch.multinomial(fm.double().cpu(), 1, generator=g)
                      .squeeze(-1))
            ms.append(torch.multinomial(mm.double().cpu(), 1, generator=g)
                      .squeeze(-1))
        f_idx = torch.stack(fs, 1)
        m_idx = torch.stack(ms, 1)
        t1 = time.perf_counter()
        t_mask += t1 - tm
        ep.step_idx(f_idx, m_idx)
        t_step += time.perf_counter() - t1
    wall = time.perf_counter() - t0
    return (steps * B / wall,                       # lane-steps/s, full loop
            steps * B / t_step,                     # lane-steps/s, step only
            t_mask / (steps * B) * 1e6,             # us/lane-step masks+sample
            t_step / (steps * B) * 1e6)             # us/lane-step step_idx


def gate_g6(device, bench_steps):
    import bench
    print(f"  torch {torch.__version__}, threads={torch.get_num_threads()}, "
          f"device={device}", flush=True)
    print("  recording replay stream (engine_np random-legal, for the "
          "step_raw baseline)...", flush=True)
    stream = bench.record_stream(bench_steps)
    for B in (256, 1024):
        total, step_only, us_mask, us_step = bench_step_idx(B, bench_steps, device)
        raw = bench.bench_t(bench_steps, "replay", stream, B, device)
        print(f"  B={B:>5}: step_idx {total:>9,.0f} lane-steps/s "
              f"(step_idx alone {step_only:,.0f}; per lane-step: "
              f"masks+sample {us_mask:.1f} us, step_idx {us_step:.1f} us)",
              flush=True)
        print(f"           step_raw replay same host: {raw:>9,.0f} lane-steps/s"
              f"  -> step_idx/step_raw = {step_only / raw:.1f}x", flush=True)
    print("  DESIGN §4.5 reference (2xL40S job, 2026-08-16): engine_t CPU "
          "B=1024 replay 11.5k lane-steps/s; GPU replay 4.5k", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--steps", type=int, default=720)
    ap.add_argument("--seeds", type=int, default=3,
                    help="random-policy lanes (>=2 per the gate)")
    ap.add_argument("--seed0", type=int, default=95_000)
    ap.add_argument("--bench-steps", type=int, default=240)
    ap.add_argument("--skip-bench", action="store_true",
                    help="G5 only (fast iteration)")
    args = ap.parse_args()

    seeds = ([args.seed0 + i * 41 for i in range(args.seeds)]
             + [args.seed0 + 6_000, args.seed0 + 7_000])
    kinds = ["rand"] * args.seeds + ["ranch", "storm"]
    assert len(seeds) >= 3

    print("== G5: step_idx vs decode+step_raw, per-step snapshot equality ==",
          flush=True)
    gate_g5(args.steps, seeds, kinds, args.device, prologue=_PROLOGUE)
    # Capacity-truncation scenario: order-dependent deposits at a full shed.
    gate_g5(min(args.steps, 60), [args.seed0 + 8_000, args.seed0 + 8_001],
            ["cap", "cap"], args.device, prologue=_CAP_PROLOGUES,
            label="G5cap", shed_capacity=40)

    if not args.skip_bench:
        print("== G6: step_idx throughput under masks_t-sampled load ==",
              flush=True)
        gate_g6(args.device, args.bench_steps)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("B3B-FAIL")
        sys.exit(1)
    print("B3B-PASS")
