"""Deterministic fixed-field probes + the early stopper they feed.

Per-iteration batch win rates oscillate with the opponent pool's sampling
(0.00 on a barnyard batch, 1.00 on a starter batch), so plateau detection
on the training curve misfires by construction. The probe is the proper
validation analog: every N iterations, play a FIXED seed set with the
ARGMAX policy against the current curriculum anchor at zero handicap --
same seeds every probe, deterministic policy, so consecutive probes are
paired measurements and "no improvement" means exactly that.

EarlyStopper is pure logic over probe results (unit-tested in
test_trl.py gate ix). Three triggers, in the order they are checked:

  curriculum-complete  last stage, handicap 0, probe win >= the advance
                       gate: the run achieved its curriculum; further
                       iterations only deepen the self-play basin
                       (the foothold result, docs/RUNS.md 2026-08-19).
  stagnated            `patience` consecutive probes at the SAME frontier
                       (stage and handicap unchanged) improving neither
                       probe win (by >= delta_win) nor probe margin (by >=
                       delta_margin) over the frontier's best. Both metrics
                       must be flat: at a 0%-win wall a shrinking loss
                       margin IS learning and must not stop the run.
  (peak staleness folds into `stagnated`: the frontier best not moving for
  `patience` probes is exactly a stale peak, measured deterministically.)

Chain safety: the trainer writes {"stopped": reason} into the checkpoint;
a resumed link sees the marker and exits cleanly at once. New training chains
use `afterok` through tools/submit_rl.py; a stale queued link therefore cannot
resume model updates after an early-stop marker.
"""

import torch


def _probe_opponent(pool, args):
    """Use the configured single opponent; pools replace this after init.

    --probe-vs pins it instead: a curriculum probe measures against the CURRENT
    stage anchor, so the yardstick moves every time the pool advances and two
    probes from different stages are not comparable. Pinning one fixed
    opponent -- normally a mined tape -- makes the whole run one paired series
    against the same field, which is what "is it losing less money" needs.
    """
    pinned = getattr(args, "probe_vs", "")
    if pinned:
        return pinned
    return "starter" if pool is not None else getattr(args, "opponent", "starter")


def run_probe(actor_net, pool, args, device):
    """One deterministic episode batch vs the current stage anchor.

    Returns (win_rate, mean_margin) as python floats. Fixed base_seed and a
    fresh env per call => the identical seed set every probe (episode index
    restarts at 0); argmax policy => no sampling noise. Handicap 0 and no
    opponent noise: the probe measures the real frontier.
    """
    from trl_env import KGTensorEnv

    multi = bool(getattr(args, "multi_head", False))
    k_mkt = max(1, int(getattr(args, "market_orders", 1)))
    seat = getattr(args, "seat", 0)
    seat = 0 if seat == "alt" else int(seat)
    qty_head = bool(getattr(args, "qty_head", False))
    env = KGTensorEnv(
        args.probe_lanes, device=device, seat=seat, market_orders=k_mkt,
        qty_head=qty_head,
        episode_steps=args.steps, base_seed=args.seed + 991,
        opponent=_probe_opponent(pool, args), win_bonus=0.0,
        potential=args.potential, shape_scale=args.shape_scale,
        multi_head=multi,
        fixed_market_profile=getattr(args, "fixed_market_profile", ""),
        # The graft has to be forwarded or the probe measures a policy that
        # does not exist. Under --fixed-farm-tape the farmer and hand heads
        # are overridden in training and receive no objective, so an
        # UNGRAFTED probe env argmaxes them anyway and reads "an untrained
        # farm plus the trained market head" -- and that reading then drives
        # EarlyStopper and the best.pt ratchet. Gate: test_trl.py
        # gate_probe_graft.
        fixed_farm_tape=getattr(args, "fixed_farm_tape", ""),
        farm_tape_market=getattr(args, "farm_tape_market", "buys"))
    if pool is not None and not getattr(args, "probe_vs", ""):
        env.opp_fn = pool.anchors[pool.stage][1]
    td = env.reset()
    with torch.no_grad():
        while True:
            x = td["observation"]
            outs = actor_net(x)
            fl, ml = outs[0], outs[1]
            fa = fl.masked_fill(~td["farmer_mask"], -1e9).argmax(-1)
            # The K slots do NOT live in the net: MultiActorNet.forward
            # returns (B, N_MARKET) and the slots come from the DISTRIBUTION's
            # slot_bias / couple_m. An earlier version here sliced ml[..., j, :]
            # believing the head was (B, K, N_MARKET); that indexed the BATCH,
            # gave every lane one lane's logits, and made the probe bit-identical
            # whether the tables were zero or N(0, 5) -- i.e. blind to the whole
            # feature it was meant to measure, while still driving EarlyStopper
            # and the best.pt ratchet. Reproduce MultiOrderMultiHead.mode here.
            # --couple-heads conditions the market head on THIS turn's farmer
            # action and hand tasks. Applying slot_bias/couple_m but not these
            # is the same blindness one table pair over: the probe would argmax
            # the base logits while the played policy argmaxes the conditional.
            if getattr(actor_net, "couple_f", None) is not None:
                ml = ml + actor_net.couple_f.t()[fa]
                if multi:
                    ml = ml + actor_net.couple_h.t()[
                        outs[2].masked_fill(~td["hand_mask"], -1e9).argmax(-1)
                    ].mean(-2)
            ql = outs[3] if qty_head and len(outs) > 3 else None
            mcols, qcols, prev = [], [], None
            for j in range(k_mkt):
                lj = ml
                if k_mkt > 1 or qty_head:
                    lj = lj + actor_net.slot_bias[j]
                    if prev is not None:
                        lj = lj + actor_net.couple_m.t()[prev]
                aj = lj.masked_fill(~td["market_mask"], -1e9).argmax(-1)
                mcols.append(aj.unsqueeze(-1))
                if ql is not None:
                    # The rung head is the same blindness one table over: a
                    # probe that skipped it would drive EarlyStopper and the
                    # best.pt ratchet from a policy that is never played.
                    qj = (ql[..., j, :] + actor_net.couple_q.t()[aj]).argmax(-1)
                    qcols.append(qj.unsqueeze(-1))
                prev = aj
            if multi:
                ha = outs[2].masked_fill(~td["hand_mask"], -1e9).argmax(-1)
                td["action"] = torch.cat(
                    [fa.unsqueeze(-1)] + mcols + qcols + [ha], -1)
            else:
                td["action"] = torch.cat(
                    [fa.unsqueeze(-1)] + mcols + qcols, -1)
            td = env.step(td)
            if bool(td["next", "done"].all()):
                break
            td = td["next"].exclude("reward")
    money = td["next", "money"]
    omoney = td["next", "opp_money"]
    win = ((money > omoney).double().mean()
           + 0.5 * (money == omoney).double().mean()).item()
    margin = (money - omoney).mean().item()
    return win, margin


