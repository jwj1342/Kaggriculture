#!/usr/bin/env python
"""Behaviour-clone the scripted expert into the Policy net, saving a
checkpoint train_ppo.py can resume from (fresh optimiser, stage 0).

    python rl/train_bc.py --data rl/runs/bc/data --run m2 --epochs 6
"""

import argparse
import glob
import os
import sys

import numpy as np
import torch

_RL = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _RL)

import actions as A
import obs as O
from policy import Policy


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(_RL, "runs", "bc", "data"))
    ap.add_argument("--run", default="m2")
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--batch", type=int, default=2048)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--threads", type=int, default=16)
    args = ap.parse_args()

    torch.set_num_threads(args.threads)
    shards = sorted(glob.glob(os.path.join(args.data, "shard-*.npz")))
    assert shards, f"no shards under {args.data}"
    obs_l, fm_l, mm_l, fa_l, ma_l = [], [], [], [], []
    for s in shards:
        d = np.load(s)
        obs_l.append(d["obs"])
        fm_l.append(d["fmask"])
        mm_l.append(d["mmask"])
        fa_l.append(d["fa"])
        ma_l.append(d["ma"])
    X = torch.from_numpy(np.concatenate(obs_l)).float()
    FM = torch.from_numpy(np.concatenate(fm_l))
    MM = torch.from_numpy(np.concatenate(mm_l))
    FA = torch.from_numpy(np.concatenate(fa_l).astype(np.int64))
    MA = torch.from_numpy(np.concatenate(ma_l).astype(np.int64))
    n = X.shape[0]
    print(f"{n:,} samples from {len(shards)} shards")

    policy = Policy(O.OBS_DIM, A.N_FARMER, A.N_MARKET)
    optim = torch.optim.Adam(policy.parameters(), lr=args.lr)
    ce = torch.nn.CrossEntropyLoss()

    for epoch in range(args.epochs):
        perm = torch.randperm(n)
        tot = facc = macc = 0.0
        for i in range(0, n, args.batch):
            mb = perm[i:i + args.batch]
            h = policy.trunk(X[mb])
            flog = policy.farmer(h).masked_fill(~FM[mb], -1e9)
            mlog = policy.market(h).masked_fill(~MM[mb], -1e9)
            loss = ce(flog, FA[mb]) + ce(mlog, MA[mb])
            optim.zero_grad()
            loss.backward()
            optim.step()
            bs = len(mb)
            tot += loss.item() * bs
            facc += (flog.argmax(-1) == FA[mb]).sum().item()
            macc += (mlog.argmax(-1) == MA[mb]).sum().item()
        print(f"epoch {epoch}: loss {tot / n:.4f}  "
              f"farmer acc {facc / n:.3f}  market acc {macc / n:.3f}", flush=True)

    run_dir = os.path.join(_RL, "runs", args.run)
    os.makedirs(run_dir, exist_ok=True)
    ppo_optim = torch.optim.Adam(policy.parameters(), lr=3e-4, eps=1e-5)
    ck = {"model": policy.state_dict(), "optim": ppo_optim.state_dict(),
          "global_step": 0, "stage": 0, "iter": -1}
    # bc_init.pt is immutable -- PPO overwrites latest.pt within minutes, and
    # the pristine clone must stay exportable/diagnosable forever.
    torch.save(ck, os.path.join(run_dir, "bc_init.pt"))
    torch.save(ck, os.path.join(run_dir, "latest.pt"))
    print(f"BC checkpoint -> {run_dir}/latest.pt (+ immutable bc_init.pt)")
    print("BC-DONE")


if __name__ == "__main__":
    main()
