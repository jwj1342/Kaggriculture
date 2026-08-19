"""Behavior Cloning pretraining from the 371 expert plans.

Two stages:
1. collect: replay plans in the local engine (vs starter) and harvest (features,
   task_label, mode_label) tuples.
2. train: fit a small MLP to predict the labels from features.

Output: ``rl/weights_bc.npz`` — a PPO-compatible weights file the trainer can
warm-start from.
"""

import base64
import gzip
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

from . import features  # noqa: E402
from .action_space import labels_from_plan_turn  # noqa: E402
from .ppo import MLP, MarketMLP  # noqa: E402


TRACES = "dist/tracelib.json.xz"
OUT_DATA = "rl/bc_data.npz"
OUT_WEIGHTS = "rl/weights_bc.npz"


def _load_traces(limit=None):
    import lzma
    with lzma.open(TRACES, "rb") as f:
        data = json.loads(f.read().decode())
    lines = data.get("lines", {})
    rows = []
    for k, v in lines.items():
        turns = json.loads(gzip.decompress(base64.b64decode(v["turns"])).decode())
        rows.append({
            "key": k,
            "count": int(v.get("count", 1)),
            "best_score": float(v.get("best_score", 0)),
            "seed": int(v.get("seed", 0) or 0),
            "turns": turns,
        })
    rows.sort(key=lambda r: -r["count"])
    if limit:
        rows = rows[: int(limit)]
    return rows


def _replay_plan(plan_row, opponent="starter"):
    from .env import make_env
    seed = plan_row.get("seed") or 0
    trainer, obs = make_env(opponent=opponent, seed=seed)
    turns = plan_row["turns"]
    feats = []
    tasks = []
    modes = []
    step = 0
    try:
        while True:
            feats.append(features.encode(obs))
            if step >= len(turns):
                turn = {"farmer": ["PASS"], "hands": [], "market": []}
            else:
                turn = turns[step]
            tasks.append(labels_from_plan_turn(turn)[0])
            modes.append(labels_from_plan_turn(turn)[1])
            act = turn.get("market", []) or []
            # pass market orders as-is; policy seat gets raw turn back
            action = {"farmer": turn.get("farmer", ["PASS"]),
                      "hands": turn.get("hands", []) or [],
                      "market": list(act)}
            try:
                obs, reward, done, info = trainer.step(action)
            except Exception:
                done = True
            step += 1
            if done:
                break
    finally:
        try:
            trainer.close()
        except Exception:
            pass
    return feats, tasks, modes


def collect(limit=100, opponent="starter", out=OUT_DATA):
    rows = _load_traces(limit)
    X, yt, ym = [], [], []
    print(f"BC collect: {len(rows)} plans vs {opponent}")
    t0 = time.time()
    for i, row in enumerate(rows):
        print(f"  plan {i+1}/{len(rows)} key={row['key']} count={row['count']}")
        feats, tasks, modes = _replay_plan(row, opponent=opponent)
        X.extend(feats)
        yt.extend(tasks)
        ym.extend(modes)
        if (i + 1) % 4 == 0:
            print(f"    elapsed {time.time()-t0:.1f}s  samples={len(X)}")
    np.savez(out, X=np.array(X, dtype=np.float64),
             yt=np.array(yt, dtype=np.int64),
             ym=np.array(ym, dtype=np.int64))
    print(f"wrote {out}  samples={len(X)}  elapsed={time.time()-t0:.1f}s")


