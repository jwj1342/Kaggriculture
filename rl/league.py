"""League self-play: population, PFSP sampling, gated promotion, retirement.

Design (agreed 2026-08-14, wired for after the ghost milestone):

- The pool is ANCHORS (fixed real-field agents, never retired -- the repo's
  own history says a ranking against an inbred field is not evidence) plus
  exported checkpoints of the training policy.
- Opponent sampling is PFSP with variance weighting f(p) = p(1-p) + eps:
  probability mass concentrates on ~50% opponents, not on hopeless walls or
  crushed victims. Non-transitivity is documented in this game; latest-vs-
  latest self-play cycles, a weighted population does not.
- Promotion is gated with sample-size discipline: the current policy joins
  the pool only after >= MIN_GAMES recent league episodes at >= GATE mean win
  rate (seed spread here resolves ~10pp at ~200 episodes).
- Checkpoint members (never anchors) retire once the policy beats them >= 80%
  over >= 100 games: they stop sampling but stay on disk and in the manifest.

Members are exported numpy agent directories -- exactly what vec_env already
accepts as opponents, so league mode changes nothing below the pool list.
"""

import json
import os

_RL = os.path.dirname(os.path.abspath(__file__))
_AGENTS = os.path.join(os.path.dirname(_RL), "agents")

ANCHORS = [
    ("anchor-starter", "starter"),
    ("anchor-barnyard", os.path.join(_AGENTS, "barnyard.py")),
    ("anchor-ghost", os.path.join(_AGENTS, "ghosts", "ghost-89825016-0.py")),
    ("anchor-spar-grazier",
     os.path.join(_AGENTS, "spar", "estate-crew-grazier-flood-blind-muck.py")),
]

MIN_GAMES = 200
GATE = 0.55
RETIRE_WINRATE = 0.80
RETIRE_MIN_GAMES = 100
EMA_ALPHA = 0.02
PFSP_EPS = 0.05


class League:
    def __init__(self, league_dir):
        self.dir = league_dir
        self.agents_dir = os.path.join(league_dir, "agents")
        os.makedirs(self.agents_dir, exist_ok=True)
        self.manifest_path = os.path.join(league_dir, "league.json")
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path) as f:
                self.m = json.load(f)
        else:
            self.m = {"members": [], "recent": []}
        known = {mm["name"] for mm in self.m["members"]}
        for name, path in ANCHORS:
            if name not in known:
                self.m["members"].append(self._new_member(name, path, "anchor", 0))
        self._by_path = {mm["path"]: mm for mm in self.m["members"]}
        self._save()

    @staticmethod
    def _new_member(name, path, kind, step):
        return {"name": name, "path": path, "kind": kind, "added_step": step,
                "games": 0, "wins": 0.0, "ema": 0.5, "retired": False}

    def _save(self):
        tmp = self.manifest_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.m, f, indent=1)
        os.replace(tmp, self.manifest_path)

    # ---- sampling --------------------------------------------------------

    def active(self):
        return [mm for mm in self.m["members"] if not mm["retired"]]

    def pool(self):
        """[(path, weight)] under PFSP variance weighting. `ema` is the
        *policy's* win rate against the member; f peaks at ema=0.5."""
        out = []
        for mm in self.active():
            p = mm["ema"]
            out.append((mm["path"], p * (1.0 - p) + PFSP_EPS))
        return out

    # ---- bookkeeping -----------------------------------------------------

    def record(self, opponent_path, win):
        mm = self._by_path.get(opponent_path)
        if mm is None:
            return
        mm["games"] += 1
        mm["wins"] += win
        mm["ema"] += EMA_ALPHA * (win - mm["ema"])
        self.m["recent"].append(win)
        del self.m["recent"][:-2 * MIN_GAMES]
        if (mm["kind"] != "anchor" and mm["games"] >= RETIRE_MIN_GAMES
                and mm["wins"] / mm["games"] >= RETIRE_WINRATE):
            mm["retired"] = True

    # ---- promotion -------------------------------------------------------

    def maybe_promote(self, policy, global_step):
        """Export the current policy into the pool when the gate clears.
        Returns the new member's path, or None."""
        recent = self.m["recent"]
        if len(recent) < MIN_GAMES:
            return None
        if sum(recent) / len(recent) < GATE:
            return None
        name = f"ckpt-{global_step // 1000}k"
        out_dir = os.path.join(self.agents_dir, name)
        from export_agent import write_agent_dir
        write_agent_dir(policy, out_dir)
        member = self._new_member(
            name, os.path.join(out_dir, "main.py"), "checkpoint", global_step)
        self.m["members"].append(member)
        self._by_path[member["path"]] = member
        self.m["recent"] = []
        self._save()
        return member["path"]

    def summary(self):
        rows = []
        for mm in self.m["members"]:
            g = mm["games"]
            wr = mm["wins"] / g if g else float("nan")
            flag = "R" if mm["retired"] else (mm["kind"][0])
            rows.append(f"{flag} {mm['name']:<24} g {g:>5} win {wr:5.2f} ema {mm['ema']:.2f}")
        return "\n".join(rows)
