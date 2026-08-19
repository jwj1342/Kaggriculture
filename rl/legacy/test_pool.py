#!/usr/bin/env python
"""Smoke gate for rl/episode_pool.py: 4 autonomous workers vs "starter".

Two publish/collect rounds of >= 2000 steps each with a fresh Policy, then:
  - every episode is complete (719 steps -- episodeSteps 720 means the agent
    acts 719 times) with the declared shapes/dtypes,
  - rewards and obs are finite (obs travel float16: overflow would show here),
  - logp of the sampled pair is in [-20, 0] and the sampled actions are legal
    under the shipped masks,
  - the shaped-return ledger balances on a manually replayed episode: with
    shape_w=1 the per-step rewards telescope, so
    sum(rew) == (final_net_worth - 3000)/3000 + win_bonus_term, and each
    step's reward is recomputed independently from the replay,
  - generations on collected episodes never lag the published gen by > 1.

Prints steps/s and ends POOL-PASS / POOL-FAIL.

    source setup_env.sh && python rl/tensor_env/test_pool.py

Login-node budget: 4 worker processes, ~1-2 minutes, no torch in the workers.
"""

import os
import shutil
import sys
import tempfile
import time
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
for _p in (_HERE, _RL):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import numpy as np

N_WORKERS = 4
MIN_STEPS = 2000
ITERS = 2
EP_LEN = 719
WIN_BONUS = 3.0


def check_episode(ep, obs_dim, n_farmer, n_market, cur_gen):
    L = int(ep["rew"].shape[0])
    assert L == EP_LEN, f"episode has {L} steps, expected {EP_LEN}"
    assert ep["obs"].shape == (L, obs_dim) and ep["obs"].dtype == np.float16
    assert ep["fmask"].shape == (L, n_farmer) and ep["fmask"].dtype == np.bool_
    assert ep["mmask"].shape == (L, n_market) and ep["mmask"].dtype == np.bool_
    assert ep["fa"].shape == (L,) and ep["fa"].dtype == np.int16
    assert ep["ma"].shape == (L,) and ep["ma"].dtype == np.int16
    assert ep["logp"].shape == (L,) and ep["logp"].dtype == np.float32
    assert ep["rew"].shape == (L,) and ep["rew"].dtype == np.float32
    assert ep["fp"].shape == (n_farmer + n_market,) and ep["fp"].dtype == np.float32

    assert np.isfinite(ep["rew"]).all(), "non-finite reward"
    assert np.isfinite(ep["obs"].astype(np.float32)).all(), \
        "non-finite obs after the float16 round trip"
    assert (ep["logp"] <= 0.0).all() and (ep["logp"] >= -20.0).all(), \
        f"logp outside [-20, 0]: [{ep['logp'].min()}, {ep['logp'].max()}]"

    rows = np.arange(L)
    assert ep["fmask"][rows, ep["fa"].astype(np.int64)].all(), \
        "sampled farmer action illegal under its own mask"
    assert ep["mmask"][rows, ep["ma"].astype(np.int64)].all(), \
        "sampled market action illegal under its own mask"
    assert ep["win"] in (0.0, 0.5, 1.0)
    assert ep["seat"] in (0, 1)
    assert ep["opponent"] == "starter"
    assert cur_gen - 1 <= ep["gen"] <= cur_gen, \
        f"gen {ep['gen']} outside [{cur_gen - 1}, {cur_gen}]"
    return L


