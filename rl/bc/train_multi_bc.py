#!/usr/bin/env python
"""Behaviour-clone the current-balance top ladder into the multi-head actor.

Data: rl/bc/build_dataset.py shards (both seats of ~3.1k-rated games,
labels = head indices whose decode reproduces the recorded action; -1 is
skipped). Model: trl_policy.MultiActorNet -- the same net rl/train.py
trains, so the checkpoint feeds --init-from / --residual-base / export
unchanged ({"model": ..., "hidden": ...}).

The one lesson from the old line's BC post-mortem baked in: the market
head is ~an order of magnitude NOOP-heavy and a plain CE learns to stay
silent (docs: "market 头 90% NOOP 标签 -> 学成永远沉默"). Non-default
classes get 1/freq^alpha weights on the market and hand heads.

    python rl/bc/train_multi_bc.py --epochs 12          # CPU ok, GPU faster
    -> rl/runs/bc-toprec/bc.pt  + per-head val accuracy report

Split is BY EPISODE (both seats of a game stay on one side).
"""

import argparse
import glob
import os
import sys

import numpy as np
import torch
import torch.nn.functional as Fn

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
_REPO = os.path.dirname(_RL)
for p in (_RL, os.path.join(_RL, "tensor_env")):
    if p not in sys.path:
        sys.path.insert(0, p)

import actions as A  # noqa: E402
import obs as O      # noqa: E402

DATA = os.path.join(_REPO, "data", "bcdata")


def _load(files):
    Xs, Fs, Ms, Hs = [], [], [], []
    for f in files:
        z = np.load(f)
        Xs.append(z["obs"])
        Fs.append(z["farmer"])
        Ms.append(z["market"])
        Hs.append(z["hands"])
    return (np.concatenate(Xs), np.concatenate(Fs),
            np.concatenate(Ms), np.concatenate(Hs))


def _class_weights(labels, n_classes, alpha):
    lab = labels[labels >= 0]
    cnt = np.bincount(lab, minlength=n_classes).astype(np.float64)
    w = (cnt.sum() / np.maximum(cnt, 1.0)) ** alpha
    w = w / w[cnt > 0].mean()
    return torch.tensor(w, dtype=torch.float32)


def _head_ce(logits, lab, weight=None):
    ok = lab >= 0
    if not bool(ok.any()):
        return None, 0
    return Fn.cross_entropy(logits[ok], lab[ok].long(),
                            weight=weight), int(ok.sum())


def _accuracy(logits, lab):
    ok = lab >= 0
    if not bool(ok.any()):
        return float("nan"), 0
    pred = logits.argmax(-1)
    return float((pred[ok] == lab[ok]).float().mean()), int(ok.sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=12)
    ap.add_argument("--batch", type=int, default=512)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--alpha", type=float, default=0.5,
                    help="class-weight exponent for market/hand heads")
    ap.add_argument("--val-frac", type=float, default=0.15)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available()
                    else "cpu")
    ap.add_argument("--hidden", type=int, nargs=2, default=[512, 256])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(_RL, "runs", "bc-toprec",
                                                  "bc.pt"))
    args = ap.parse_args()
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)

    shards = sorted(glob.glob(os.path.join(DATA, "*.npz")))
    eps = sorted({os.path.basename(s).split("-")[0] for s in shards})
    rng.shuffle(eps)
    n_val = max(1, int(len(eps) * args.val_frac))
    val_eps = set(eps[:n_val])
    tr = [s for s in shards
          if os.path.basename(s).split("-")[0] not in val_eps]
    va = [s for s in shards if os.path.basename(s).split("-")[0] in val_eps]
    X, F, M, H = _load(tr)
    Xv, Fv, Mv, Hv = _load(va)
    print(f"train {X.shape[0]:,} steps / {len(tr)} shards; "
          f"val {Xv.shape[0]:,} / {len(va)}")

    dev = torch.device(args.device)
    from trl_policy import MultiActorNet
    net = MultiActorNet(O.OBS_DIM, A.N_FARMER, A.N_MARKET,
                        args.hidden[0], args.hidden[1]).to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=args.lr)
    w_m = _class_weights(M, A.N_MARKET, args.alpha).to(dev)
    w_h = _class_weights(H.reshape(-1), A.N_HAND_TASK, args.alpha).to(dev)

    Xt = torch.tensor(X, dtype=torch.float16)
    Ft = torch.tensor(F, dtype=torch.int64)
    Mt = torch.tensor(M, dtype=torch.int64)
    Ht = torch.tensor(H, dtype=torch.int64)
    Xvt = torch.tensor(Xv, dtype=torch.float16)
    Fvt, Mvt, Hvt = (torch.tensor(v, dtype=torch.int64) for v in (Fv, Mv, Hv))

    n = Xt.shape[0]
    for ep in range(args.epochs):
        net.train()
        perm = torch.randperm(n)
        tot = cnt = 0.0
        for i in range(0, n, args.batch):
            idx = perm[i:i + args.batch]
            x = Xt[idx].to(dev, torch.float32)
            fl, ml, hl = net(x)
            losses = []
            lf, _ = _head_ce(fl, Ft[idx].to(dev))
            lm, _ = _head_ce(ml, Mt[idx].to(dev), w_m)
            lh, _ = _head_ce(hl.reshape(-1, A.N_HAND_TASK),
                             Ht[idx].reshape(-1).to(dev), w_h)
            for l in (lf, lm, lh):
                if l is not None:
                    losses.append(l)
            loss = sum(losses)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            tot += float(loss) * len(idx)
            cnt += len(idx)
        # validation
        net.eval()
        accs = {}
        with torch.no_grad():
            outs = []
            for i in range(0, Xvt.shape[0], 4096):
                outs.append(net(Xvt[i:i + 4096].to(dev, torch.float32)))
            fl = torch.cat([o[0] for o in outs])
            ml = torch.cat([o[1] for o in outs])
            hl = torch.cat([o[2] for o in outs])
            accs["farmer"], _ = _accuracy(fl, Fvt.to(dev))
            accs["market"], _ = _accuracy(ml, Mvt.to(dev))
            accs["hand"], _ = _accuracy(hl.reshape(-1, A.N_HAND_TASK),
                                        Hvt.reshape(-1).to(dev))
            noop = float((ml.argmax(-1) == 0).float().mean())
        print(f"epoch {ep:2d}  loss {tot / cnt:.4f}  "
              f"val acc farmer {accs['farmer']:.3f} market {accs['market']:.3f} "
              f"hand {accs['hand']:.3f}  market-argmax-NOOP {noop:.2f}",
              flush=True)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    # train.py-compatible: actor keys under "model" (critic absent is fine
    # for export; --init-from merges what it finds)
    torch.save({"model": net.state_dict(), "hidden": list(args.hidden),
                "v_hidden": 256, "algo": "bc", "iter": -1,
                "args": vars(args)}, args.out)
    print(f"saved {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
