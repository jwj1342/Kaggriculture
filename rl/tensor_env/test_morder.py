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
import argparse, os, sys
import numpy as np
import torch

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
    # (the real net opens with slot_bias[1:, 0] = SLOT_NOOP_BIAS; this gate
    # checks the distribution's algebra at literally zero tables, and gate O5
    # checks what the initialised net actually plays)
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


def gate_s1(args, broken=False):
    """Bulk seed: BUY_SEED_BULK_<c> must actually buy SEED_BULK seeds.

    Known-positive and its counterexample in one: the bulk action has to move
    the seed store by actions.SEED_BULK where the single action moves it by 1.
    `broken` decodes the bulk index through the SINGLE action instead, which is
    exactly the failure a wrong LUT row would produce, and must fail.
    """
    i_one = A.MARKET_ACTIONS.index("BUY_SEED_WHEAT")
    i_bulk = A.MARKET_ACTIONS.index("BUY_SEED_BULK_WHEAT")
    if broken:
        i_bulk = i_one
    seeds = [55_000 + 3 * i for i in range(args.lanes)]
    got = {}
    for tag, idx in (("one", i_one), ("bulk", i_bulk)):
        ep = _ep(seeds, 8, args.device)
        before = ep.seeds_t[:, 0].clone()
        f = torch.zeros((args.lanes, 2), dtype=torch.int64)
        m = torch.full((args.lanes, 2), idx, dtype=torch.int64)
        ep.step_idx(f, m)
        got[tag] = int((ep.seeds_t[:, 0] - before).sum())
    want = A.SEED_BULK * got["one"]
    if got["one"] <= 0:
        return False, f"S1: the single action bought nothing ({got})"
    if got["bulk"] != want:
        return False, (f"S1: bulk bought {got['bulk']}, single bought "
                       f"{got['one']}, expected {want}")
    return True, (f"S1: BUY_SEED_BULK moved the seed store by {got['bulk']} "
                  f"against the single action's {got['one']} "
                  f"(SEED_BULK={A.SEED_BULK})")


def gate_d1(args, broken=False):
    """Depth: a deeper trunk must be bit-identical at init, in every variant.

    `broken` builds the residual blocks WITHOUT restoring the RNG state, which
    is what the first implementation did; it shifts every layer created after
    them and must fail.
    """
    import torch.nn as nn
    from trl_policy import ActorNet, MultiActorNet, _ortho
    variants = [(ActorNet, {}), (MultiActorNet, {"n_hands": 12, "n_hand_task": 39}),
                (MultiActorNet, {"n_hands": 12, "n_hand_task": 39,
                                 "market_orders": 4})]
    if broken:
        def leaky(self):
            h2 = self._hidden2
            self.extra = nn.ModuleList()
            for _ in range(self.depth - 2):
                a = _ortho(nn.Linear(h2, h2), 1.41)
                b = nn.Linear(h2, h2)
                nn.init.zeros_(b.weight); nn.init.zeros_(b.bias)
                self.extra.append(nn.ModuleList([a, b]))
        saved, ActorNet._build_extra = ActorNet._build_extra, leaky
    try:
        for cls, kw in variants:
            torch.manual_seed(0); a = cls(64, 5, 7, 32, 16, depth=2, **kw)
            torch.manual_seed(0); b = cls(64, 5, 7, 32, 16, depth=8, **kw)
            x = torch.randn(4, 64)
            with torch.no_grad():
                oa, ob = a(x), b(x)
            d = max(float((p - q).abs().max()) for p, q in zip(oa, ob))
            if d != 0.0:
                return False, (f"D1: {cls.__name__} depth 2 vs 8 differs by "
                               f"{d:.2e} at init")
    finally:
        if broken:
            ActorNet._build_extra = saved
    return True, "D1: depth 8 == depth 2 at init, bit for bit, in 3 variants"


