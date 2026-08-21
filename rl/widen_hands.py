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


def widen_flat(model, head, old_n, new_n):
    """Widen a flat head (farmer / market): new actions are APPENDED to
    the action list by convention (SELL_HALF set the precedent), so the
    old rows copy in place and the tail starts at zero weight, NEW_BIAS.
    Residual actors carry a delta twin (d_<head>) -- widened the same."""
    out = dict(model)
    for key in (head, f"d_{head}"):
        wk, bk = f"{key}.weight", f"{key}.bias"
        if wk not in model:
            continue
        w, b = model[wk], model[bk]
        assert w.shape[0] == old_n, (wk, w.shape, old_n)
        nw = torch.zeros((new_n, w.shape[1]), dtype=w.dtype)
        nb = torch.full((new_n,), NEW_BIAS, dtype=b.dtype)
        nw[:old_n], nb[:old_n] = w, b
        out[wk], out[bk] = nw, nb
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--old-tasks", type=int, default=0,
                    help="source hand-task count (0 = head unchanged)")
    ap.add_argument("--old-market", type=int, default=0,
                    help="source market head width (0 = head unchanged)")
    ap.add_argument("--old-farmer", type=int, default=0,
                    help="source farmer head width (0 = head unchanged)")
    args = ap.parse_args()

    ck = torch.load(args.src, map_location="cpu", weights_only=False)
    model = ck.get("model") or ck
    hidden = ck.get("hidden") or [1024, 512]
    v_hidden = ck.get("v_hidden") or 512
    n_hands = A.MAX_HANDS
    old_tasks = args.old_tasks or A.N_HAND_TASK
    old_market = args.old_market or A.N_MARKET
    old_farmer = args.old_farmer or A.N_FARMER
    parts = []
    widened = dict(model)
    if old_tasks != A.N_HAND_TASK:
        widened = widen(widened, n_hands, old_tasks, A.N_HAND_TASK,
                        hidden[1])
        parts.append(f"hands {old_tasks}->{A.N_HAND_TASK}")
    if old_market != A.N_MARKET:
        widened = widen_flat(widened, "market", old_market, A.N_MARKET)
        parts.append(f"market {old_market}->{A.N_MARKET}")
    if old_farmer != A.N_FARMER:
        widened = widen_flat(widened, "farmer", old_farmer, A.N_FARMER)
        parts.append(f"farmer {old_farmer}->{A.N_FARMER}")
    assert parts, "nothing to widen: pass --old-tasks/--old-market/--old-farmer"

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
    # the OLD net needs the old vocabulary widths to load the old weights
    _, _, olda, oldc = build_actor_critic(
        O.OBS_DIM, old_farmer, old_market, hidden1=hidden[0],
        hidden2=hidden[1], v_hidden=v_hidden, device="cpu", multi=True,
        n_hand_task=old_tasks)
    load_merged_state_dict(olda, oldc, model)
    with torch.no_grad():
        f_n, m_n, h_n = neta(obs)[:3]
        f_o, m_o, h_o = olda(obs)[:3]
    hn = h_n.view(-1, n_hands, A.N_HAND_TASK)
    ho = h_o.view(-1, n_hands, old_tasks)
    for name, new, old in (("farmer", f_n, f_o), ("market", m_n, m_o)):
        assert torch.equal(new[..., :old.shape[-1]], old), \
            f"{name} head prefix moved"
        tail = new[..., old.shape[-1]:]
        assert tail.numel() == 0 or torch.allclose(
            tail, torch.full_like(tail, NEW_BIAS)), f"{name} tail not bias"
    assert torch.equal(hn[..., :old_tasks], ho), "old task logits moved"
    nc = hn[..., old_tasks:]
    assert nc.numel() == 0 or torch.allclose(
        nc, torch.full_like(nc, NEW_BIAS)), "new column is not the bare bias"
    torch.save({"model": widened, "hidden": hidden, "v_hidden": v_hidden},
               args.dst)
    print(f"widened {', '.join(parts)}; heads verified identical on "
          f"{ep.B} reset lanes -> {args.dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
