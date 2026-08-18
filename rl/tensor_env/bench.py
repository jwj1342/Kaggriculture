#!/usr/bin/env python
"""Engine speed benchmark + multi-GPU scaling probe (map-reduce prototype).

    python rl/tensor_env/bench.py --engines kaggle np t-cpu          # CPU only
    python rl/tensor_env/bench.py --engines t-gpu --devices 0 1      # GPU node

Three action loads per engine:
  noop     PASS/PASS every turn -- pure engine cost floor.
  replay   a pre-recorded random-legal stream (recorded once from engine_np)
           broadcast to every lane -- includes realistic host-side action
           parsing and market traffic (step_raw, dict interface).
  idx      (tensor engines only) the tensor-native path: step_idx driven by
           head indices sampled from features_t.masks_t every step with a
           seeded generator (test_b3b's G6 load). Reported twice: the full
           loop (masks + sample + step) and step_idx alone.

Multi-GPU mode is the map-reduce prototype the orchestration layer will grow
from: one spawned worker per device runs its own EpisodeT shard (map), the
parent sums lane-steps/s and collects per-device numbers (reduce). No state
crosses devices -- lanes are independent games, so sharding is exact, not
approximate.
"""

import argparse
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
for p in (_HERE, _RL):
    if p not in sys.path:
        sys.path.insert(0, p)

NOOP = {"farmer": ["PASS"], "hands": [], "market": []}


def record_stream(steps):
    import numpy as np
    import engine_np
    import actions as A
    from verify_t import _np_obs
    rng = np.random.default_rng(777)
    ep = engine_np.Episode(seed=777, episode_steps=steps + 1)
    stream = []
    for _ in range(steps):
        pair = []
        for pl in (0, 1):
            obs = _np_obs(ep, pl)
            fm, mm = A.farmer_mask(obs), A.market_mask(obs)
            pair.append(A.decode(obs, int(rng.choice(np.flatnonzero(fm))),
                                 int(rng.choice(np.flatnonzero(mm)))))
        ep.step(pair)
        stream.append(pair)
    return stream


def bench_kaggle(steps, load, stream):
    from kaggle_environments import make
    env = make("kaggriculture", configuration={"episodeSteps": steps + 1, "seed": 777})
    env.reset(2)
    t0 = time.perf_counter()
    for n in range(steps):
        env.step(stream[n] if load == "replay" else [NOOP, NOOP])
    return steps / (time.perf_counter() - t0)


def bench_np(steps, load, stream):
    import engine_np
    ep = engine_np.Episode(seed=777, episode_steps=steps + 1)
    t0 = time.perf_counter()
    for n in range(steps):
        ep.step(stream[n] if load == "replay" else [NOOP, NOOP])
    return steps / (time.perf_counter() - t0)


def bench_t(steps, load, stream, B, device):
    import torch
    import engine_t
    ep = engine_t.EpisodeT(list(range(70_000, 70_000 + B)),
                           episode_steps=steps + 1, device=device)
    if device.startswith("cuda"):
        torch.cuda.synchronize(torch.device(device))
    t0 = time.perf_counter()
    for n in range(steps):
        pair = stream[n] if load == "replay" else [NOOP, NOOP]
        ep.step_raw([pair] * B)
    if device.startswith("cuda"):
        torch.cuda.synchronize(torch.device(device))
    return steps * B / (time.perf_counter() - t0)


def bench_t_idx(steps, B, device, seed=4242):
    """step_idx under masks_t-sampled legal actions; returns (lane-steps/s
    for the whole loop, lane-steps/s for step_idx alone)."""
    import torch
    import engine_t
    import engine_t_idx  # noqa: F401  (attaches step_idx)
    import features_t
    ep = engine_t.EpisodeT(list(range(81_000, 81_000 + B)),
                           episode_steps=steps + 2, device=device)
    g = torch.Generator().manual_seed(seed)
    sync = (lambda: torch.cuda.synchronize(torch.device(device))
            if device.startswith("cuda") else None)
    t_step = 0.0
    sync()
    t0 = time.perf_counter()
    for _ in range(steps):
        fs, ms = [], []
        for p in (0, 1):
            fm, mm = features_t.masks_t(ep, p)
            fs.append(torch.multinomial(fm.double().cpu(), 1, generator=g)
                      .squeeze(-1))
            ms.append(torch.multinomial(mm.double().cpu(), 1, generator=g)
                      .squeeze(-1))
        f_idx = torch.stack(fs, 1).to(device)
        m_idx = torch.stack(ms, 1).to(device)
        sync()
        t1 = time.perf_counter()
        ep.step_idx(f_idx, m_idx)
        sync()
        t_step += time.perf_counter() - t1
    wall = time.perf_counter() - t0
    return steps * B / wall, steps * B / t_step


