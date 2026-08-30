#!/usr/bin/env python
"""Gates for CoupledMultiHeadMasked (the joint farm+market intervention).

Why this design exists (docs/RUNS.md 28da6ef): the farm x market interaction
measured +68,972 while swapping either side alone measured NEGATIVE, so a
policy whose heads are independent given the state cannot represent the
coordination the gap consists of. The coupling conditions the market head on
the same turn's sampled farmer/hand intents through zero-initialised tables.

What each gate protects against, all failure modes this repository has paid
for at least once:

  G1  zero-coupling identity. All-zero tables must make log_prob, entropy and
      mode BIT-IDENTICAL to MultiHeadMasked. This is what makes legacy warm
      starts valid and the iter-0 deterministic lane gate usable. A near-miss
      here (float noise) silently invalidates every lane comparison.
  G2  the coupling bites, and ONLY where it should. Non-zero tables must move
      the market mode on some states while leaving the farmer/hand modes
      byte-identical -- a plumbed-but-inert knob reads as "measured and
      refuted" (test_profile_knobs' lesson), and a knob that leaks into other
      heads confounds every downstream attribution.
  G3  gradients reach the tables through log_prob. The parameters arrive in
      the distribution as CLASS attributes (build_actor_critic binds a
      per-build subclass), which autograd must not care about -- asserted,
      not assumed.
  G4  the export contract carries the coupling. state_np -> numpy forward
      (the export template's math, replicated here operation for operation)
      must reproduce the torch mode exactly, and the actor_arrays /
      arrays_to_sd round trip must keep cfw/chw. Dropping them would make a
      deployed or league-snapshot copy silently play the UNCOUPLED base
      policy -- the loads-the-unwrapped-agent failure mode, one layer down.
  G5  legacy tolerance. A checkpoint WITHOUT coupling keys must load into a
      coupled net (strict=False path) and leave the tables at zero.

Engine-free on purpose: random logits and masks, so it runs in seconds on a
login node and gates every commit that touches the policy stack.
"""

import sys

import numpy as np
import torch

import trl_policy as P


def _case(B=64, nf=23, nm=31, H=12, T=39, seed=0):
    g = torch.Generator().manual_seed(seed)
    fl = torch.randn(B, nf, generator=g)
    ml = torch.randn(B, nm, generator=g)
    hl = torch.randn(B, H, T, generator=g)
    fm = torch.rand(B, nf, generator=g) < 0.7
    mm = torch.rand(B, nm, generator=g) < 0.7
    hm = torch.rand(B, H, T, generator=g) < 0.7
    fm[:, 0] = True
    mm[:, 0] = True
    hm[:, :, 0] = True   # at least one legal entry per row
    return fl, ml, hl, fm, mm, hm


def _bound(cf, ch):
    return type("CoupledBound", (P.CoupledMultiHeadMasked,),
                {"couple_f": cf, "couple_h": ch})


