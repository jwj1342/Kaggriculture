"""Gym-style environment wrapper around the Kaggriculture kaggle environment.

The wrapper exposes:
- reset(seed, opponent) -> observation list[float]
- step(action) -> (obs, reward, done, info)

Reward is potential-based (see rl/potential.py):
    r' = (Φ_rel(s') − Φ_rel(s)) / 1000
    done 时加 ±15
"""

import os

os.environ.setdefault("KG_FAST_ENV", "1")

from kaggle_environments import make  # noqa: E402

from . import features  # noqa: E402
from .action_space import decode, decode_market_only, decode_per_unit  # noqa: E402
from .potential import relative_potential, shaped_reward  # noqa: E402


HAND_CAP = 12


def _default_opponent():
    return "starter"


def make_env(opponent=None, board_size=10, starting_money=3000, turns_per_day=24,
             episode_steps=720, seed=None):
    spec = {
        "boardSize": int(board_size),
        "startingMoney": int(starting_money),
        "turnsPerDay": int(turns_per_day),
        "episodeSteps": int(episode_steps),
    }
    if seed is not None:
        spec["seed"] = int(seed)
    env = make("kaggriculture", configuration=spec)
    opp = opponent or _default_opponent()
    trainer = env.train([None, opp])
    obs = trainer.reset()
    return trainer, obs


def _n_hands(obs):
    player = int(features._get(obs, "player") or 0)
    farms = features._get(obs, "farms") or []
    farm = farms[player] if player < len(farms) else {}
    return len(features._get(farm, "hands") or [])


class _BaseEnv:
    def __init__(self, opponent=None, seed=None):
        self.opponent = opponent or _default_opponent()
        self.seed = seed
        self.trainer = None
        self.obs = None
        self.done = False
        self.info = {}
        self._ep_reward = 0.0
        self._step = 0
        self.n_hands = 0
        self._phi = 0.0

    def _after_reset(self):
        self.done = False
        self.info = {"n_hands": _n_hands(self.obs)}
        self._ep_reward = 0.0
        self._step = 0
        self.n_hands = self.info["n_hands"]
        self._phi = relative_potential(self.obs)
        return features.encode(self.obs)

    def _finish_step(self, obs_prev, done, info):
        self.done = bool(done)
        self._step += 1
        self.n_hands = _n_hands(self.obs)
        r, phi = shaped_reward(obs_prev, self.obs, done=self.done, phi_prev=self._phi)
        self._phi = phi
        self._ep_reward += r
        self.info = dict(info or {})
        self.info["n_hands"] = self.n_hands
        return features.encode(self.obs), r, self.done, self.info

    def reset(self):
        self.trainer, self.obs = make_env(opponent=self.opponent, seed=self.seed)
        return self._after_reset()

    def close(self):
        try:
            if self.trainer is not None:
                self.trainer.close()
        except Exception:
            pass


class KaggEnv(_BaseEnv):
    """Single (task, mode) action — v1 action space, v2 reward."""

    def step(self, action):
        if self.done:
            return features.encode(self.obs), 0.0, True, self.info
        task_idx, mode_idx = int(action[0]), int(action[1])
        step_before = int(features._get(self.obs, "step") or 0)
        act = decode(task_idx, mode_idx, self.obs, step=step_before)
        obs_prev = self.obs
        self.obs, _reward, done, info = self.trainer.step(act)
        return self._finish_step(obs_prev, done, info)


class KaggEnvMulti(_BaseEnv):
    """Per-unit action: farmer task + 12 hand tasks + market mode."""

    def step(self, action):
        if self.done:
            return features.encode(self.obs), 0.0, True, self.info
        action = list(action)
        if len(action) < 2:
            action = [0] * (HAND_CAP + 2)
        tasks = action[:1 + HAND_CAP]
        mode_idx = int(action[1 + HAND_CAP] if len(action) > 1 + HAND_CAP else action[-1])
        step_before = int(features._get(self.obs, "step") or 0)
        act = decode_per_unit(tasks, mode_idx, self.obs, step=step_before, hand_cap=HAND_CAP)
        obs_prev = self.obs
        self.obs, _reward, done, info = self.trainer.step(act)
        return self._finish_step(obs_prev, done, info)


class PlanMarketEnv(_BaseEnv):
    """Farm actions from a mined plan; RL controls only market_mode."""

    def __init__(self, plan_turns, opponent=None, seed=None):
        super().__init__(opponent=opponent, seed=seed)
        self.plan = list(plan_turns)
        self.step_count = 0

    def reset(self):
        self.trainer, self.obs = make_env(opponent=self.opponent, seed=self.seed)
        self.step_count = 0
        return self._after_reset()

    def step(self, market_mode):
        if self.done:
            return features.encode(self.obs), 0.0, True, self.info
        plan_turn = self.plan[self.step_count] if self.step_count < len(self.plan) else {
            "farmer": ["PASS"], "hands": [],
        }
        market_orders = decode_market_only(market_mode, self.obs, self.step_count)
        action = {
            "farmer": plan_turn.get("farmer", ["PASS"]),
            "hands": plan_turn.get("hands", []) or [],
            "market": market_orders,
        }
        obs_prev = self.obs
        self.obs, _reward, done, info = self.trainer.step(action)
        self.step_count += 1
        return self._finish_step(obs_prev, done, info)
