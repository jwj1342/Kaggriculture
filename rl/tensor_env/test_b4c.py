#!/usr/bin/env python
"""B4c acceptance gate: on-device potential, tensor-starter head indices, and
the on-device training loop's learning curve (DESIGN.md Appendix B).

  (i)   potential_t.net_worth_t == obs.net_worth, EXACTLY (float64 equality),
        at every step, both players, every lane, on recorded engine_np-oracle
        action streams (verify_t's random-legal generator, plus one market
        storm) replayed through one EpisodeT batch via step_raw.
  (ii)  opponents_t.starter_indices: actions.decode of the farmer index equals
        the reference-form starter_actions farmer action lane by lane over
        full episodes played on the training path (step_idx, learner seat
        random-legal). The market head is single-choice; the documented
        approximation (SELL_CARROT before BUY_SEED_CARROT when both fire) is
        counted and reported, and every decoded market order list must equal
        the reference list whenever the reference emits at most one order.
  (iii) learning curve: train_t on --device with B=128 for as many
        iterations as fit --minutes; the win rate vs the starter must end
        above 0.5 and rise "monotone-ish" (block means non-decreasing up to
        a small tolerance). Prints the curve and end-to-end sps.

Ends B4C-PASS / B4C-FAIL.

    source setup_env.sh && python rl/tensor_env/test_b4c.py             # all
    python rl/tensor_env/test_b4c.py --skip-train                      # (i)+(ii)
    python rl/tensor_env/test_b4c.py --minutes 7 --threads 4 --lr 3e-4
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
import obs as O
import engine_t
import engine_t_idx  # noqa: F401
import features_t
import opponents_t
import potential_t
import train_t
from verify_t import _random_legal_stream, _storm_stream


def _t_obs(ept, snap, player):
    """verify_t._np_obs, from an EpisodeT lane snapshot (test_b3 pattern)."""
    return {"player": player, "step": ept._step, "day": snap["day"],
            "hour": snap["hour"], "farms": snap["farms"],
            "market": {"inventory": snap["market"]["inventory"],
                       "prices": snap["market"]["prices"]},
            "town": snap["town"], "private": snap["private"][player]}


# ---------------------------------------------------------------------------
# (i) potential gate
# ---------------------------------------------------------------------------

def gate_potential(device, steps, n_random, n_storm, seed0):
    print("== (i) net_worth_t vs obs.net_worth, exact ==", flush=True)
    lanes = []
    for i in range(n_random):
        seed = seed0 + i * 41
        rng = np.random.default_rng(seed)
        stream, trace = _random_legal_stream(seed, steps, rng)
        lanes.append((seed, stream))
        print(f"  oracle seed {seed} (random-legal): {len(stream)} steps", flush=True)
    for i in range(n_storm):
        seed = seed0 + 7_000 + i * 13
        rng = np.random.default_rng(seed)
        stream, trace = _storm_stream(seed, steps, rng)
        lanes.append((seed, stream))
        print(f"  oracle seed {seed} (market-storm): {len(stream)} steps", flush=True)

    ept = engine_t.EpisodeT([l[0] for l in lanes], episode_steps=steps, device=device)
    B = len(lanes)
    n = 0
    checked = 0
    max_assets = 0
    t_dev = t_ref = 0.0

    def check():
        nonlocal checked, max_assets, t_dev, t_ref
        t0 = time.perf_counter()
        dev = [potential_t.net_worth_t(ept, p) for p in (0, 1)]
        assets = [potential_t.assets_t(ept, p) for p in (0, 1)]
        if ept.device.type == "cuda":
            torch.cuda.synchronize()
        t_dev += time.perf_counter() - t0
        got = [d.cpu().tolist() for d in dev]
        max_assets = max(max_assets, int(torch.stack(assets).max()))
        for lane in range(B):
            snap = ept.snapshot(lane)
            for p in (0, 1):
                obsd = _t_obs(ept, snap, p)
                t0 = time.perf_counter()
                ref = O.net_worth(obsd)
                t_ref += time.perf_counter() - t0
                if got[p][lane] != ref:
                    raise AssertionError(
                        f"step {n} lane {lane} p{p}: net_worth_t {got[p][lane]!r} "
                        f"!= obs.net_worth {ref!r} (diff {got[p][lane] - ref:g})")
                checked += 1

    while not ept.done:
        check()
        ept.step_raw([lanes[k][1][n] for k in range(B)])
        n += 1
        if n % 120 == 0:
            print(f"  ... step {n}: exact so far", flush=True)
    check()
    states = n + 1
    print(f"  {states} states x {B} lanes x 2 players = {checked} comparisons, "
          f"all exactly equal (largest asset total seen {max_assets}; "
          f"device {t_dev / (states * B) * 1e6:.1f} us/lane/state vs reference "
          f"{t_ref / (states * B) * 1e6:.1f})", flush=True)


# ---------------------------------------------------------------------------
# (ii) starter_indices gate
# ---------------------------------------------------------------------------

def gate_starter_indices(device, steps, lanes, seed):
    print("== (ii) starter_indices vs starter_actions (decoded), training path ==",
          flush=True)
    ept = engine_t.EpisodeT([seed + 17 * i for i in range(lanes)],
                            episode_steps=steps, device=device)
    gen = torch.Generator(device=device).manual_seed(seed)
    B = lanes
    n = 0
    farmer_checked = 0
    market_exact = market_two = market_other = 0
    harvest_noop = 0
    hist = {}
    while not ept.done:
        ref = opponents_t.starter_actions(ept, 1)
        fa, ma = opponents_t.starter_indices(ept, 1)
        assert fa.dtype == torch.int64 and ma.dtype == torch.int64
        assert fa.shape == (B,) and ma.shape == (B,)
        fal, mal = fa.cpu().tolist(), ma.cpu().tolist()
        for lane in range(B):
            snap = ept.snapshot(lane)
            obs1 = _t_obs(ept, snap, 1)
            dec = A.decode(obs1, fal[lane], mal[lane])
            hist[A.FARMER_ACTIONS[fal[lane]]] = hist.get(A.FARMER_ACTIONS[fal[lane]], 0) + 1
            if dec["farmer"] != ref[lane]["farmer"]:
                # documented effect-identical case: raw HARVEST on a tile
                # with zero yield is an engine no-op; decode says PASS.
                fx, fy = obs1["farms"][1]["farmer"]
                tile = obs1["farms"][1]["tiles"][fy][fx]
                if (ref[lane]["farmer"] == ["HARVEST"] and dec["farmer"] == ["PASS"]
                        and isinstance(tile, dict) and tile.get("yield_units", 0) == 0):
                    harvest_noop += 1
                else:
                    raise AssertionError(
                        f"step {n} lane {lane}: decoded farmer {dec['farmer']} != "
                        f"starter {ref[lane]['farmer']} (idx {fal[lane]} "
                        f"{A.FARMER_ACTIONS[fal[lane]]}); tile {tile}")
            farmer_checked += 1
            if dec["hands"] != ref[lane]["hands"]:
                raise AssertionError(f"step {n} lane {lane}: hands {dec['hands']} != []")
            rm = ref[lane]["market"]
            if len(rm) >= 2:
                market_two += 1
                if dec["market"] != rm[:1]:
                    raise AssertionError(
                        f"step {n} lane {lane}: two-order turn, decoded "
                        f"{dec['market']} != first ref order {rm[:1]}")
            elif dec["market"] == rm:
                market_exact += 1
            else:
                market_other += 1
                raise AssertionError(
                    f"step {n} lane {lane}: decoded market {dec['market']} != "
                    f"starter {rm} (idx {mal[lane]} {A.MARKET_ACTIONS[mal[lane]]})")
        # learner seat: random-legal from masks_t (the training path's sampler)
        fm, mm = features_t.masks_t(ept, 0)
        f0 = torch.multinomial(fm.float(), 1, generator=gen).squeeze(-1)
        m0 = torch.multinomial(mm.float(), 1, generator=gen).squeeze(-1)
        ept.step_idx(torch.stack([f0, fa], 1), torch.stack([m0, ma], 1))
        n += 1
    print(f"  {n} steps x {B} lanes: farmer action identical after decode "
          f"({farmer_checked} checks; {harvest_noop} zero-yield HARVEST no-op "
          f"equivalences); market: {market_exact} single-order turns exact, "
          f"{market_two} two-order turns (documented single-choice approximation: "
          f"SELL first), {market_other} other", flush=True)
    print(f"  starter farmer index histogram: {hist}", flush=True)
    print(f"  starter final money over {B} lanes: "
          f"{[round(v) for v in ept.money[:, 1].tolist()]}", flush=True)


# ---------------------------------------------------------------------------
# (iii) learning-curve gate
# ---------------------------------------------------------------------------

def gate_learning(args):
    print(f"== (iii) learning curve: train_t B={args.B} on {args.device}, "
          f"~{args.minutes} min ==", flush=True)
    targs = train_t.build_parser().parse_args([
        "--device", args.device, "--B", str(args.B), "--iters", str(args.max_iters),
        "--max-minutes", str(args.minutes), "--threads", str(args.threads),
        "--lr", str(args.lr), "--seed", str(args.train_seed),
        "--epochs", str(args.epochs), "--minibatches", str(args.minibatches),
        "--hidden", str(args.hidden[0]), str(args.hidden[1]),
    ] + (["--log", args.log] if args.log else []))
    _, recs = train_t.train(targs, log_fn=lambda s: print("  " + s, flush=True))
    if not recs:
        raise AssertionError("no iterations completed")
    wins = [r["win"] for r in recs]
    money = [r["money"] for r in recs]
    sps = [r["sps"] for r in recs]
    print("  curve (win rate vs starter per iteration):")
    print("    " + " ".join(f"{w:.2f}" for w in wins))
    print("  learner mean money per iteration:")
    print("    " + " ".join(f"{m:,.0f}" for m in money))
    total_steps = recs[-1]["steps"]
    total_sec = sum(r["sec"] for r in recs)
    print(f"  end-to-end: {len(recs)} iterations, {total_steps:,} learner lane-steps "
          f"in {total_sec:.0f}s = {total_steps / total_sec:,.0f} lane-steps/s "
          f"(per-iteration mean {np.mean(sps):,.0f}; collection only "
          f"{np.mean([r['n_steps'] / r['t_collect'] for r in recs]):,.0f})",
          flush=True)

    # monotone-ish: means of consecutive thirds must not decrease by more
    # than `tol`, and the run must END above 0.5 (mean of the last 3 iters).
    k = len(wins)
    thirds = [np.mean(wins[i * k // 3:(i + 1) * k // 3]) for i in range(3)] if k >= 3 else [np.mean(wins)] * 3
    tol = 0.05
    end = float(np.mean(wins[-3:]))
    print(f"  block means (thirds): {[round(t, 3) for t in thirds]}; end (last-3 mean) {end:.3f}")
    if not (thirds[1] >= thirds[0] - tol and thirds[2] >= thirds[1] - tol):
        raise AssertionError(f"win-rate curve is not monotone-ish: thirds {thirds}")
    if not (thirds[2] > thirds[0]):
        raise AssertionError(f"win-rate curve did not rise: thirds {thirds}")
    if not end > 0.5:
        raise AssertionError(f"final win rate {end:.3f} <= 0.5")
    print(f"  learning curve OK: rises from {wins[0]:.2f} to {end:.2f}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--steps", type=int, default=720)
    ap.add_argument("--seed0", type=int, default=93_000)
    ap.add_argument("--random", type=int, default=2, help="(i) random-legal oracle lanes")
    ap.add_argument("--storms", type=int, default=1, help="(i) market-storm oracle lanes")
    ap.add_argument("--lanes", type=int, default=4, help="(ii) lanes")
    ap.add_argument("--skip-train", action="store_true")
    ap.add_argument("--B", type=int, default=128)
    ap.add_argument("--minutes", type=float, default=7.0)
    ap.add_argument("--max-iters", type=int, default=1000)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--minibatches", type=int, default=8)
    ap.add_argument("--hidden", type=int, nargs=2, default=[512, 256])
    ap.add_argument("--train-seed", type=int, default=0)
    ap.add_argument("--log", default="")
    args = ap.parse_args()
    if args.threads > 0:
        torch.set_num_threads(args.threads)

    gate_potential(args.device, args.steps, args.random, args.storms, args.seed0)
    gate_starter_indices(args.device, args.steps, args.lanes, args.seed0 + 500)
    if not args.skip_train:
        gate_learning(args)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("B4C-FAIL")
        sys.exit(1)
    print("B4C-PASS")
