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
                 handicap=0):
        from trl_env import _make_opponent
        self.device = device
        self.anchors = [(_spec_name(s), _make_opponent(s, device)) for s in specs]
        self.stage = 0
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
                name, fn = entries[self._rng.randrange(len(entries))]
                break
            r -= mass
        self._pending.append(name)
        return fn

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
        return (f"stage {self.stage + 1}/{len(self.anchors)} ({cur}){hc}  "
                f"snaps {len(self.snapshots)}  ema[{ws}]")
