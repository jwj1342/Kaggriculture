"""League self-play: population, mixture sampling, gated promotion, diversity.

Design (agreed 2026-08-14, wired for after the ghost milestone):

- **Pool** = ANCHORS (fixed real-field agents, never retired) + a rolling
  MIRROR of the current policy (refreshed every few iterations; the closest a
  frozen-file opponent gets to live self-play) + promoted checkpoints.
- **Sampling** is a three-bucket mixture: 40% mirror / 40% history / 20%
  anchors, with PFSP variance weighting f(p)=p(1-p)+eps *inside* the history
  bucket only -- effort concentrates on ~50% opponents, the anchor floor
  keeps real-field pressure from ever vanishing.
- **Promotion gate**, all of: >= MIN_GAMES recent league episodes (seat-
  balanced by construction -- workers alternate seats) at >= GATE mean win
  rate; per-anchor EMA floors (a policy that beats the league but fails the
  real field is a degenerate and stays out); behavioural-fingerprint dedup --
  cosine > DUP_COS against a member replaces that member instead of joining
  beside it (upgrades swap in, near-duplicates never accumulate).
- **Retirement**: checkpoint members beaten >= 80% over >= 100 games stop
  being sampled. Anchors and the mirror are exempt.
- Full N x N Bradley-Terry refits are a separate offline job (tools/stats.py
  has bradley_terry; shards must be keyed by *directory* -- every member here
  is a main.py, and the ratings table keys by basename, which would merge the
  whole league into one row).

Members are exported numpy agent directories -- exactly what vec_env accepts
as opponents. Caveat: all member dirs carry copies of the same kg_rl_*
modules and Python caches the first one loaded, so an obs/actions encoding
change invalidates every existing member (delete the league dir and let it
rebuild).
"""

import json
import os

import numpy as np

_RL = os.path.dirname(os.path.abspath(__file__))
_AGENTS = os.path.join(os.path.dirname(_RL), "agents")

ANCHORS = [
    ("anchor-starter", "starter"),
    ("anchor-barnyard", os.path.join(_AGENTS, "barnyard.py")),
    ("anchor-ghost", os.path.join(_AGENTS, "ghosts", "ghost-89825016-0.py")),
    ("anchor-spar-grazier",
     os.path.join(_AGENTS, "spar", "estate-crew-grazier-flood-blind-muck.py")),
    # The nearest unbeaten roster member belongs in the pool -- one measured
    # league-hour trained a distribution that did not contain the goal.
    ("anchor-main", os.path.join(_AGENTS, "enhanced", "main.py")),
]

# Promotion floors on per-anchor EMA win rate, banded by anchor strength;
# raise as the policy matures. Strong anchors (barnyard, spar) deliberately
# have no floor yet.
ANCHOR_FLOORS = {"anchor-starter": 0.80, "anchor-ghost": 0.50}
FLOOR_MIN_GAMES = 40

# Mirror demoted from 0.40: an hour of league play showed mirror games
# inflating the rolling win while ghost skill regressed 0.54 -> 0.42.
MIX_MIRROR, MIX_HISTORY, MIX_ANCHOR = 0.25, 0.25, 0.50
MIN_GAMES = 200
GATE = 0.55
RETIRE_WINRATE = 0.80
RETIRE_MIN_GAMES = 100
EMA_ALPHA = 0.02
PFSP_EPS = 0.05
DUP_COS = 0.97


