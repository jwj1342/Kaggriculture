"""On-device opponent pool: rl/league.py + rl/legacy/train_ppo.py's curriculum
ported to the tensor path (the "league-lite" the unified trainer samples from).

What is kept from the old line, coefficient for coefficient:
  * ordered anchor stages with a rolling-win advance gate (default 0.85 EMA,
    train_ppo's `advance_at`);
  * after advancing, the current stage keeps 0.5 of the sampling mass and
    everything earlier shares the rest (train_ppo's 50/50);
  * with --league, self-snapshots take 0.25 and earlier anchors 0.25
    (league.py's MIX_MIRROR/MIX_HISTORY/MIX_ANCHOR = 0.25/0.25/0.50 -- mirror
    had been downgraded from 0.40 after it inflated the rolling win while
    ghost skill fell; the latest snapshot plays the mirror role here).

What is deliberately simpler (documented deviations, revisit when they bite):
  * one opponent per episode BATCH (sampled at env reset), not per lane --
    the iteration is the natural unit on the tensor path;
  * snapshots are periodic + capped (drop oldest) instead of gate-promoted
    with fingerprint dedup; win EMAs are tracked per entry either way;
  * anchors must be tensor-representable: "starter" or exported weights
    (npz / checkpoint). Scripted python agents (barnyard, ghosts) are NOT --
    they stay in the kaggle-env world (rl/league.py, slurm/rl_eval.sh) until
    someone tensorises them. This is the known boundary, listed in rl/TODO.md.

Attribution is a FIFO: the collector auto-resets (and therefore samples the
NEXT batch's opponent) before the current batch is yielded, so record() pops
the oldest pending entry rather than trusting "last sampled".
"""

import collections
import os
import random

import numpy as np
import torch


def _spec_name(spec):
    base = os.path.basename(spec.split(":", 1)[-1])
    return base or spec