def check_ledger(ep, A, O, KGEnvNP):
    """Replay the recorded actions on the recorded seed/seat and rebuild the
    reward stream independently (float64), then check the telescoped identity
    the worker's per-step deltas must satisfy."""
    env = KGEnvNP(opponent="starter", seat=int(ep["seat"]))
    raw = env.reset(seed=int(ep["seed"]))
    prev = O.net_worth(raw)
    assert abs(prev - 3000.0) < 1e-9, f"opening net worth {prev} != 3000"
    L = int(ep["rew"].shape[0])
    recomputed = np.empty(L, dtype=np.float64)
    done = False
    for t in range(L):
        raw, done = env.step(A.decode(raw, int(ep["fa"][t]), int(ep["ma"][t])))
        worth = O.net_worth(raw)
        recomputed[t] = (worth - prev) / 3000.0        # shape_w == 1
        prev = worth
    assert done, "replay did not finish in the recorded number of steps"
    final_nw = prev
    mine, theirs = env.final_money()
    assert abs(mine - ep["money"]) < 1e-6 and abs(theirs - ep["opp_money"]) < 1e-6, \
        (f"replayed final money ({mine}, {theirs}) != recorded "
         f"({ep['money']}, {ep['opp_money']}) -- nondeterministic replay?")
    win = 1.0 if mine > theirs else 0.0 if mine < theirs else 0.5
    assert win == ep["win"], f"replayed win {win} != recorded {ep['win']}"
    win_term = WIN_BONUS * (1.0 if win == 1.0 else -1.0 if win == 0.0 else 0.0)
    recomputed[L - 1] += win_term

    step_err = float(np.max(np.abs(recomputed - ep["rew"].astype(np.float64))))
    assert step_err < 1e-4, f"per-step reward mismatch, max |diff| {step_err}"

    ledger = float(ep["rew"].astype(np.float64).sum())
    expect = (final_nw - 3000.0) / 3000.0 + win_term
    assert abs(ledger - expect) < 1e-2, \
        f"ledger off: sum(rew) {ledger} vs (final_nw-3000)/3000 + win {expect}"
    return ledger, expect, step_err


def main():
    import torch
    from policy import Policy
    import actions as A
    import obs as O
    from adapter import KGEnvNP
    from episode_pool import EpisodePool

    torch.manual_seed(0)
    torch.set_num_threads(1)
    policy = Policy(O.OBS_DIM, A.N_FARMER, A.N_MARKET)

    weights_dir = tempfile.mkdtemp(prefix="kg-pool-gate-")
    pool = EpisodePool(N_WORKERS, [("starter", 1.0)], shape_w=1.0,
                       win_bonus=WIN_BONUS, opp_lambda=0.0,
                       seed_range=(0, 10_000), base_rng_seed=0,
                       weights_dir=weights_dir)
    try:
        all_eps, total_steps = [], 0
        iter_sps = []
        t0 = time.time()
        for it in range(ITERS):
            t_it = time.time()
            pool.publish(policy.state_np(), gen=it)
            eps = pool.collect(MIN_STEPS)
            got = 0
            for ep in eps:
                got += check_episode(ep, O.OBS_DIM, A.N_FARMER, A.N_MARKET, it)
            assert got >= MIN_STEPS
            iter_sps.append(got / (time.time() - t_it))
            print(f"iter {it}: {len(eps)} episodes, {got} steps, "
                  f"gens {sorted({e['gen'] for e in eps})}, "
                  f"dropped so far {pool.dropped}", flush=True)
            all_eps.extend(eps)
            total_steps += got
        dt = time.time() - t0

        ledger, expect, step_err = check_ledger(all_eps[0], A, O, KGEnvNP)
        print(f"ledger: sum(rew) {ledger:+.6f}  recomputed {expect:+.6f}  "
              f"max per-step |diff| {step_err:.2e}", flush=True)

        seats = {e["seat"] for e in all_eps}
        assert seats == {0, 1}, f"seat alternation broken: only seats {seats}"

        sps = total_steps / dt
        print(f"steps/s: {sps:,.0f} overall ({total_steps} steps in {dt:.1f}s, "
              f"{N_WORKERS} workers; per-iter "
              f"{', '.join(f'{s:,.0f}' for s in iter_sps)} -- iter 0 pays "
              f"worker start-up)", flush=True)
        print("POOL-PASS")
        return 0
    except Exception:
        traceback.print_exc()
        print("POOL-FAIL")
        return 1
    finally:
        pool.close()
        shutil.rmtree(weights_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