class EarlyStopper:
    """Feed (stage, handicap, win, margin) per probe; returns a stop reason
    string or None. Pure state machine -- no tensors, no I/O."""

    def __init__(self, n_stages, advance_at, patience=6,
                 delta_win=0.01, delta_margin=500.0, pinned=False):
        # pinned: the probe measures a FIXED opponent (--probe-vs) rather than
        # the stage anchor, which disables curriculum-complete and keeps the
        # stagnation frontier continuous across advances -- the whole point of
        # pinning is that the series IS comparable across stages.
        self.pinned = bool(pinned)
        self.n_stages = int(n_stages)
        self.advance_at = float(advance_at)
        self.patience = int(patience)
        self.delta_win = float(delta_win)
        self.delta_margin = float(delta_margin)
        self._frontier = None            # (stage, handicap)
        self._best = None                # (win, margin) at this frontier
        self._flat = 0

    def update(self, stage, handicap, win, margin):
        # A pinned probe says nothing about having beaten the curriculum:
        # measured, this stopped a run at iteration 1 with a batch win of 0.000
        # and money 1 against 2,940, because an argmax policy that does nothing
        # keeps its starting capital while `starter` spends 60 of its own.
        if (not self.pinned) and stage == self.n_stages - 1 and handicap == 0 \
                and win >= self.advance_at:
            return "curriculum-complete"
        # A pinned series is one frontier: advancing the pool must not reset
        # the stagnation clock, or the paired series restarts on every advance.
        frontier = (0, 0) if self.pinned else (stage, handicap)
        if frontier != self._frontier:   # new frontier resets the clock
            self._frontier = frontier
            self._best = (win, margin)
            self._flat = 0
            return None
        bw, bm = self._best
        improved = False
        if win >= bw + self.delta_win:
            bw, improved = win, True
        if margin >= bm + self.delta_margin:
            bm, improved = margin, True
        self._best = (bw, bm)
        self._flat = 0 if improved else self._flat + 1
        if self._flat >= self.patience:
            return "stagnated"
        return None

    def state(self):
        return {"frontier": self._frontier, "best": self._best,
                "flat": self._flat}

    def load_state(self, st):
        fr = st.get("frontier")
        self._frontier = tuple(fr) if fr is not None else None
        bs = st.get("best")
        self._best = tuple(bs) if bs is not None else None
        self._flat = int(st.get("flat", 0))