def train(data=OUT_DATA, epochs=20, lr=3e-3, out=OUT_WEIGHTS, batch=1024):
    dat = np.load(data)
    X = dat["X"].astype(np.float64)
    yt = dat["yt"].astype(np.int64)
    ym = dat["ym"].astype(np.int64)
    mlp = MLP(seed=42)
    N = len(X)
    print(f"BC train: {N} samples, {epochs} epochs, batch={batch}")
    for ep in range(epochs):
        idx = np.random.permutation(N)
        loss_sum = 0.0
        acc_t = 0
        acc_m = 0
        for start in range(0, N, batch):
            batch_idx = idx[start:start + batch]
            bx = X[batch_idx]
            bty = yt[batch_idx]
            bmy = ym[batch_idx]
            fwd = mlp.forward(bx)
            h2 = fwd["h2"]
            lt, lm = fwd["lt"], fwd["lm"]
            lt -= lt.max(axis=1, keepdims=True)
            pt = np.exp(lt) / np.exp(lt).sum(axis=1, keepdims=True)
            logp_t = np.log(pt[np.arange(len(batch_idx)), bty] + 1e-8)
            lm -= lm.max(axis=1, keepdims=True)
            pm = np.exp(lm) / np.exp(lm).sum(axis=1, keepdims=True)
            logp_m = np.log(pm[np.arange(len(batch_idx)), bmy] + 1e-8)
            loss = -logp_t.mean() - logp_m.mean()
            loss_sum += float(loss) * len(batch_idx)
            acc_t += int(np.sum(np.argmax(pt, axis=1) == bty))
            acc_m += int(np.sum(np.argmax(pm, axis=1) == bmy))
            dlt = pt.copy()
            dlt[np.arange(len(batch_idx)), bty] -= 1.0
            dlt = dlt / len(batch_idx)
            dlm = pm.copy()
            dlm[np.arange(len(batch_idx)), bmy] -= 1.0
            dlm = dlm / len(batch_idx)
            dlv = np.zeros((len(batch_idx), 1), dtype=np.float64)
            grads = mlp.backward(fwd, dlt, dlm, dlv)
            mlp.adam_step(grads, lr=lr, max_grad_norm=1.0)
        print(f"  epoch {ep+1}: loss={loss_sum/N:.4f} task_acc={acc_t/N:.3f} mode_acc={acc_m/N:.3f}")
    mlp.save(out)
    print(f"wrote {out}")


def collect_market(limit=100, opponent="starter", out="rl/bc_market_data.npz"):
    rows = _load_traces(limit)
    X, ym = [], []
    print(f"BC market collect: {len(rows)} plans vs {opponent}")
    t0 = time.time()
    for i, row in enumerate(rows):
        print(f"  plan {i+1}/{len(rows)} key={row['key']} count={row['count']}")
        feats, _, modes = _replay_plan(row, opponent=opponent)
        X.extend(feats)
        ym.extend(modes)
        if (i + 1) % 10 == 0:
            print(f"    elapsed {time.time()-t0:.1f}s  samples={len(X)}")
    np.savez(out, X=np.array(X, dtype=np.float64), ym=np.array(ym, dtype=np.int64))
    print(f"wrote {out}  samples={len(X)}  elapsed={time.time()-t0:.1f}s")


def train_market(data="rl/bc_market_data.npz", epochs=20, lr=3e-3, out="rl/weights_bc_market.npz", batch=1024):
    dat = np.load(data)
    X = dat["X"].astype(np.float64)
    ym = dat["ym"].astype(np.int64)
    mlp = MarketMLP(seed=42)
    N = len(X)
    print(f"BC market train: {N} samples, {epochs} epochs, batch={batch}")
    for ep in range(epochs):
        idx = np.random.permutation(N)
        loss_sum = 0.0
        acc_m = 0
        for start in range(0, N, batch):
            batch_idx = idx[start:start + batch]
            bx = X[batch_idx]
            bmy = ym[batch_idx]
            fwd = mlp.forward(bx)
            lm = fwd["lm"]
            lm -= lm.max(axis=1, keepdims=True)
            pm = np.exp(lm) / np.exp(lm).sum(axis=1, keepdims=True)
            logp = np.log(pm[np.arange(len(batch_idx)), bmy] + 1e-8)
            loss = -logp.mean()
            loss_sum += float(loss) * len(batch_idx)
            acc_m += int(np.sum(np.argmax(pm, axis=1) == bmy))
            dlm = pm.copy()
            dlm[np.arange(len(batch_idx)), bmy] -= 1.0
            dlm = dlm / len(batch_idx)
            dlv = np.zeros((len(batch_idx), 1), dtype=np.float64)
            grads = mlp.backward(fwd, dlm, dlv)
            mlp.adam_step(grads, lr=lr, max_grad_norm=1.0)
        print(f"  epoch {ep+1}: loss={loss_sum/N:.4f} mode_acc={acc_m/N:.3f}")
    mlp.save(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["collect", "train", "collect_market", "train_market"])
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    if args.cmd == "collect":
        kw = {"limit": args.limit}
        if args.out:
            kw["out"] = args.out
        collect(**kw)
    elif args.cmd == "train":
        kw = {"epochs": args.epochs}
        if args.out:
            kw["out"] = args.out
        train(**kw)
    elif args.cmd == "collect_market":
        kw = {"limit": args.limit}
        if args.out:
            kw["out"] = args.out
        collect_market(**kw)
    else:
        kw = {"epochs": args.epochs}
        if args.out:
            kw["out"] = args.out
        train_market(**kw)
