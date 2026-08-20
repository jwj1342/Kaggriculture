#!/usr/bin/env python
"""Fork / restore for EpisodeT batches -- the backplay primitive.

TODO #6 called it: EpisodeT state is all tensors, fork = clone. The RNG
needs no state at all -- every daily draw derives from
random.Random((seed * 1_000_003) ^ day), so seeds plus _step determine
the future. What fork() must carry beyond the tensors: the host-side
scalars (_step/day/hour/done), the two host mirrors (_shops_len,
_inv_ord) and the seeds list.

    st = fork(ep)          # snapshot, detached clones
    restore(ep, st)        # overwrite ep in place (same B, any instance)

Gate (python rl/tensor_env/bank_t.py): drive an episode 200 steps on
random legal actions, fork, continue 64 steps; restore into a FRESH
EpisodeT and replay the same 64 actions -- full snapshots must match
byte for byte, weeds and shop unlocks included (two day boundaries).
Ends BANK-PASS / BANK-FAIL.
"""

import copy
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
for p in (_HERE, _RL):
    if p not in sys.path:
        sys.path.insert(0, p)

import torch

_SCALARS = ("_step", "day", "hour", "done", "starting_money")
_LISTS = ("seeds", "_shops_len", "_inv_ord", "_ord_ctr")


def fork(ep):
    """Detached snapshot of every mutable piece of an EpisodeT."""
    st = {"__tensors__": {}, "__scalars__": {}, "__lists__": {},
          "__B__": ep.B}
    for name, val in vars(ep).items():
        if isinstance(val, torch.Tensor):
            # remember which tensors are lane-first so restore_lanes can
            # remap them; constants and oddly-shaped state stay whole
            st["__tensors__"][name] = (val.clone(),
                                       val.dim() > 0
                                       and val.shape[0] == ep.B)
    for name in _SCALARS:
        if hasattr(ep, name):
            st["__scalars__"][name] = getattr(ep, name)
    for name in _LISTS:
        if hasattr(ep, name):
            st["__lists__"][name] = copy.deepcopy(getattr(ep, name))
    return st


def restore(ep, st):
    """Overwrite ep with a fork()ed snapshot (batch sizes must match)."""
    for name, entry in st["__tensors__"].items():
        val = entry[0] if isinstance(entry, tuple) else entry
        cur = getattr(ep, name, None)
        if isinstance(cur, torch.Tensor) and cur.shape == val.shape \
                and cur.dtype == val.dtype:
            cur.copy_(val)
        else:
            setattr(ep, name, val.clone())
    for name, val in st["__scalars__"].items():
        setattr(ep, name, val)
    for name, val in st["__lists__"].items():
        setattr(ep, name, copy.deepcopy(val))
    return ep


def restore_lanes(ep, st, src_idx):
    """Restore a snapshot into ep with per-lane remapping: ep lane i gets
    the bank's lane src_idx[i]. Lane-first tensors (flagged at fork time)
    are gathered on dim 0; everything else restores whole. Lets a small
    bank (e.g. 64 barnyard-vs-barnyard games) seed a big training batch."""
    src = list(int(i) for i in src_idx)
    assert len(src) == ep.B, (len(src), ep.B)
    idx_t = torch.as_tensor(src, dtype=torch.int64)
    for name, entry in st["__tensors__"].items():
        val, lane_first = entry if isinstance(entry, tuple) else (entry, False)
        pick = (val.index_select(0, idx_t.to(val.device))
                if lane_first else val)
        cur = getattr(ep, name, None)
        if isinstance(cur, torch.Tensor) and cur.shape == pick.shape \
                and cur.dtype == pick.dtype:
            cur.copy_(pick)
        else:
            setattr(ep, name, pick.clone().to(ep.device))
    for name, val in st["__scalars__"].items():
        setattr(ep, name, val)
    for name, val in st["__lists__"].items():
        if isinstance(val, list) and len(val) == st.get("__B__", -1):
            setattr(ep, name, copy.deepcopy([val[i] for i in src]))
        else:
            setattr(ep, name, copy.deepcopy(val))
    return ep


def _gate():
    import engine_t
    import engine_t_idx  # noqa: F401
    import features_t
    import verify

    B, pre, post = 3, 200, 64
    seeds = [88_000 + 13 * i for i in range(B)]
    gen = torch.Generator().manual_seed(17)
    ep = engine_t.EpisodeT(seeds, episode_steps=720, device="cpu")

    def rnd_actions(e):
        fi, mi = [], []
        for p in range(2):
            fm, mm = features_t.masks_t(e, p)
            fi.append(torch.multinomial(fm.double(), 1, generator=gen)
                      .squeeze(-1))
            mi.append(torch.multinomial(mm.double(), 1, generator=gen)
                      .squeeze(-1))
        return torch.stack(fi, 1), torch.stack(mi, 1)

    for _ in range(pre):
        fi, mi = rnd_actions(ep)
        ep.step_idx(fi, mi)
    st = fork(ep)
    tape = []
    for _ in range(post):
        fi, mi = rnd_actions(ep)
        tape.append((fi, mi))
        ep.step_idx(fi, mi)
    want = [ep.snapshot(l) for l in range(B)]

    fresh = engine_t.EpisodeT(seeds, episode_steps=720, device="cpu")
    # dirty the fresh instance so restore() has to overwrite real state
    fi, mi = rnd_actions(fresh)
    fresh.step_idx(fi, mi)
    restore(fresh, st)
    for fi, mi in tape:
        fresh.step_idx(fi, mi)
    for lane in range(B):
        d = verify.first_diff(fresh.snapshot(lane), want[lane])
        if d:
            print(f"BANK-FAIL lane {lane}: {d}")
            return 1
    print(f"BANK-PASS: fork at step {pre}, {post} replayed steps across "
          f"{post // 24} day boundaries, {B} lanes snapshot-identical")
    return 0


if __name__ == "__main__":
    sys.exit(_gate())