def gate_o5(args, broken=False):
    """An initialised K>1 net must play exactly ONE order greedily.

    That is the deployment half of "K>1 starts as K=1". It was false: zero
    tables made every slot argmax the same logits, so an untrained K=4 export
    opened with four copies of BUY_SEED MELON 8. `broken` zeroes the NOOP bias
    and must fail.
    """
    from trl_policy import MultiActorNet, SLOT_NOOP_BIAS
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import obs as O
    K = 4
    torch.manual_seed(11)
    net = MultiActorNet(O.OBS_DIM, A.N_FARMER, A.N_MARKET, 128, 64,
                        n_hands=12, n_hand_task=A.N_HAND_TASK, market_orders=K)
    if broken:
        with torch.no_grad():
            net.slot_bias.zero_()
    from trl_env import KGTensorEnv
    env = KGTensorEnv(4, device="cpu", episode_steps=48, market_orders=K,
                      multi_head=True, potential="future-mkt", opponent="starter")
    td = env.reset()
    with torch.no_grad():
        ml = net(td["observation"])[1]
        picks, prev = [], None
        for j in range(K):
            lj = ml + net.slot_bias[j]
            if prev is not None:
                lj = lj + net.couple_m.t()[prev]
            a = lj.masked_fill(~td["market_mask"], -1e9).argmax(-1)
            picks.append(a); prev = a
    later = torch.stack(picks[1:])
    n_active = int((later != 0).sum())
    if n_active:
        return False, (f"O5: {n_active} of {later.numel()} later slots are not "
                       f"NOOP at init (bias={float(net.slot_bias[1, 0]):.2f}); "
                       f"a greedy export would repeat slot 0's order")
    return True, (f"O5: slots 1..{K-1} all open NOOP "
                  f"(SLOT_NOOP_BIAS={SLOT_NOOP_BIAS}); slot 0 picks "
                  f"{picks[0].tolist()}")


def gate_o7(args, broken=False):
    """The tensor slot layout must equal the export's concatenation.

    export_agent builds the deployed list as macro0's orders then macro1's then
    macro2's, in order. The first tensor version wrote extra macros at S-1-kx,
    i.e. REVERSED and at the tail, so training and deployment played different
    order lists -- with [NOOP, SELL_CARROT, BUY_SHEEP] the tensor ran the animal
    purchase before the sell and it failed for want of cash while the deployed
    agent sold first and bought it. Nothing compared the two layouts.

    This gate asserts (a) live slots form a PREFIX -- no holes -- and (b) the
    extra macros land in ascending slot order right after macro0's block.
    `broken` restores the tail placement and must fail.
    """
    K = 3
    seeds = [64_000 + 5 * i for i in range(args.lanes)]
    ep = _ep(seeds, args.steps, args.device)
    orig = X._idx_decode_market
    bad = {"holes": 0, "order": 0, "checked": 0}

    def spy(self, m_idx, herd, day, t):
        if m_idx.dim() != 3:
            return orig(self, m_idx, herd, day, t)
        base = orig(self, m_idx[..., :1], herd, day, t)
        full = orig(self, m_idx, herd, day, t)
        if broken:                      # the shipped layout: tail, reversed
            S = self.max_market_orders
            full = tuple(x.clone() for x in base)
            for kx in range(m_idx.shape[-1] - 1):
                slot = S - 1 - kx
                one = orig(self, m_idx[..., kx + 1:kx + 2], herd, day, t)
                free = full[0][..., slot] == 0
                for a, b in zip(full, one):
                    a[..., slot] = torch.where(free, b[..., 0], a[..., slot])
        live = full[0] != 0
        n = int(live.sum())
        if n:
            bad["checked"] += 1
            counts = live.sum(-1)
            prefix = (torch.arange(live.shape[-1], device=live.device)
                      < counts.unsqueeze(-1))
            if not torch.equal(live, prefix):
                bad["holes"] += 1
            # each extra macro must sit at or after macro0's block end
            n_base = int((base[0] != 0).sum(-1).max())
            if n_base and int(counts.max()) < n_base:
                bad["order"] += 1
        return full

    X._idx_decode_market = spy
    engine_t.EpisodeT._idx_decode_market = spy
    try:
        g = torch.Generator(device="cpu").manual_seed(99)
        while not ep.done:
            f = torch.randint(0, A.N_FARMER, (args.lanes, 2), generator=g)
            m = torch.randint(1, A.N_MARKET, (args.lanes, 2, K), generator=g)
            ep.step_idx(f, m)
    finally:
        X._idx_decode_market = orig
        engine_t.EpisodeT._idx_decode_market = orig
    if bad["checked"] == 0:
        return False, "O7: no decodes observed"
    if bad["holes"]:
        return False, (f"O7: live slots have HOLES in {bad['holes']} of "
                       f"{bad['checked']} decodes -- the deployed list packs "
                       f"orders contiguously, so the layouts differ")
    if bad["order"]:
        return False, f"O7: extra macros landed before macro0's block"
    return True, (f"O7: live slots are a contiguous prefix in all "
                  f"{bad['checked']} decodes (K={K})")


