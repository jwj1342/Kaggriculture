#!/usr/bin/env python
"""B1/B1.5/B2 acceptance gates for the batched tensor engine (DESIGN.md §4).

Contract under test -- engine_t.EpisodeT:
    EpisodeT(seeds: list[int], episode_steps=720, device="cpu")
    .step_raw(actions)   # actions[lane] = [p0_action_dict, p1_action_dict]
    .snapshot(lane)      # dict, same structure as engine_np.Episode.snapshot()
    .done                # bool, whole batch (fixed length -> lanes agree)

Gates (all comparisons are exact, via verify.first_diff):

  G1 byte-exact   B=1 lanes vs engine_np, full 720-step episodes, random-legal
                  actions for both players (generated from engine_np's state so
                  both engines consume identical action streams).
  G2 batch-consistency
                  the SAME recorded action streams replayed in one B=K batch;
                  every lane must match its own B=1 engine_np trajectory at
                  every comparison point (batching must not change any lane).
  G3 market-storm (B1.5) adversarial per-unit-lockstep coverage: sell storms,
                  same-item duels, atomic HIRE/BUY_LAND ordering, liquidation
                  cascades -- the serial market loop is where batching is most
                  likely to diverge.

    python rl/tensor_env/verify_t.py           # all gates, CPU
    python rl/tensor_env/verify_t.py --device cuda   # B2: same gates on GPU

Every gate compares full snapshots every --stride steps and at the terminal
state. Any diff prints lane/step/path and the run fails.
"""

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
for p in (_HERE, _RL):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np

import engine_np
from verify import first_diff


def _np_obs(ep, player):
    snap = ep.snapshot()
    return {"player": player, "step": ep._step, "day": snap["day"],
            "hour": snap["hour"], "farms": snap["farms"],
            "market": {"inventory": snap["market"]["inventory"],
                       "prices": snap["market"]["prices"]},
            "town": snap["town"], "private": snap["private"][player]}


class SnapView:
    """Duck-types _np_obs onto one EpisodeT lane -- the shared bridge every
    opponent/action gate uses to feed reference agents real obs dicts."""

    def __init__(self, ep, lane):
        self.ep, self.lane = ep, lane
        self._step = ep._step

    def snapshot(self):
        return self.ep.snapshot(self.lane)


def lane_obs(ep, lane, player):
    """Official-format obs dict for one EpisodeT lane and seat."""
    return _np_obs(SnapView(ep, lane), player)


def _random_legal_stream(seed, steps, rng):
    """Play engine_np with random-legal actions for both players; return the
    recorded action stream and the snapshot trace (oracle)."""
    import actions as A
    ep = engine_np.Episode(seed=seed, episode_steps=steps)
    stream, trace = [], []
    while not ep.done:
        pair = []
        for p in (0, 1):
            obs = _np_obs(ep, p)
            fm, mm = A.farmer_mask(obs), A.market_mask(obs)
            fi = int(rng.choice(np.flatnonzero(fm)))
            mi = int(rng.choice(np.flatnonzero(mm)))
            pair.append(A.decode(obs, fi, mi))
        trace.append(ep.snapshot())
        ep.step(pair)
        stream.append(pair)
    trace.append(ep.snapshot())
    return stream, trace


