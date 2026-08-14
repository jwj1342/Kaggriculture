"""Gym-style single-seat wrapper around the kaggriculture environment.

One KGEnv = one seat in a two-player episode. The opponent runs inside the
kaggle_environments trainer and can be a registered name ("starter", "random",
"pass") or a path to any agent file in this repo.

This layer speaks *raw* observations and *raw* action dicts on purpose:
encoding lives in obs.py, the action space in actions.py, so each can be
iterated without touching the episode driver.

    env = KGEnv(opponent="starter")
    obs = env.reset(seed=1000)
    while True:
        obs, done = env.step({"farmer": ["PASS"], "hands": [], "market": []})
        if done:
            break
    print(env.final_money())
"""

import os
import sys

_RL_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_RL_DIR)
# kg_rules and the agents live one level up; imports stay flat like the agents'.
for _p in (_REPO, os.path.join(_REPO, "agents")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _fast_env():
    """Same verified-identical shortcut as tools/tournament.py: the interpreter
    ignores malformed actions anyway, so jsonschema.validate buys nothing."""
    import jsonschema
    jsonschema.validate = lambda instance, schema, *a, **k: None


class KGEnv:
    def __init__(self, opponent="starter", steps=720, seat=0, fast=True):
        if fast:
            _fast_env()
        from kaggle_environments import make
        self._make = make
        self.opponent = opponent
        self.steps = steps
        self.seat = seat
        self.env = None
        self._trainer = None
        self._last_obs = None

    def reset(self, seed):
        self.env = self._make(
            "kaggriculture",
            configuration={"episodeSteps": self.steps, "seed": seed},
        )
        seats = [None, self.opponent] if self.seat == 0 else [self.opponent, None]
        self._trainer = self.env.train(seats)
        self._last_obs = self._trainer.reset()
        return self._last_obs

    def step(self, action):
        """action: raw kaggle dict {"farmer": [...], "hands": [...], "market": [...]}.
        Returns (obs, done). Reward is derived from obs by the caller (obs.net_worth
        for shaping, final_money for the truth) -- the framework's own per-step
        reward is empty until DONE and never used here."""
        obs, _reward, done, _info = self._trainer.step(action)
        if obs:  # trainer may hand back an empty obs on the terminal step
            self._last_obs = obs
        return self._last_obs, bool(done)

    def final_money(self):
        """(mine, theirs) after done, from the last recorded state."""
        final = self.env.steps[-1]
        me = self.seat
        return (
            float(final[me].reward or 0),
            float(final[1 - me].reward or 0),
        )

    def statuses(self):
        return [str(s.status) for s in self.env.steps[-1]]
