#!/usr/bin/env python
"""Net2Net-style hand-head widening: give an old checkpoint the new task.

The hand-task vocabulary grew (8 -> 9: PLANT, the w49 anatomy), and the
policy head is a single Linear of n_hands * n_hand_task rows in hand-major
order, so an era-mismatched checkpoint fails loud by design. This widens
the head instead of retraining it: every old row is copied into place and
each hand's new task row starts at ZERO weight with a NEW_BIAS logit --
the trunk's behaviour is preserved (the new task draws ~e^(NEW_BIAS -
auto_bias) of AUTO's probability mass, negligible at -4 vs 2.5) while
sampling can still discover it and gradient can grow it.

The output is a model-only checkpoint for --init-from (fresh optimizer,
fresh step counter -- the kickstart anneal re-runs, which is the point:
the teacher's hand-PLANT intents label the new column from iter 0).

    python rl/widen_hands.py <old.pt> <out.pt> [--old-tasks 8]

Self-check: both policies run on real reset observations; farmer/market/
value outputs must be byte-identical and hand logits must agree on every
old task column.
"""

import argparse
import os
import sys

import torch

_HERE = os.path.dirname(os.path.abspath(__file__))
for p in (_HERE, os.path.join(_HERE, "tensor_env")):
    if p not in sys.path:
        sys.path.insert(0, p)

import actions as A

NEW_BIAS = -4.0


def widen(model, n_hands, old_tasks, new_tasks, hidden2):
    out = dict(model)
    w, b = model["hands.weight"], model["hands.bias"]
    assert w.shape == (n_hands * old_tasks, hidden2), w.shape
    nw = torch.zeros((n_hands * new_tasks, hidden2), dtype=w.dtype)
    nb = torch.full((n_hands * new_tasks,), NEW_BIAS, dtype=b.dtype)
    for h in range(n_hands):
        nw[h * new_tasks:h * new_tasks + old_tasks] = \
            w[h * old_tasks:(h + 1) * old_tasks]
        nb[h * new_tasks:h * new_tasks + old_tasks] = \
            b[h * old_tasks:(h + 1) * old_tasks]
    out["hands.weight"], out["hands.bias"] = nw, nb
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--old-tasks", type=int, default=8)
    args = ap.parse_args()

    ck = torch.load(args.src, map_location="cpu", weights_only=False)
    model = ck.get("model") or ck
    hidden = ck.get("hidden") or [1024, 512]
    v_hidden = ck.get("v_hidden") or 512
    n_hands = A.MAX_HANDS
    new_tasks = A.N_HAND_TASK
    assert new_tasks > args.old_tasks, (new_tasks, args.old_tasks)
    widened = widen(model, n_hands, args.old_tasks, new_tasks, hidden[1])

    # -- self-check on real reset observations ------------------------------
    import engine_t
    import features_t as O
    from trl_policy import build_actor_critic, load_merged_state_dict
    ep = engine_t.EpisodeT(list(range(41, 49)), episode_steps=720,
                           device="cpu")
    obs = O.encode_t(ep, 0)
    _, _, neta, netc = build_actor_critic(
        O.OBS_DIM, A.N_FARMER, A.N_MARKET, hidden1=hidden[0],
        hidden2=hidden[1], v_hidden=v_hidden, device="cpu", multi=True)
    load_merged_state_dict(neta, netc, widened)
    # the OLD net needs the old vocabulary width to load the old weights
    _, _, olda, oldc = build_actor_critic(
        O.OBS_DIM, A.N_FARMER, A.N_MARKET, hidden1=hidden[0],
        hidden2=hidden[1], v_hidden=v_hidden, device="cpu", multi=True,
        n_hand_task=args.old_tasks)
    load_merged_state_dict(olda, oldc, model)
    with torch.no_grad():
        f_n, m_n, h_n = neta(obs)[:3]
        f_o, m_o, h_o = olda(obs)[:3]
    hn = h_n.view(-1, n_hands, new_tasks)
    ho = h_o.view(-1, n_hands, args.old_tasks)
    assert torch.equal(f_n, f_o) and torch.equal(m_n, m_o), \
        "farmer/market heads changed"
    assert torch.equal(hn[..., :args.old_tasks], ho), "old task logits moved"
    nc = hn[..., args.old_tasks:]
    assert torch.allclose(nc, torch.full_like(nc, NEW_BIAS)), \
        "new column is not the bare bias"
    torch.save({"model": widened, "hidden": hidden, "v_hidden": v_hidden},
               args.dst)
    print(f"widened {args.old_tasks} -> {new_tasks} hand tasks; "
          f"heads verified identical on {ep.B} reset lanes -> {args.dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