def _storm_stream(seed, steps, rng):
    """Adversarial market generator: both players fire dense market combos.
    Farm side keeps a simple plant/water loop so there is inventory to fight
    over; market side cycles sell-storms, same-item duels, hire/land atomics."""
    import actions as A
    ep = engine_np.Episode(seed=seed, episode_steps=steps)
    stream, trace = [], []
    t = 0
    while not ep.done:
        pair = []
        for p in (0, 1):
            obs = _np_obs(ep, p)
            fm, mm = A.farmer_mask(obs), A.market_mask(obs)
            legal_f = np.flatnonzero(fm)
            fi = int(rng.choice(legal_f))
            act = A.decode(obs, fi, 0)
            shed = obs["private"]["shed"]
            money = obs["farms"][p]["money"]
            phase = (t // 8) % 4
            if phase == 0:      # same-item duel + storm: everyone dumps wheat/eggs
                orders = [["SELL", it, max(1, shed.get(it, 0))]
                          for it in ("WHEAT", "EGG", "CARROT") if shed.get(it, 0) > 0]
                orders += [["BUY_SEED", "WHEAT", 1]] * 3
            elif phase == 1:    # atomic ordering stress
                orders = [["HIRE"], ["BUY_LAND"], ["HIRE"],
                          ["BUY_PRODUCT", "WHEAT", 3], ["HIRE"]]
            elif phase == 2:    # liquidation cascade
                orders = [["SELL", it, shed[it]] for it in list(shed)
                          if shed.get(it, 0) > 0][:10]
            else:               # mixed buys incl. unaffordable tails
                orders = [["BUY_ANIMAL", "GOOSE", 1], ["BUY_SEED", "MELON", 2],
                          ["BUY_PRODUCT", "FERTILIZER", 2], ["BUY_LAND"],
                          ["SELL", "WHEAT", 999]]
            if money < 60 and shed:
                orders = [["SELL", it, shed[it]] for it in list(shed)
                          if shed.get(it, 0) > 0][:10]
            act["market"] = orders[:10]
            pair.append(act)
        trace.append(ep.snapshot())
        ep.step(pair)
        stream.append(pair)
        t += 1
    trace.append(ep.snapshot())
    return stream, trace


def _replay_batch(streams, traces, steps, device, stride, label):
    """Feed recorded streams into one EpisodeT batch; diff every stride."""
    import engine_t
    ept = engine_t.EpisodeT([s for s, _ in streams], episode_steps=steps,
                            device=device)
    n = 0
    ok = True
    while not ept.done:
        for lane in range(len(streams)):
            if n % stride == 0:
                d = first_diff(traces[lane][n], ept.snapshot(lane))
                if d:
                    print(f"{label}: DIVERGED lane {lane} step {n}: {d}")
                    ok = False
        if not ok:
            return False
        ept.step_raw([streams[lane][1][n] for lane in range(len(streams))])
        n += 1
    for lane in range(len(streams)):
        d = first_diff(traces[lane][n], ept.snapshot(lane))
        if d:
            print(f"{label}: DIVERGED lane {lane} terminal: {d}")
            ok = False
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--steps", type=int, default=720)
    ap.add_argument("--seeds", type=int, default=4, help="episodes per gate")
    ap.add_argument("--seed0", type=int, default=92_000)
    ap.add_argument("--stride", type=int, default=24)
    args = ap.parse_args()

    ok = True

    print("== G1/G2: random-legal, byte-exact + batch-consistency ==", flush=True)
    streams = []
    traces = []
    for i in range(args.seeds):
        seed = args.seed0 + i * 41
        rng = np.random.default_rng(seed)
        stream, trace = _random_legal_stream(seed, args.steps, rng)
        streams.append((seed, stream))
        traces.append(trace)
        print(f"  oracle seed {seed}: {len(stream)} steps recorded", flush=True)
    # G1: each lane alone (B=1)
    for i in range(args.seeds):
        ok &= _replay_batch([streams[i]], [traces[i]], args.steps,
                            args.device, args.stride, f"G1 seed{streams[i][0]}")
    print(f"  G1 {'pass' if ok else 'FAIL'}", flush=True)
    # G2: all lanes in one batch
    if ok:
        ok &= _replay_batch(streams, traces, args.steps, args.device,
                            args.stride, "G2")
        print(f"  G2 {'pass' if ok else 'FAIL'}", flush=True)

    if ok:
        print("== G3: market storm (B1.5) ==", flush=True)
        sstreams, straces = [], []
        for i in range(max(2, args.seeds // 2)):
            seed = args.seed0 + 7_000 + i * 13
            rng = np.random.default_rng(seed)
            stream, trace = _storm_stream(seed, args.steps, rng)
            sstreams.append((seed, stream))
            straces.append(trace)
            print(f"  storm seed {seed} recorded", flush=True)
        ok &= _replay_batch(sstreams, straces, args.steps, args.device,
                            args.stride, "G3")
        print(f"  G3 {'pass' if ok else 'FAIL'}", flush=True)

    print("VERIFY-T-PASS" if ok else "VERIFY-T-FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
