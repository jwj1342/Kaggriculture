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
a resumed link sees the marker and exits cleanly at once, so afterany
chains do not resurrect a stopped run and afterok evals still fire.
"""

import torch


def run_probe(actor_net, pool, args, device):
    """One deterministic episode batch vs the current stage anchor.

    Returns (win_rate, mean_margin) as python floats. Fixed base_seed and a
    fresh env per call => the identical seed set every probe (episode index
    restarts at 0); argmax policy => no sampling noise. Handicap 0 and no
    opponent noise: the probe measures the real frontier.
    """
    from trl_env import KGTensorEnv

    multi = bool(getattr(args, "multi_head", False))
    env = KGTensorEnv(
        args.probe_lanes, device=device, seat=0,
        episode_steps=args.steps, base_seed=args.seed + 991,
        opponent="starter", win_bonus=0.0,
        potential=args.potential, shape_scale=args.shape_scale,
        multi_head=multi)
    if pool is not None:
        env.opp_fn = pool.anchors[pool.stage][1]
    td = env.reset()
    with torch.no_grad():
        while True:
            x = td["observation"]
            outs = actor_net(x)
            fl, ml = outs[0], outs[1]
            fa = fl.masked_fill(~td["farmer_mask"], -1e9).argmax(-1)
            ma = ml.masked_fill(~td["market_mask"], -1e9).argmax(-1)
            if multi:
                ha = outs[2].masked_fill(~td["hand_mask"], -1e9).argmax(-1)
                td["action"] = torch.cat(
                    [fa.unsqueeze(-1), ma.unsqueeze(-1), ha], -1)
            else:
                td["action"] = torch.stack([fa, ma], -1)
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
                 delta_win=0.01, delta_margin=500.0):
        self.n_stages = int(n_stages)
        self.advance_at = float(advance_at)
        self.patience = int(patience)
        self.delta_win = float(delta_win)
        self.delta_margin = float(delta_margin)
        self._frontier = None            # (stage, handicap)
        self._best = None                # (win, margin) at this frontier
        self._flat = 0

    def update(self, stage, handicap, win, margin):
        if stage == self.n_stages - 1 and handicap == 0 \
                and win >= self.advance_at:
            return "curriculum-complete"
        frontier = (stage, handicap)
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