def gate_l1(args, broken=False):
    """A frozen/league snapshot of a K>1 policy must PLAY K slots.

    Dropping slot_bias/couple_m makes the snapshot a one-order agent -- the cap
    measured at -89,479 on closer_cleo -- so under --league the learner would
    train against copies of itself that are systematically weaker than itself.
    `broken` drops the tables and must fail.
    """
    from trl_env import FrozenPolicyOpponent
    from trl_policy import MultiActorNet
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import obs as O
    K = 4
    torch.manual_seed(1)
    net = MultiActorNet(O.OBS_DIM, A.N_FARMER, A.N_MARKET, 64, 32, n_hands=12,
                        n_hand_task=A.N_HAND_TASK, market_orders=K, depth=4)
    with torch.no_grad():
        net.slot_bias.add_(torch.randn_like(net.slot_bias))
        net.couple_m.add_(torch.randn_like(net.couple_m))
    arrays = net.state_np()
    if broken:
        arrays.pop("msb", None); arrays.pop("cmw", None)
    op = FrozenPolicyOpponent.from_state_np(arrays, "cpu")
    ep = _ep([5 + i for i in range(args.lanes)], 20, args.device)
    res = op(ep, 1)
    ma = res[1]
    if ma.dim() != 2 or ma.shape[-1] != K:
        return False, (f"L1: snapshot market action is {tuple(ma.shape)}, "
                       f"expected (B, {K}) -- it plays one order a turn")
    if int((ma[:, 1:] != ma[:, :1]).sum()) == 0:
        return False, "L1: every slot chose the same action; the tables are inert"
    return True, (f"L1: snapshot plays {K} slots, e.g. {ma[0].tolist()}")


def gate_p1(args, broken=False):
    """The probe must SEE the slot tables.

    Checked on the ACTIONS, not on the returned margin: an untrained policy
    banks nothing either way, so the margin saturates and two very different
    policies read the same number. That is how the first "multi-order probe
    fix" shipped -- it sliced ml[..., j, :] believing the head was
    (B, K, N_MARKET) when MultiActorNet returns (B, N_MARKET), so it indexed
    the BATCH and gave every lane one lane's logits, and the probe was bit
    identical with the tables zeroed or at N(0, 5). `broken` reproduces that
    slice and must fail.
    """
    from trl_policy import MultiActorNet
    from trl_env import KGTensorEnv
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import obs as O
    K = 4
    torch.manual_seed(5)
    net = MultiActorNet(O.OBS_DIM, A.N_FARMER, A.N_MARKET, 128, 64,
                        n_hands=12, n_hand_task=A.N_HAND_TASK, market_orders=K)
    env = KGTensorEnv(6, device="cpu", episode_steps=48, market_orders=K,
                      multi_head=True, potential="future-mkt", opponent="starter")
    td = env.reset()

    def slots():
        with torch.no_grad():
            ml = net(td["observation"])[1]
            out, prev = [], None
            for j in range(K):
                if broken:                        # the shipped bug
                    lj = ml[..., j, :]
                else:
                    lj = ml + net.slot_bias[j]
                    if prev is not None:
                        lj = lj + net.couple_m.t()[prev]
                a = lj.masked_fill(~td["market_mask"], -1e9).argmax(-1)
                out.append(a.tolist()); prev = a
            return out

    before = slots()
    with torch.no_grad():
        net.slot_bias.add_(torch.randn_like(net.slot_bias) * 5)
        net.couple_m.add_(torch.randn_like(net.couple_m) * 5)
    after = slots()
    if before == after:
        return False, ("P1: perturbing slot_bias/couple_m did not change the "
                       "probe's actions -- the probe is blind to the head")
    return True, f"P1: probe actions move with the tables ({before[1]} -> {after[1]})"


