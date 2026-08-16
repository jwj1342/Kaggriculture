"""KGEnvNP: drop-in replacement for kg_env.KGEnv running on the verified
engine_np port instead of the kaggle framework. 43x engine throughput
(34,386 vs 798 steps/s on PASS actions, measured 2026-08-15).

Training-only. Evaluation stays on the reference kaggle env (tools/eval.py),
so any residual engine divergence surfaces as a train/eval gap instead of a
corrupted measurement. The engine itself passed the byte-exact 3x720 gate
(verify.py) before this adapter existed.

Opponent handling mirrors the kaggle trainer: a file path is loaded with the
real get_last_callable semantics (empty globals, dir appended to sys.path);
registered names map to the reference module's own agent functions.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_RL = os.path.dirname(_HERE)
_REPO = os.path.dirname(_RL)
for _p in (_HERE, _RL):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import engine_np


def _load_named(name):
    import importlib.util
    ref = os.path.join(_REPO, "reference", "engine", "kaggriculture.py")
    spec = importlib.util.spec_from_file_location("kg_reference_engine", ref)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.agents[name]


def load_agent(opponent):
    """Callable(obs_dict) -> action dict, from a registered name or a file
    path, with the loader semantics agents are written against."""
    if callable(opponent):
        return opponent
    if os.path.sep not in str(opponent) and not str(opponent).endswith(".py"):
        return _load_named(opponent)
    path = os.path.abspath(opponent)
    with open(path) as f:
        code = compile(f.read(), path, "exec")
    env = {}
    sys.path.append(os.path.dirname(path))
    try:
        exec(code, env)
    finally:
        sys.path.pop()
    fns = [v for v in env.values() if callable(v)]
    return fns[-1]


class KGEnvNP:
    """Same surface as kg_env.KGEnv: reset(seed) -> obs, step(action) ->
    (obs, done), final_money(), statuses()."""

    def __init__(self, opponent="starter", steps=720, seat=0, fast=True):
        self.opponent = opponent
        self.steps = steps
        self.seat = seat
        self._opp_fn = load_agent(opponent)
        self._ep = None
        self._final = None

    def _obs_for(self, player):
        snap = self._ep.snapshot()
        return {
            "player": player,
            "step": self._ep._step,
            "day": snap["day"],
            "hour": snap["hour"],
            "farms": snap["farms"],
            "market": {"inventory": snap["market"]["inventory"],
                       "prices": snap["market"]["prices"]},
            "town": snap["town"],
            "private": snap["private"][player],
        }

    def reset(self, seed):
        self._ep = engine_np.Episode(seed=seed, episode_steps=self.steps)
        self._final = None
        return self._obs_for(self.seat)

    def step(self, action):
        opp_seat = 1 - self.seat
        try:
            # No defensive deepcopy: the kaggle framework copies state per
            # agent to protect against ARBITRARY submitted code; every
            # opponent this adapter ever loads is this repo's own (agents/,
            # ghosts, exported policies), none of which mutate their obs.
            # Measured cost of the copy was ~30% of the whole step. If an
            # opponent is ever suspected of mutation, verify by diffing
            # snapshot() before/after its call.
            opp_action = self._opp_fn(self._obs_for(opp_seat))
        except Exception:
            opp_action = {"farmer": ["PASS"], "hands": [], "market": []}
        if not isinstance(opp_action, dict):
            opp_action = {"farmer": ["PASS"], "hands": [], "market": []}
        pair = [action, opp_action] if self.seat == 0 else [opp_action, action]
        self._ep.step(pair)
        done = self._ep.done
        if done and self._final is None:
            snap = self._ep.snapshot()
            self._final = (float(snap["farms"][self.seat]["money"]),
                           float(snap["farms"][opp_seat]["money"]))
        return self._obs_for(self.seat), done

    def final_money(self):
        return self._final

    def statuses(self):
        return ["DONE", "DONE"] if self._ep is not None and self._ep.done else []