def _gpu_worker(dev_idx, B, steps, load, stream, q):
    import torch  # noqa: F401  (fresh spawn: clean CUDA context per device)
    rate = bench_t(steps, load, stream, B, f"cuda:{dev_idx}")
    q.put((dev_idx, rate))


def bench_multi_gpu(devices, B, steps, load, stream):
    """Map: one worker per device, B lanes each. Reduce: sum of rates."""
    import multiprocessing as mp
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    procs = [ctx.Process(target=_gpu_worker, args=(d, B, steps, load, stream, q))
             for d in devices]
    t0 = time.perf_counter()
    for p in procs:
        p.start()
    results = [q.get() for _ in procs]
    for p in procs:
        p.join()
    wall = time.perf_counter() - t0
    total = sum(r for _, r in results)
    return total, dict(results), steps * B * len(devices) / wall


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engines", nargs="+",
                    default=["kaggle", "np", "t-cpu"],
                    choices=["kaggle", "np", "t-cpu", "t-gpu", "t-multi"])
    ap.add_argument("--steps", type=int, default=240)
    ap.add_argument("--batches", type=int, nargs="+", default=[256, 1024, 4096])
    ap.add_argument("--devices", type=int, nargs="+", default=[0])
    args = ap.parse_args()

    print("recording realistic action stream...", flush=True)
    stream = record_stream(args.steps)
    base = {}

    for load in ("noop", "replay"):
        print(f"\n== load: {load} ==", flush=True)
        if "kaggle" in args.engines:
            r = bench_kaggle(args.steps, load, stream)
            base[load] = r
            print(f"kaggle reference      : {r:>12,.0f} lane-steps/s  (1x)", flush=True)
        if "np" in args.engines:
            r = bench_np(args.steps, load, stream)
            print(f"engine_np (B=1)       : {r:>12,.0f} lane-steps/s"
                  f"  ({r / base.get(load, r):.0f}x)", flush=True)
        if "t-cpu" in args.engines:
            for B in args.batches:
                r = bench_t(args.steps, load, stream, B, "cpu")
                print(f"engine_t cpu  B={B:>5} : {r:>12,.0f} lane-steps/s"
                      f"  ({r / base.get(load, r):.0f}x)", flush=True)
        if "t-gpu" in args.engines:
            for B in args.batches:
                r = bench_t(args.steps, load, stream, B, f"cuda:{args.devices[0]}")
                print(f"engine_t gpu  B={B:>5} : {r:>12,.0f} lane-steps/s"
                      f"  ({r / base.get(load, r):.0f}x)", flush=True)
        if "t-multi" in args.engines and len(args.devices) > 1:
            B = args.batches[-1]
            total, per_dev, eff = bench_multi_gpu(
                args.devices, B, args.steps, load, stream)
            per = " ".join(f"cuda:{d}={r:,.0f}" for d, r in sorted(per_dev.items()))
            print(f"engine_t multi-gpu {len(args.devices)}dev B={B}/dev: "
                  f"sum {total:,.0f}  wall-effective {eff:,.0f}  [{per}]", flush=True)
    if "t-cpu" in args.engines or "t-gpu" in args.engines:
        print(f"\n== load: idx (step_idx, masks_t-sampled) ==", flush=True)
        devs = []
        if "t-cpu" in args.engines:
            devs.append(("cpu", "cpu"))
        if "t-gpu" in args.engines:
            devs.append(("gpu", f"cuda:{args.devices[0]}"))
        for tag, dev in devs:
            for B in args.batches:
                full, alone = bench_t_idx(args.steps, B, dev)
                print(f"engine_t {tag:<3} B={B:>5} : step_idx alone "
                      f"{alone:>10,.0f} lane-steps/s ; incl. masks+sample "
                      f"{full:>10,.0f}", flush=True)
    print("\nBENCH-DONE", flush=True)


if __name__ == "__main__":
    main()
