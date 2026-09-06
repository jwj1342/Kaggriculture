"""Gates for the autoregressive multi-order market head (rl/TODO.md 20).

Why the head exists, measured not assumed (docs/RUNS.md verdict 33): capping
closer_cleo at ONE market order a turn costs it -89,479 margin and leaves the
farm on 1,765 dollars against a baseline of 80,647. One order a turn is exactly
what every head in this repo could emit.

  O1  K == 1 is byte-identical to the historical single-order decode, on
      full engine state, every step.
  O2  zero-init slot_bias/couple_m: slot 0's distribution is bit-identical to
      MultiHeadMasked's market head, and log_prob decomposes as the sum of K
      identical slot terms.
  O3  known-positive: with K > 1 the decode really places more orders per turn
      than K == 1 does, and never displaces an order the K == 1 path made.
  O4  load-bearing: a BROKEN decode (extra macros dropped) must fail O3.
"""
import argparse, os, sys, torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine_t, engine_t_idx as X          # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import actions as A                          # noqa: E402


def _ep(seeds, steps, device):
    return engine_t.EpisodeT(seeds, episode_steps=steps, device=device)


def _state(ep):
    return [ep.money.clone(), ep.shed.clone(), ep.kind.clone(),
            ep.crop.clone(), ep.hands_n.clone(), ep.mkt_inv.clone()]


def gate_o1(args):
    """K == 1 (B,P,1) must equal the classic (B,P) path, bit for bit."""
    seeds = [77_000 + 13 * i for i in range(args.lanes)]
    a, b = _ep(seeds, args.steps, args.device), _ep(seeds, args.steps, args.device)
    g = torch.Generator(device="cpu").manual_seed(4242)
    n = 0
    while not a.done:
        f = torch.randint(0, A.N_FARMER, (args.lanes, 2), generator=g)
        m = torch.randint(0, A.N_MARKET, (args.lanes, 2), generator=g)
        a.step_idx(f, m)
        b.step_idx(f, m.unsqueeze(-1))          # (B, P, 1)
        for x, y in zip(_state(a), _state(b)):
            if not torch.equal(x, y):
                return False, f"O1: divergence at step {n}"
        n += 1
    return True, f"O1: {n} steps byte-identical (K=1 == classic)"


def gate_o2(args):
    """Zero tables: slot 0 == MultiHeadMasked's market head; K slots i.i.d."""
    import torch.nn.functional as F
    from trl_policy import MultiHeadMasked, MultiOrderMultiHead
    B, K, NM, NF, NT, H = 8, 3, A.N_MARKET, A.N_FARMER, A.N_HAND_TASK, 4
    g = torch.Generator(device="cpu").manual_seed(7)
    fl = torch.randn(B, NF, generator=g)
    ml = torch.randn(B, NM, generator=g)
    hl = torch.randn(B, H, NT, generator=g)
    fm = torch.ones(B, NF, dtype=torch.bool)
    mm = torch.rand(B, NM, generator=g) > 0.3
    mm[:, 0] = True
    hm = torch.ones(B, H, NT, dtype=torch.bool)

    cls = type("Bound", (MultiOrderMultiHead,),
               {"slot_bias": torch.zeros(K, NM),
                "couple_m": torch.zeros(NM, NM)})
    d1 = MultiHeadMasked(fl, ml, hl, fm, mm, hm)
    dK = cls(fl, ml, hl, fm, mm, hm)
    for k in range(K):
        if not torch.allclose(dK._slot_lp(k, None), d1.mlp, atol=0):
            return False, f"O2: slot {k} differs from the one-order head"
    act = torch.cat([torch.zeros(B, 1, dtype=torch.long),
                     torch.randint(0, NM, (B, K), generator=g),
                     torch.randint(0, NT, (B, H), generator=g)], -1)
    act[:, 1:1 + K] = act[:, 1:1 + K].clamp(max=NM - 1)
    want = (d1.flp[:, 0]
            + sum(d1.mlp.gather(-1, act[:, 1 + k:2 + k]).squeeze(-1)
                  for k in range(K))
            + d1.hlp.gather(-1, act[:, 1 + K:].unsqueeze(-1)).squeeze(-1).sum(-1))
    got = dK.log_prob(act)
    if not torch.allclose(want, got, atol=1e-5):
        return False, f"O2: log_prob mismatch, max |d| {(want-got).abs().max():.2e}"
    return True, f"O2: zero tables reproduce the one-order head (K={K})"


def gate_o3(args, broken=False):
    """Known-positive: K > 1 places strictly more orders and destroys none.

    The two decodes are compared INSIDE one episode, on the same engine state:
    the wrapper runs the real K-slot decode and, on the same tensors, the
    one-slot decode built from macro 0 alone. Rebuilding the decode's table
    argument outside step_idx would be a second implementation to get wrong.
    """
    seeds = [91_000 + 7 * i for i in range(args.lanes)]
    K = 3
    ep = _ep(seeds, args.steps, args.device)
    orig = X._idx_decode_market
    tally = {"extra": 0, "destroyed": 0}

    def spy(self, m_idx, herd, day, t):
        outK = orig(self, m_idx, herd, day, t)
        if m_idx.dim() == 3:
            out1 = orig(self, m_idx[..., 0], herd, day, t)
            live1 = int((out1[0] != 0).sum())
            liveK = int((outK[0] != 0).sum())
            tally["extra"] += liveK - live1
            tally["destroyed"] += int(
                (((out1[0] != 0) & (outK[0] != out1[0])).sum()))
        return outK

    X._idx_decode_market = spy
    engine_t.EpisodeT._idx_decode_market = spy
    try:
        g = torch.Generator(device="cpu").manual_seed(31337)
        while not ep.done:
            f = torch.randint(0, A.N_FARMER, (args.lanes, 2), generator=g)
            mK = torch.randint(1, A.N_MARKET, (args.lanes, 2, K), generator=g)
            if broken:
                mK = mK[..., :1].expand(-1, -1, K).contiguous()
                mK[..., 1:] = 0          # BROKEN: extra slots always NOOP
            ep.step_idx(f, mK)
    finally:
        X._idx_decode_market = orig
        engine_t.EpisodeT._idx_decode_market = orig
    if tally["destroyed"]:
        return False, f"O3: K>1 displaced {tally['destroyed']} existing orders"
    if tally["extra"] <= 0:
        return False, f"O3: K>1 added no orders (extra={tally['extra']})"
    return True, f"O3: K=3 added {tally['extra']} orders, displaced 0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lanes", type=int, default=6)
    ap.add_argument("--steps", type=int, default=120)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()
    ok = True
    for name, fn in (("O1", gate_o1), ("O2", gate_o2), ("O3", gate_o3)):
        try:
            good, msg = fn(args)
        except Exception as exc:                       # noqa: BLE001
            good, msg = False, f"{name}: raised {type(exc).__name__}: {exc}"
        print(("PASS " if good else "FAIL ") + msg)
        ok &= good
    try:
        good, msg = gate_o3(args, broken=True)
    except Exception as exc:                           # noqa: BLE001
        good, msg = False, str(exc)
    print(("FAIL O4: broken decode PASSED O3 -- the gate is not load-bearing"
           if good else f"PASS O4: broken decode fails O3 ({msg})"))
    ok &= not good
    print("ALL PASS" if ok else "GATES FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
