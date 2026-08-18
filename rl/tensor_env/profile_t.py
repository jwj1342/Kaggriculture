#!/usr/bin/env python
"""Where does a step_idx lane-step spend its time? (DESIGN.md B4b, step 1)

Runs step_idx-driven episodes under the realistic policy load (actions
sampled from features_t.masks_t with a seeded generator, exactly test_b3b's
G6 loop) and prints three ranked tables:

  1. per-phase wall time (method wrappers around EpisodeT's phases): decode
     farmer / hands / market, unit-slot apply, market order loop (lockstep +
     atomics + price refresh), town consume, plant decay, the end-of-day
     tensor refresh, the end-of-day RNG segment (with its host word pull),
     the end-of-day drop, plus masks_t + sampling outside the engine;
  2. cProfile top-N by tottime (host python vs torch dispatch);
  3. torch.profiler top-N ops by self CPU time with call counts -- the call
     count divided by steps is the per-step kernel-launch count, which is
     what a CUDA device would pay per step regardless of B.

    python rl/tensor_env/profile_t.py                     # B=1024, 120 steps, cpu
    python rl/tensor_env/profile_t.py --B 4096 --steps 48 --no-torch-prof

Read-only: instruments by wrapping methods on the EpisodeT class for the
duration of the run; nothing in the engine changes.
"""

import argparse
import cProfile
import functools
import os
import pstats
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
for _p in (_HERE, _RL):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import torch

import engine_t
import engine_t_idx                      # noqa: F401  (attaches step_idx)
import features_t

# (label, method name) -- every method wrapped is timed by wall clock; nested
# wrappers are subtracted so each phase reports SELF time.
_PHASES = [
    ("decode.farmer",        "_idx_decode_farmer"),
    ("decode.hands",         "_idx_decode_hands"),
    ("decode.market",        "_idx_decode_market"),
    ("apply.unit_slots",     "_idx_apply_slot"),
    ("market.orders(total)", "_idx_market"),
    ("market.lockstep",      "_market_lockstep"),
    ("market.hire",          "_idx_do_hire"),
    ("market.land",          "_idx_do_land"),
    ("market.refresh_prices", "_refresh_prices"),
    ("town.consume",         "_town_consume"),
    ("decay.plants",         "_decay_plants"),
    ("eod.total",            "_end_of_day"),
    ("eod.tensor_refresh",   "_eod_refresh"),
    ("eod.rng_segment",      "_eod_rng"),
    ("eod.rng_host_words",   "_rng_words"),
    ("eod.drop_seq",         "_eod_drop_seq"),
    ("eod.drop_host",        "_eod_drop_host"),
    ("step_idx(total)",      "step_idx"),
]


class _Timers:
    def __init__(self):
        self.self_t = {}
        self.calls = {}
        self.stack = []

    def wrap(self, label, fn):
        @functools.wraps(fn)
        def w(*a, **k):
            t0 = time.perf_counter()
            self.stack.append(0.0)           # child time accumulator
            try:
                return fn(*a, **k)
            finally:
                dt = time.perf_counter() - t0
                child = self.stack.pop()
                self.self_t[label] = self.self_t.get(label, 0.0) + dt - child
                self.calls[label] = self.calls.get(label, 0) + 1
                if self.stack:
                    self.stack[-1] += dt
        return w


def _instrument(timers):
    cls = engine_t.EpisodeT
    saved = {}
    for label, name in _PHASES:
        fn = getattr(cls, name, None)
        if fn is None:
            continue
        saved[name] = fn
        setattr(cls, name, timers.wrap(label, fn))
    return saved


def _restore(saved):
    for name, fn in saved.items():
        setattr(engine_t.EpisodeT, name, fn)


def run(B, steps, device, timers=None, seed=4242, prof=None):
    ep = engine_t.EpisodeT(list(range(81_000, 81_000 + B)),
                           episode_steps=steps + 2, device=device)
    g = torch.Generator().manual_seed(seed)
    t_mask = 0.0
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
        f_idx = torch.stack(fs, 1).to(device)
        m_idx = torch.stack(ms, 1).to(device)
        t_mask += time.perf_counter() - tm
        ep.step_idx(f_idx, m_idx)
        if prof is not None:
            prof.step()
    if device.startswith("cuda"):
        torch.cuda.synchronize(torch.device(device))
    wall = time.perf_counter() - t0
    if timers is not None:
        timers.self_t["masks_t+sample (outside engine)"] = t_mask
        timers.calls["masks_t+sample (outside engine)"] = steps
    return wall, ep


