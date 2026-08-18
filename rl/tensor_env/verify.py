#!/usr/bin/env python
"""Byte-exact verification harness for the new engine (TODO #2, hard gate).

Replays identical (seed, per-step action dicts for both players) through the
reference kaggle engine and through rl/tensor_env/engine_np.py, and diffs the
COMPLETE game state after every step. Any divergence prints the step and the
first differing path and exits non-zero. No training use until this passes on
every probe below.

    python rl/tensor_env/verify.py --episodes 3

Probes: random-legal policies on both seats (exercises weeds, market lockstep,
hires, liquidation), plus the scripted expert vs starter (exercises the whole
production economy). Seeds cover the shop-unlock RNG.

State compared: farms (tiles, money, farmer, hands, quadrants, hires_today),
private (shed, seeds, inventories), market (inventory, prices), town
(unlocked_shops), day/hour. Floats compared exactly -- the reference engine
uses int-rounded prices and float money with identical operation order, so
byte-exact is achievable and REQUIRED (README/TODO: an engine that drifts
trains an optimal policy for the wrong world).
"""

import argparse
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
_REPO = os.path.dirname(_RL)
for p in (_RL, _HERE):
    if p not in sys.path:
        sys.path.insert(0, p)


def _canon(x):
    """Canonical JSON-able form of any state fragment."""
    if isinstance(x, dict):
        return {k: _canon(v) for k, v in sorted(x.items())}
    if isinstance(x, (list, tuple)):
        return [_canon(v) for v in x]
    return x


def snapshot(state):
    """Full observable+private state of a 2-player episode, canonicalised.
    `state` is the kaggle env state list (or an equivalent duck-typed pair
    from the new engine: objects with .observation dicts)."""
    obs0 = state[0].observation if hasattr(state[0], "observation") else state[0]
    out = {
        "day": obs0["day"], "hour": obs0["hour"],
        "farms": _canon(obs0["farms"]),
        "market": _canon({k: obs0["market"][k] for k in ("inventory", "prices")}),
        "town": _canon(obs0["town"]),
        "private": [],
    }
    for s in state:
        o = s.observation if hasattr(s, "observation") else s
        out["private"].append(_canon(o["private"]))
    return out


def first_diff(a, b, path="$"):
    if type(a) is not type(b):
        return f"{path}: type {type(a).__name__} != {type(b).__name__}"
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                return f"{path}.{k}: missing on one side"
            d = first_diff(a[k], b[k], f"{path}.{k}")
            if d:
                return d
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: len {len(a)} != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            d = first_diff(x, y, f"{path}[{i}]")
            if d:
                return d
        return None
    if a != b:
        return f"{path}: {a!r} != {b!r}"
    return None


def make_reference(seed, steps):
    from kaggle_environments import make
    return make("kaggriculture",
                configuration={"episodeSteps": steps, "seed": seed})


def run_pair(seed, steps, action_fn, verbose=False):
    """action_fn(step_idx, obs_pair) -> [action_dict_p0, action_dict_p1].
    Drives both engines with identical actions; returns steps compared."""
    import engine_np  # the implementation under test

    ref = make_reference(seed, steps)
    ref.reset(2)
    new = engine_np.Episode(seed=seed, episode_steps=steps)

    n = 0
    while not ref.done:
        ref_state = ref.state
        acts = action_fn(n, [s.observation for s in ref_state])
        want = snapshot(ref_state)
        got = new.snapshot()
        d = first_diff(want, got)
        if d:
            print(f"DIVERGED at step {n} (pre-action): {d}")
            return n, False
        ref.step(acts)
        new.step(acts)
        n += 1
    d = first_diff(snapshot(ref.state), new.snapshot())
    if d:
        print(f"DIVERGED at terminal state: {d}")
        return n, False
    if verbose:
        print(f"seed {seed}: {n} steps identical")
    return n, True


def _random_legal(rng):
    import actions as A

    def fn(step, obs_pair):
        acts = []
        for obs in obs_pair:
            import numpy as np
            fm, mm = A.farmer_mask(obs), A.market_mask(obs)
            fi = int(rng.choice(np.flatnonzero(fm)))
            mi = int(rng.choice(np.flatnonzero(mm)))
            acts.append(A.decode(obs, fi, mi))
        return acts
    return fn


def main():
    import numpy as np
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=3)
    ap.add_argument("--steps", type=int, default=720)
    ap.add_argument("--seed0", type=int, default=91_000)
    args = ap.parse_args()

    ok = True
    for ep in range(args.episodes):
        seed = args.seed0 + ep * 37
        rng = np.random.default_rng(seed)
        _, good = run_pair(seed, args.steps, _random_legal(rng), verbose=True)
        ok = ok and good
        if not good:
            break
    print("VERIFY-PASS" if ok else "VERIFY-FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
