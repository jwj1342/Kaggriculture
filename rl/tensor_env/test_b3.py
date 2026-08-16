#!/usr/bin/env python
"""B3 (first half) acceptance gate: device featurization + masks (DESIGN.md D5).

Contract under test -- features_t:
    encode_t(ep, player) -> (B, 4867) float32 on ep.device
    masks_t(ep, player)  -> ((B, 23) bool, (B, 22) bool) on ep.device

Recorded engine_np-oracle action streams (verify_t's generators: >=2
random-legal episodes plus >=1 market-storm episode) drive ONE EpisodeT
batch via step_raw. At EVERY step, for both players, for every lane, the
dict obs is rebuilt from ept.snapshot(lane) (verify_t's _np_obs shape) and
the CPU reference obs.encode / actions.farmer_mask / actions.market_mask is
compared against the device result pulled to host: np.array_equal on the
float32 encode vectors, boolean equality on the masks. Terminal states get
the same check, plus a first_diff of each lane's snapshot against the
oracle trace (wiring sanity only -- the state gate proper is verify_t.py).

Ends with B3-PASS / B3-FAIL and timing lines (device featurization
us/lane/step vs the CPU reference path, plus a synthetic B=256 probe).

    source setup_env.sh && python rl/tensor_env/test_b3.py --steps 120
    source setup_env.sh && python rl/tensor_env/test_b3.py            # full
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
import features_t
from verify import first_diff
from verify_t import _random_legal_stream, _storm_stream


def _t_obs(ept, snap, player):
    """verify_t._np_obs, but from an EpisodeT lane snapshot."""
    return {"player": player, "step": ept._step, "day": snap["day"],
            "hour": snap["hour"], "farms": snap["farms"],
            "market": {"inventory": snap["market"]["inventory"],
                       "prices": snap["market"]["prices"]},
            "town": snap["town"], "private": snap["private"][player]}


def _check_step(ept, n, t_acc):
    """Device encode/masks for both players vs CPU reference, every lane.
    Returns the lane snapshots (reused for the terminal trace check)."""
    B = ept.B
    cuda = ept.device.type == "cuda"

    t0 = time.perf_counter()
    dev = []
    for p in (0, 1):
        enc = features_t.encode_t(ept, p)
        fm, mm = features_t.masks_t(ept, p)
        dev.append((enc, fm, mm))
    if cuda:
        torch.cuda.synchronize()
    t_acc["dev"] += time.perf_counter() - t0

    if n == 0:
        for enc, fm, mm in dev:
            assert enc.dtype == torch.float32 and enc.shape == (B, O.OBS_DIM), \
                f"encode_t {enc.dtype} {tuple(enc.shape)}"
            assert fm.dtype == torch.bool and fm.shape == (B, A.N_FARMER)
            assert mm.dtype == torch.bool and mm.shape == (B, A.N_MARKET)
            _dev = __import__("torch").empty(0, device=ept.device).device
    assert enc.device == fm.device == mm.device == _dev
    host = [(enc.cpu().numpy(), fm.cpu().numpy(), mm.cpu().numpy())
            for enc, fm, mm in dev]

    snaps = [ept.snapshot(lane) for lane in range(B)]
    for lane in range(B):
        for p in (0, 1):
            obsd = _t_obs(ept, snaps[lane], p)
            t0 = time.perf_counter()
            ref_enc = O.encode(obsd)
            ref_fm = A.farmer_mask(obsd)
            ref_mm = A.market_mask(obsd)
            t_acc["ref"] += time.perf_counter() - t0
            enc, fm, mm = host[p]
            if not np.array_equal(enc[lane], ref_enc):
                bad = np.flatnonzero(enc[lane] != ref_enc)[:8]
                raise AssertionError(
                    f"step {n} lane {lane} p{p}: encode mismatch at {bad}: "
                    f"dev {enc[lane][bad]} ref {ref_enc[bad]}")
            if not np.array_equal(fm[lane], ref_fm):
                raise AssertionError(
                    f"step {n} lane {lane} p{p}: farmer_mask "
                    f"dev {fm[lane].astype(int).tolist()} "
                    f"ref {ref_fm.astype(int).tolist()}")
            if not np.array_equal(mm[lane], ref_mm):
                raise AssertionError(
                    f"step {n} lane {lane} p{p}: market_mask "
                    f"dev {mm[lane].astype(int).tolist()} "
                    f"ref {ref_mm.astype(int).tolist()}")
    return snaps


def _probe(device, B=256, iters=50):
    """Synthetic device-throughput probe on initial state (op count barely
    depends on state content; this isolates featurization from stepping)."""
    ept = engine_t.EpisodeT(list(range(B)), episode_steps=720, device=device)
    cuda = ept.device.type == "cuda"
    for p in (0, 1):                     # warm up caches / allocator
        features_t.encode_t(ept, p)
        features_t.masks_t(ept, p)
    if cuda:
        torch.cuda.synchronize()
    t0 = time.perf_counter()
    for _ in range(iters):
        for p in (0, 1):
            features_t.encode_t(ept, p)
            features_t.masks_t(ept, p)
    if cuda:
        torch.cuda.synchronize()
    return (time.perf_counter() - t0) / (iters * B) * 1e6


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--steps", type=int, default=720)
    ap.add_argument("--seeds", type=int, default=2, help="random-legal episodes")
    ap.add_argument("--storms", type=int, default=1, help="market-storm episodes")
    ap.add_argument("--seed0", type=int, default=93_000)
    args = ap.parse_args()

    print("== B3 gate: device featurization + masks vs CPU reference ==",
          flush=True)
    lanes = []                           # (seed, stream, trace)
    for i in range(args.seeds):
        seed = args.seed0 + i * 41
        rng = np.random.default_rng(seed)
        stream, trace = _random_legal_stream(seed, args.steps, rng)
        lanes.append((seed, stream, trace))
        print(f"  oracle seed {seed} (random-legal): {len(stream)} steps",
              flush=True)
    for i in range(args.storms):
        seed = args.seed0 + 7_000 + i * 13
        rng = np.random.default_rng(seed)
        stream, trace = _storm_stream(seed, args.steps, rng)
        lanes.append((seed, stream, trace))
        print(f"  oracle seed {seed} (market-storm): {len(stream)} steps",
              flush=True)

    ept = engine_t.EpisodeT([l[0] for l in lanes], episode_steps=args.steps,
                            device=args.device)
    t_acc = {"dev": 0.0, "ref": 0.0}
    n = 0
    while not ept.done:
        _check_step(ept, n, t_acc)
        ept.step_raw([lanes[k][1][n] for k in range(len(lanes))])
        n += 1
        if n % 120 == 0:
            print(f"  ... step {n}: every lane/player exact so far", flush=True)
    snaps = _check_step(ept, n, t_acc)   # terminal state
    for k in range(len(lanes)):
        d = first_diff(lanes[k][2][n], snaps[k])
        if d:
            raise AssertionError(
                f"lane {k} terminal snapshot diverged from oracle trace: {d}")

    B = len(lanes)
    states = n + 1
    per_dev = t_acc["dev"] / (states * B) * 1e6
    per_ref = t_acc["ref"] / (states * B) * 1e6
    print(f"  {states} states x {B} lanes x 2 players: encode + both masks "
          f"exact everywhere", flush=True)
    print(f"timing: device featurization {per_dev:.1f} us/lane/step vs CPU "
          f"reference {per_ref:.1f} us/lane/step (B={B}, both perspectives "
          f"per step, device={args.device})", flush=True)
    per_probe = _probe(args.device)
    print(f"timing: synthetic probe B=256: {per_probe:.2f} us/lane/step "
          f"(device={args.device})", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        print("B3-FAIL")
        sys.exit(1)
    print("B3-PASS")