def main():
    B, nf, nm, H, T = 64, 23, 31, 12, 39
    fl, ml, hl, fm, mm, hm = _case(B, nf, nm, H, T)
    base = P.MultiHeadMasked(fl, ml, hl, fm, mm, hm)

    # ---- G1: zero coupling is bit-identical to the factored policy --------
    zero = _bound(torch.zeros(nm, nf), torch.zeros(nm, T))(
        fl, ml, hl, fm, mm, hm)
    act = base.mode
    if not torch.equal(zero.mode, base.mode):
        print("G1 FAIL: mode differs at zero coupling")
        print("COUPLE-FAIL")
        return 1
    for name, a, b in (("log_prob", zero.log_prob(act), base.log_prob(act)),
                       ("entropy", zero.entropy(), base.entropy())):
        if not torch.equal(a, b):
            print(f"G1 FAIL: {name} differs at zero coupling "
                  f"(max |d| {(a - b).abs().max():.3e})")
            print("COUPLE-FAIL")
            return 1
    print("  G1 zero coupling == MultiHeadMasked, bit-identical "
          "(mode / log_prob / entropy)")

    # ---- G2: the coupling bites, and only the market column moves ---------
    g = torch.Generator().manual_seed(7)
    cf = torch.randn(nm, nf, generator=g)
    ch = torch.randn(nm, T, generator=g)
    hot = _bound(cf, ch)(fl, ml, hl, fm, mm, hm)
    dm, db = hot.mode, base.mode
    moved = int((dm[:, 1] != db[:, 1]).sum())
    if moved == 0:
        print("G2 FAIL: non-zero coupling never moves the market mode -- "
              "plumbed but inert")
        print("COUPLE-FAIL")
        return 1
    if not (torch.equal(dm[:, 0], db[:, 0])
            and torch.equal(dm[:, 2:], db[:, 2:])):
        print("G2 FAIL: coupling leaked into the farmer/hand modes")
        print("COUPLE-FAIL")
        return 1
    print(f"  G2 coupling bites: market mode moves on {moved}/{B} states, "
          f"farmer/hand modes untouched")

    # ---- G3: gradients reach the tables through log_prob ------------------
    cf_p = torch.nn.Parameter(cf.clone())
    ch_p = torch.nn.Parameter(ch.clone())
    dist = _bound(cf_p, ch_p)(fl, ml, hl, fm, mm, hm)
    dist.log_prob(act).sum().backward()
    for name, p in (("couple_f", cf_p), ("couple_h", ch_p)):
        if p.grad is None or not torch.isfinite(p.grad).all() \
                or float(p.grad.abs().max()) == 0.0:
            print(f"G3 FAIL: no finite non-zero gradient reached {name}")
            print("COUPLE-FAIL")
            return 1
    print("  G3 finite non-zero gradients reach both coupling tables "
          "through log_prob")

    # ---- G4: export contract (numpy forward == torch mode; arrays keep) ---
    torch.manual_seed(11)
    net = P.MultiActorNet(obs_dim=97, n_farmer=nf, n_market=nm, hidden1=32,
                          hidden2=16, n_hands=H, n_hand_task=T, couple=True)
    with torch.no_grad():
        net.couple_f.copy_(cf)
        net.couple_h.copy_(ch)
    W = net.state_np()
    for k in ("cfw", "chw"):
        if k not in W:
            print(f"G4 FAIL: state_np dropped {k}")
            print("COUPLE-FAIL")
            return 1
    sd = P.arrays_to_sd(P.actor_arrays(
        {**net.state_dict()}, numpy=True))
    if "couple_f" not in sd or "couple_h" not in sd:
        print("G4 FAIL: actor_arrays/arrays_to_sd round trip dropped the "
              "coupling tables")
        print("COUPLE-FAIL")
        return 1
    x = torch.randn(B, 97)
    tfl, tml, thl = net(x)
    dist = _bound(net.couple_f, net.couple_h)(tfl, tml, thl, fm, mm, hm)
    tmode = dist.mode

    # G4a -- the CONDITIONING math itself, on SHARED logits, must be exact.
    # Feeding the torch-computed base logits into the numpy template isolates
    # the coupling arithmetic (what this gate is about) from cross-backend
    # matmul accumulation noise in the MLP, which is a different contract
    # (export_agent's own verification replays a full episode for that).
    f = tfl.detach().numpy().copy()
    m0 = tml.detach().numpy().copy()
    hlg = thl.detach().numpy().copy()
    f[~fm.numpy()] = -1e9
    hlg[~hm.numpy()] = -1e9
    fa = f.argmax(-1)
    tasks = hlg.argmax(-1)
    m = m0 + W["cfw"][:, fa].T + W["chw"][:, tasks].mean(axis=-1).T
    m[~mm.numpy()] = -1e9
    # Bit-exactness across torch/numpy is unattainable even on shared logits:
    # .mean over the 12 hand intents accumulates in a different order, worth
    # ~2e-7 in float32 (measured). The SEMANTIC contract is therefore two
    # checks: the conditioned logits agree to well below any decision-relevant
    # scale, and any argmax flip sits on a top-2 gap inside that noise band.
    t_cond = (tml + net.couple_f.t()[torch.as_tensor(fa)]
              + net.couple_h.t()[torch.as_tensor(tasks)].mean(-2))
    t_cond = t_cond.masked_fill(~mm, -1e9).detach().numpy()
    dev = float(np.abs(np.where(mm.numpy(), m - t_cond, 0.0)).max())
    if dev > 1e-5:
        print(f"G4a FAIL: conditioned logits deviate by {dev:.2e} (> 1e-5) "
              f"on shared inputs -- template math error, not float noise")
        print("COUPLE-FAIL")
        return 1
    ma = m.argmax(-1)
    tnp = tmode.numpy()
    # Attribute flips per column. An INTENT flip (farmer or hand) must sit on
    # a near-tie in ITS OWN head -- log_softmax subtracts one constant per
    # row, which cannot invert a strict order but CAN round two near-equal
    # float32 logits into an exact tie, flipping that head's argmax. A market
    # flip is then either carried by a flipped intent (a different coupling
    # row, arbitrarily large market gap -- legitimate) or must itself sit on
    # a near-tie of the conditioned logits.
    def _gap(logits, mask):
        z = np.where(mask, logits, -np.inf)
        s = np.sort(z, -1)
        return s[..., -1] - s[..., -2]
    intent_flip = (fa != tnp[:, 0]) | (tasks != tnp[:, 2:]).any(-1)
    if intent_flip.any():
        gf = _gap(f, fm.numpy())[fa != tnp[:, 0]]
        gh = _gap(hlg, hm.numpy())[tasks != tnp[:, 2:]]
        worst = max([g.max() for g in (gf, gh) if g.size], default=0.0)
        if float(worst) > 1e-5:
            print(f"G4a FAIL: an intent argmax flip sits on a clear margin "
                  f"in its own head (top-2 gap {float(worst):.2e})")
            print("COUPLE-FAIL")
            return 1
    m_flip = (ma != tnp[:, 1]) & ~intent_flip
    if m_flip.any():
        gm = _gap(t_cond, mm.numpy())[m_flip]
        if float(gm.max()) > 1e-5:
            print(f"G4a FAIL: a market argmax flip with AGREEING intents "
                  f"sits on a clear margin (top-2 gap {float(gm.max()):.2e})")
            print("COUPLE-FAIL")
            return 1
    n_flip = int(((np.concatenate([fa[:, None], ma[:, None], tasks], -1)
                   != tnp).any(-1)).sum())
    print(f"  G4a coupling math == torch on shared logits (max dev "
          f"{dev:.1e} <= 1e-5); {n_flip}/{B} mode flips, every one "
          f"attributed to a float32 tie in its own head; round trip "
          f"keeps cfw/chw")

    # G4b -- the full numpy forward may differ from torch only within float
    # noise: logits close, and any mode flip must sit on a near-tie. A flip
    # on a CLEAR margin would mean the template math is wrong, not the
    # backend.
    xn = x.numpy()
    h = np.maximum(0.0, xn @ W["l1w"].T + W["l1b"])
    h = np.maximum(0.0, h @ W["l2w"].T + W["l2b"])
    fn = h @ W["fw"].T + W["fb"]
    mn = h @ W["mw"].T + W["mb"]
    hn = (h @ W["hw"].T + W["hb"]).reshape(B, H, T)
    for name, a, b in (("flogits", fn, tfl), ("mlogits", mn, tml),
                       ("hlogits", hn, thl)):
        d = float(np.abs(a - b.detach().numpy()).max())
        if d > 1e-4:
            print(f"G4b FAIL: numpy {name} deviate from torch by {d:.2e} "
                  f"(> 1e-4) -- template math error, not float noise")
            print("COUPLE-FAIL")
            return 1
    fn2 = fn.copy(); fn2[~fm.numpy()] = -1e9
    hn2 = hn.copy(); hn2[~hm.numpy()] = -1e9
    fa2, tasks2 = fn2.argmax(-1), hn2.argmax(-1)
    mn2 = mn + W["cfw"][:, fa2].T + W["chw"][:, tasks2].mean(axis=-1).T
    mn2[~mm.numpy()] = -1e9
    ma2 = mn2.argmax(-1)
    # Same per-column attribution as G4a, with the wider 1e-3 tie band the
    # full-forward's accumulated float noise calls for: an intent flip must
    # sit on a near-tie in ITS OWN head; a market flip with agreeing intents
    # must sit on a near-tie of the conditioned logits; a market flip CARRIED
    # by a flipped intent used a different coupling row and is legitimate.
    intent2 = (fa2 != tnp[:, 0]) | (tasks2 != tnp[:, 2:]).any(-1)
    if intent2.any():
        gf = _gap(fn, fm.numpy())[fa2 != tnp[:, 0]]
        gh = _gap(hn, hm.numpy())[tasks2 != tnp[:, 2:]]
        worst = max([g.max() for g in (gf, gh) if g.size], default=0.0)
        if float(worst) > 1e-3:
            print(f"G4b FAIL: an intent flip sits on a clear margin in its "
                  f"own head (top-2 gap {float(worst):.2e} > 1e-3)")
            print("COUPLE-FAIL")
            return 1
    m2 = (ma2 != tnp[:, 1]) & ~intent2
    if m2.any():
        gm = _gap(t_cond, mm.numpy())[m2]
        if float(gm.max()) > 1e-3:
            print(f"G4b FAIL: a market flip with agreeing intents sits on a "
                  f"clear margin (top-2 gap {float(gm.max()):.2e} > 1e-3)")
            print("COUPLE-FAIL")
            return 1
    n_flip = int(((np.concatenate([fa2[:, None], ma2[:, None], tasks2], -1)
                   != tnp).any(-1)).sum())
    print(f"  G4b full numpy forward: logits within 1e-4 of torch; "
          f"{n_flip}/{B} mode flips, every one attributed to a float tie "
          f"in its own head (cross-backend property, documented)")

    # ---- G5: a legacy checkpoint leaves the tables at zero ----------------
    torch.manual_seed(13)
    plain = P.MultiActorNet(obs_dim=97, n_farmer=nf, n_market=nm, hidden1=32,
                            hidden2=16, n_hands=H, n_hand_task=T)
    critic = P.CriticNet(97, 16)
    legacy = {**plain.state_dict(), **critic.state_dict()}
    torch.manual_seed(17)
    coupled = P.MultiActorNet(obs_dim=97, n_farmer=nf, n_market=nm, hidden1=32,
                              hidden2=16, n_hands=H, n_hand_task=T,
                              couple=True)
    P.load_merged_state_dict(coupled, P.CriticNet(97, 16), legacy)
    if float(coupled.couple_f.detach().abs().max()) != 0.0 \
            or float(coupled.couple_h.detach().abs().max()) != 0.0:
        print("G5 FAIL: loading a legacy checkpoint disturbed the zero "
              "coupling tables")
        print("COUPLE-FAIL")
        return 1
    if not torch.equal(coupled.market.weight, plain.market.weight):
        print("G5 FAIL: legacy market head did not load into the coupled net")
        print("COUPLE-FAIL")
        return 1
    print("  G5 legacy checkpoint loads (strict=False path), coupling "
          "tables stay zero")

    print("COUPLE-GATE-DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