def _cos(a, b):
    a, b = np.asarray(a), np.asarray(b)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(a @ b) / denom if denom > 0 else 0.0


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
    def _new_member(name, path, kind, step, fingerprint=None):
        return {"name": name, "path": path, "kind": kind, "added_step": step,
                "games": 0, "wins": 0.0, "ema": 0.5, "retired": False,
                "fingerprint": fingerprint}

    def _save(self):
        tmp = self.manifest_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.m, f, indent=1)
        os.replace(tmp, self.manifest_path)

    def _member(self, name):
        for mm in self.m["members"]:
            if mm["name"] == name:
                return mm
        return None

    # ---- mirror ----------------------------------------------------------

    def refresh_mirror(self, policy):
        """Overwrite the rolling self-play mirror with the current policy.
        Weights swap atomically; agent files re-exec per episode, so workers
        pick the new net up on their next reset."""
        from export_agent import write_agent_dir
        out_dir = os.path.join(self.agents_dir, "latest-mirror")
        mm = self._member("latest-mirror")
        if mm is None:
            main_path = write_agent_dir(policy, out_dir)
            mm = self._new_member("latest-mirror", main_path, "mirror", 0)
            self.m["members"].append(mm)
            self._by_path[mm["path"]] = mm
            self._save()
        else:
            tmp = os.path.join(out_dir, "weights_tmp.npz")
            policy.export_npz(tmp)
            os.replace(tmp, os.path.join(out_dir, "weights.npz"))

    # ---- sampling --------------------------------------------------------

    def pool(self):
        """[(path, weight)] under the 40/40/20 mixture."""
        anchors, history, mirror = [], [], None
        for mm in self.m["members"]:
            if mm["retired"]:
                continue
            if mm["kind"] == "anchor":
                anchors.append(mm)
            elif mm["kind"] == "mirror":
                mirror = mm
            else:
                history.append(mm)
        out = []
        if mirror is not None:
            out.append((mirror["path"], MIX_MIRROR))

        def pfsp(members, budget):
            raw = [(mm, mm["ema"] * (1 - mm["ema"]) + PFSP_EPS) for mm in members]
            z = sum(r for _, r in raw)
            return [(mm["path"], budget * r / z) for mm, r in raw]

        # Variance weighting on anchors too: extreme-EMA anchors (mastered
        # starter, walled barnyard) fade automatically, contested ones (main,
        # ghost) absorb the anchor budget.
        if anchors:
            out.extend(pfsp(anchors, MIX_ANCHOR))
        if history:
            out.extend(pfsp(history, MIX_HISTORY))
        # Missing buckets renormalise implicitly (vec_env normalises weights).
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
        if (mm["kind"] == "checkpoint" and mm["games"] >= RETIRE_MIN_GAMES
                and mm["wins"] / mm["games"] >= RETIRE_WINRATE):
            mm["retired"] = True

    # ---- promotion -------------------------------------------------------

    def gate_status(self):
        recent = self.m["recent"]
        overall = sum(recent) / len(recent) if recent else 0.0
        floors_ok = all(
            (mm := self._member(name)) is not None
            and mm["games"] >= FLOOR_MIN_GAMES and mm["ema"] >= floor
            for name, floor in ANCHOR_FLOORS.items())
        return len(recent) >= MIN_GAMES, overall, floors_ok

    def maybe_promote(self, policy, global_step, fingerprint=None):
        """Export the current policy into the pool when every gate clears.
        Returns the new member's path, or None."""
        enough, overall, floors_ok = self.gate_status()
        if not (enough and overall >= GATE and floors_ok):
            return None
        replaced = None
        if fingerprint is not None:
            fp = list(np.asarray(fingerprint, dtype=float))
            for mm in self.m["members"]:
                if mm["kind"] == "checkpoint" and not mm["retired"] \
                        and mm.get("fingerprint") \
                        and _cos(fp, mm["fingerprint"]) >= DUP_COS:
                    mm["retired"] = True          # upgrade swaps in
                    replaced = mm["name"]
        else:
            fp = None
        name = f"ckpt-{global_step // 1000}k"
        out_dir = os.path.join(self.agents_dir, name)
        from export_agent import write_agent_dir
        main_path = write_agent_dir(policy, out_dir)
        member = self._new_member(name, main_path, "checkpoint", global_step, fp)
        self.m["members"].append(member)
        self._by_path[member["path"]] = member
        self.m["recent"] = []
        self._save()
        if replaced:
            print(f"league: {name} replaces near-duplicate {replaced}", flush=True)
        return member["path"]

    def summary(self):
        rows = []
        for mm in self.m["members"]:
            g = mm["games"]
            wr = mm["wins"] / g if g else float("nan")
            flag = "R" if mm["retired"] else mm["kind"][0]
            rows.append(f"{flag} {mm['name']:<24} g {g:>5} win {wr:5.2f} ema {mm['ema']:.2f}")
        return "\n".join(rows)