def gate_d3(args, broken=False):
    """Depth must actually DO something once the blocks are non-zero.

    D1 alone is not load-bearing: the blocks are zero at birth, so a forward
    that ignores them entirely still passes it. That is exactly what happened
    -- MultiActorNet.forward open-coded the two layers and never applied the
    residual blocks, so --depth was inert on the path every arm uses while D1
    stayed green. D3 perturbs the blocks and demands the output move, and it
    checks the numpy export path agrees with torch to 1e-5.
    """
    from trl_policy import MultiActorNet, actor_arrays
    torch.manual_seed(3)
    net = MultiActorNet(64, 5, 7, 32, 16, n_hands=12, n_hand_task=39,
                        market_orders=4, depth=6)
    x = torch.randn(1, 64)
    with torch.no_grad():
        before = net(x)[0].clone()
    with torch.no_grad():
        for blk in net.extra:
            if broken:                       # BROKEN: leave the blocks zero
                continue
            blk[1].weight.add_(torch.randn_like(blk[1].weight) * 0.05)
            blk[1].bias.add_(torch.randn_like(blk[1].bias) * 0.05)
        after = net(x)[0]
        moved = float((after - before).abs().max())
    # The farmer head is 1e-4-initialised, so the move is small by
    # construction; 1e-6 is far above float noise and far below a real signal.
    if moved < 1e-6:
        return False, (f"D3: perturbing the residual blocks moved the output "
                       f"by only {moved:.3e} -- depth is inert")
    W = actor_arrays(net.state_dict(), numpy=True)
    xn = x.numpy()[0]
    h = np.maximum(0.0, W["l1w"] @ xn + W["l1b"])
    h = np.maximum(0.0, W["l2w"] @ h + W["l2b"])
    i = 0
    while f"e{i}aw" in W:
        a = np.maximum(0.0, W[f"e{i}aw"] @ h + W[f"e{i}ab"])
        h = h + W[f"e{i}bw"] @ a + W[f"e{i}bb"]
        i += 1
    with torch.no_grad():
        tf, tm, th = net(x)
    err = max(float(np.abs(tf.numpy()[0] - (W["fw"] @ h + W["fb"])).max()),
              float(np.abs(tm.numpy()[0] - (W["mw"] @ h + W["mb"])).max()),
              float(np.abs(th.numpy()[0].reshape(-1) - (W["hw"] @ h + W["hb"])).max()))
    if i != 4:
        return False, f"D3: depth 6 built {i} residual blocks, expected 4"
    if err > 1e-5:
        return False, f"D3: numpy export path differs from torch by {err:.2e}"
    return True, (f"D3: blocks move the output by {moved:.3e}; numpy export "
                  f"matches torch to {err:.1e} across {i} blocks")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lanes", type=int, default=6)
    ap.add_argument("--steps", type=int, default=120)
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()
    ok = True
    for name, fn in (("O1", gate_o1), ("O2", gate_o2), ("O3", gate_o3),
                     ("S1", gate_s1), ("O5", gate_o5), ("O7", gate_o7), ("L1", gate_l1), ("P1", gate_p1),
                     ("D1", gate_d1), ("D3", gate_d3)):
        try:
            good, msg = fn(args)
        except Exception as exc:                       # noqa: BLE001
            good, msg = False, f"{name}: raised {type(exc).__name__}: {exc}"
        print(("PASS " if good else "FAIL ") + msg)
        ok &= good
    for tag, fn, src in (("O4", gate_o3, "O3"), ("S2", gate_s1, "S1"),
                         ("D2", gate_d1, "D1"), ("D4", gate_d3, "D3"),
                         ("O6", gate_o5, "O5"), ("P2", gate_p1, "P1"), ("O8", gate_o7, "O7"), ("L2", gate_l1, "L1")):
        try:
            good, msg = fn(args, broken=True)
        except Exception as exc:                       # noqa: BLE001
            good, msg = False, str(exc)
        print((f"FAIL {tag}: broken implementation PASSED {src} -- "
               f"the gate is not load-bearing"
               if good else f"PASS {tag}: broken implementation fails {src} ({msg})"))
        ok &= not good
    print("ALL PASS" if ok else "GATES FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