class OpponentPool:
    def __init__(self, specs, device, advance_at=0.85, ema=0.2, min_records=3,
                 league=False, max_snapshots=8, snapshot_dir="", seed=0,
                 handicap=0, pfsp=0.0, pfsp_mode="hard"):
        from trl_env import _make_opponent
        self.device = device
        self.anchors = [(_spec_name(s), _make_opponent(s, device)) for s in specs]
        self.stage = 0
        # pfsp > 0: inside each mix category, weight entries by
        # (1 - ema_win)^pfsp instead of uniformly (AlphaStar's f_hard) --
        # dominated snapshots/anchors drain out of the sampling mass instead
        # of owning the reward hill (the foothold/breach failure). A 0.1
        # uniform floor keeps every entry occasionally visited so the EMA
        # stays live (the 15% "forgotten players" slice, miniaturised).
        self.pfsp = float(pfsp)
        if pfsp_mode not in ("hard", "var"):
            raise ValueError(f"pfsp_mode must be hard|var, got {pfsp_mode!r}")
        self.pfsp_mode = pfsp_mode
        # handicap ladder: each stage opens with `handicap` extra starting
        # money for the learner; the win gate first steps the handicap down
        # (halving, zero below 200) and only advances the stage at zero --
        # "learn to beat the enemy while advantaged, then remove the crutch"
        self.handicap0 = self.handicap = int(handicap)
        self.advance_at = float(advance_at)
        self.ema = float(ema)
        self.min_records = int(min_records)
        self.league = bool(league)
        self.max_snapshots = int(max_snapshots)
        self.snapshot_dir = snapshot_dir
        self.wins = {}     # name -> EMA win rate
        self.counts = collections.Counter()
        self.snapshots = []  # (name, fn), oldest first
        self._pending = collections.deque()
        self._rng = random.Random(seed * 9176 + 11)

    # -- sampling ------------------------------------------------------------

    def _mix(self):
        """(category, entries, mass) list for the current stage."""
        cur = [self.anchors[self.stage]]
        earlier = self.anchors[:self.stage]
        snaps = self.snapshots if self.league else []
        out = [("current", cur, 0.5)]
        if earlier and snaps:
            out += [("earlier", earlier, 0.25), ("snap", snaps, 0.25)]
        elif earlier:
            out += [("earlier", earlier, 0.5)]
        elif snaps:
            out += [("snap", snaps, 0.5)]
        else:
            out = [("current", cur, 1.0)]
        return out

    def sample(self):
        """Pick an opponent fn for the next episode batch (env reset hook)."""
        cats = self._mix()
        r = self._rng.random() * sum(m for _, _, m in cats)
        for _, entries, mass in cats:
            if r < mass:
                name, fn = self._pick(entries)
                break
            r -= mass
        self._pending.append(name)
        return fn

    def _pick(self, entries):
        """Uniform inside a category, or PFSP-weighted when pfsp > 0.

        Two weightings, and the choice matters more than the exponent:

        `hard` (default, unchanged) is AlphaStar's f_hard,
        `0.1 + (1 - ema_win)**pfsp` -- mass goes to whoever beats us hardest.

        `var` is the variance form `ema*(1 - ema) + eps` that rl/league.py:149
        already implements, maximal at ema = 0.5 -- mass goes to whoever is
        CLOSEST TO PARITY. That is the objective the 2026-09-03 localisation
        argues for: of 3,840 paired cells, 508 are losses within 20,000 of
        parity and 78.5% of those sit on four opponents at median -11,134 to
        -23,692, while the seven walls at -35,778 to -46,161 hold almost none.
        f_hard pushes compute at those walls, i.e. exactly the wrong way, and
        no amount of margin there buys a game.

        In `var` mode the `pfsp` value is only an on-switch; the exponent is
        not applied, so this reproduces league.py's form rather than inventing
        an untested knob. The build logs which mode is live.
        """
        if self.pfsp <= 0.0 or len(entries) == 1:
            return entries[self._rng.randrange(len(entries))]
        if self.pfsp_mode == "var":
            eps = 0.05                      # league.py's PFSP_EPS
            ws = [self.wins.get(n, 0.0) * (1.0 - self.wins.get(n, 0.0)) + eps
                  for n, _ in entries]
        else:
            floor = 0.1
            ws = [floor + (1.0 - self.wins.get(n, 0.0)) ** self.pfsp
                  for n, _ in entries]
        r = self._rng.random() * sum(ws)
        for (name, fn), w in zip(entries, ws):
            if r < w:
                return name, fn
            r -= w
        return entries[-1]

    # -- outcome accounting ----------------------------------------------------

    def record(self, win):
        """Attribute a finished batch's win rate; returns "advanced" on a
        curriculum stage change, else None."""
        if not self._pending:
            return None
        name = self._pending.popleft()
        prev = self.wins.get(name)
        self.wins[name] = win if prev is None else (1 - self.ema) * prev + self.ema * win
        self.counts[name] += 1
        cur_name = self.anchors[self.stage][0]
        if (name == cur_name and self.counts[name] >= self.min_records
                and self.wins[name] >= self.advance_at):
            if self.handicap > 0:
                self.handicap = self.handicap // 2 if self.handicap >= 400 else 0
                self.counts[name] = 0  # re-earn the gate at the new handicap
                return "handicap"
            if self.stage + 1 < len(self.anchors):
                self.stage += 1
                self.handicap = self.handicap0
                return "advanced"
        return None

    # -- self-play snapshots ---------------------------------------------------

    def add_snapshot(self, actor_net, tag):
        from trl_env import FrozenPolicyOpponent
        arrays = actor_net.state_np()
        if self.snapshot_dir:
            os.makedirs(self.snapshot_dir, exist_ok=True)
            np.savez(os.path.join(self.snapshot_dir, f"{tag}.npz"), **arrays)
        fn = FrozenPolicyOpponent.from_state_np(arrays, self.device)
        self.snapshots.append((tag, fn))
        if len(self.snapshots) > self.max_snapshots:
            old, _ = self.snapshots.pop(0)
            self.wins.pop(old, None)

    # -- resume ------------------------------------------------------------------

    def state(self):
        return {"stage": self.stage, "wins": dict(self.wins),
                "counts": dict(self.counts), "handicap": self.handicap,
                "snapshots": [t for t, _ in self.snapshots]}

    def load_state(self, st):
        from trl_env import FrozenPolicyOpponent
        self.stage = min(int(st.get("stage", 0)), len(self.anchors) - 1)
        self.handicap = int(st.get("handicap", self.handicap))
        self.wins = dict(st.get("wins", {}))
        self.counts = collections.Counter(st.get("counts", {}))
        self.snapshots = []
        for tag in st.get("snapshots", []):
            path = os.path.join(self.snapshot_dir, f"{tag}.npz")
            if self.snapshot_dir and os.path.exists(path):
                arrays = dict(np.load(path))
                self.snapshots.append(
                    (tag, FrozenPolicyOpponent.from_state_np(arrays, self.device)))
        self._pending.clear()

    def describe(self):
        cur = self.anchors[self.stage][0]
        ws = " ".join(f"{n}:{w:.2f}" for n, w in sorted(self.wins.items()))
        hc = f"  handicap {self.handicap}" if self.handicap0 else ""
        # which weighting is live, because `hard` and `var` aim at opposite
        # ends of the win-rate range and a silent default would be unreadable
        pf = f"  pfsp {self.pfsp_mode}:{self.pfsp:g}" if self.pfsp > 0 else ""
        return (f"stage {self.stage + 1}/{len(self.anchors)} ({cur}){hc}{pf}  "
                f"snaps {len(self.snapshots)}  ema[{ws}]")