def phase_table(timers, wall, B, steps):
    print(f"\n-- per-phase self time  (B={B}, steps={steps}, wall {wall:.2f}s, "
          f"{steps * B / wall:,.0f} lane-steps/s incl. masks+sample) --")
    print(f"{'phase':<34}{'self s':>9}{'% wall':>8}{'calls':>8}"
          f"{'us/lane-step':>14}")
    rows = sorted(timers.self_t.items(), key=lambda kv: -kv[1])
    for label, t in rows:
        if label.endswith("(total)"):
            continue
        print(f"{label:<34}{t:>9.3f}{100 * t / wall:>8.1f}"
              f"{timers.calls[label]:>8}{t / (steps * B) * 1e6:>14.2f}")
    tot = sum(t for l, t in rows if not l.endswith("(total)"))
    print(f"{'(sum of listed phases)':<34}{tot:>9.3f}{100 * tot / wall:>8.1f}")
    for label in ("step_idx(total)", "market.orders(total)"):
        if label in timers.self_t:
            # totals are self time of the wrapper = time not inside any listed
            # child; report inclusive by adding children? Simpler: print self.
            print(f"{label + ' [self, unlisted glue]':<34}"
                  f"{timers.self_t[label]:>9.3f}"
                  f"{100 * timers.self_t[label] / wall:>8.1f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--B", type=int, default=1024)
    ap.add_argument("--steps", type=int, default=120)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--no-cprofile", action="store_true")
    ap.add_argument("--no-torch-prof", action="store_true")
    ap.add_argument("--phases-only", action="store_true")
    args = ap.parse_args()
    print(f"torch {torch.__version__}, threads={torch.get_num_threads()}, "
          f"device={args.device}, B={args.B}, steps={args.steps}", flush=True)

    # 1. phase timers (plain run, wrappers only)
    timers = _Timers()
    saved = _instrument(timers)
    try:
        wall, _ = run(args.B, args.steps, args.device, timers)
    finally:
        _restore(saved)
    phase_table(timers, wall, args.B, args.steps)
    if args.phases_only:
        return

    # 2. cProfile (host python view)
    if not args.no_cprofile:
        pr = cProfile.Profile()
        pr.enable()
        run(args.B, args.steps, args.device)
        pr.disable()
        print(f"\n-- cProfile top {args.top} by tottime --")
        st = pstats.Stats(pr, stream=sys.stdout)
        st.sort_stats("tottime").print_stats(args.top)

    # 3. torch.profiler (op view; call count == launches per run)
    if not args.no_torch_prof:
        from torch.profiler import profile, ProfilerActivity
        acts = [ProfilerActivity.CPU]
        if args.device.startswith("cuda"):
            acts.append(ProfilerActivity.CUDA)
        with profile(activities=acts) as prof:
            run(args.B, args.steps, args.device)
        ka = prof.key_averages()
        print(f"\n-- torch.profiler top {args.top} ops by self CPU time "
              f"(count/step = launches per step) --")
        rows = sorted(ka, key=lambda e: -e.self_cpu_time_total)
        n_ops = sum(e.count for e in ka if e.key.startswith("aten::"))
        print(f"{'op':<40}{'self ms':>10}{'count':>9}{'count/step':>12}"
              f"{'us/call':>9}")
        for e in rows[:args.top]:
            print(f"{e.key[:39]:<40}{e.self_cpu_time_total / 1e3:>10.1f}"
                  f"{e.count:>9}{e.count / args.steps:>12.1f}"
                  f"{e.self_cpu_time_total / max(e.count, 1):>9.1f}")
        print(f"total aten:: calls: {n_ops}  -> {n_ops / args.steps:,.0f} per step")
    print("PROFILE-DONE")


if __name__ == "__main__":
    main()
